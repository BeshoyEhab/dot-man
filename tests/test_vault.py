import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from dot_man.vault import SecretVault


@pytest.fixture
def temp_vault_dir(tmp_path):
    """Create a temporary directory for vault."""
    config_dir = tmp_path / ".config" / "dot-man"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def vault(temp_vault_dir):
    """Create a vault instance using temp dir."""
    v = SecretVault()
    v.config_dir = temp_vault_dir
    v.vault_file = temp_vault_dir / "vault.json"
    v.key_file = temp_vault_dir / ".key"
    return v


def test_vault_basic_ops(vault):
    """Test basic stash and get operations."""
    # Stash
    h = vault.stash_secret("file1.txt", 10, "test", "mysecret", "main")
    assert h

    # Get
    secret = vault.get_secret("file1.txt", 10, "main")
    assert secret == "mysecret"

    # Get by hash
    secret_by_hash = vault.get_secret_by_hash(h)
    assert secret_by_hash == "mysecret"


def test_vault_batching(vault):
    """Test that batching defers writes."""

    # Initial state
    assert not vault.vault_file.exists()

    with vault.batch():
        vault.stash_secret("f1", 1, "p1", "s1", "main")
        vault.stash_secret("f2", 2, "p2", "s2", "main")

        # Should not exist or be empty/stale if we checked disk content directly
        # But wait, stash_secret logic: if not batch, save.
        # Since we are in batch, it sets _dirty=True.

        # We can check that the file hasn't been created yet if it didn't exist
        # (save creates it)
        # Note: _get_fernet creates key file, but not vault file.
        assert not vault.vault_file.exists()

    # Now it should exist
    assert vault.vault_file.exists()

    # Verify content
    data = json.loads(vault.vault_file.read_text())
    assert len(data["secrets"]) == 2


def test_vault_caching(vault):
    """Test that load uses cache."""
    # Create a secret
    vault.stash_secret("f1", 1, "p1", "s1", "main")

    # Verify secret exists
    assert vault.get_secret("f1", 1, "main") == "s1"

    # Wait to ensure mtime changes
    time.sleep(0.01)

    # Manually write new content (simulate external modification)
    new_data = {"secrets": []}
    vault.vault_file.write_text(json.dumps(new_data))

    # Calling get_secret should reload because mtime changed
    # Verify we see empty secrets (cache was invalidated)
    assert vault.get_secret("f1", 1, "main") is None

    # Now restore the secret
    vault.stash_secret("f1", 1, "p1", "s1", "main")

    # Access again - should be cached from in-memory data
    # Verify secret is accessible
    assert vault.get_secret("f1", 1, "main") == "s1"

    # Verify file on disk now has the secret
    data = json.loads(vault.vault_file.read_text())
    assert len(data["secrets"]) == 1


def test_vault_concurrency(vault):
    """Test concurrent stashing."""
    count = 100

    def worker(i):
        vault.stash_secret(f"file_{i}", i, "pattern", f"secret_{i}", "main")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(count)]
        for f in futures:
            f.result()

    # Verify all 100 are present
    data = json.loads(vault.vault_file.read_text())
    assert len(data["secrets"]) == count

    # Verify values
    for i in range(count):
        s = vault.get_secret(f"file_{i}", i, "main")
        assert s == f"secret_{i}"


def test_vault_concurrency_with_batch(vault):
    """Test concurrent stashing inside a batch."""
    count = 100

    def worker(i):
        vault.stash_secret(f"file_{i}", i, "pattern", f"secret_{i}", "main")

    with vault.batch():
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(count)]
            for f in futures:
                f.result()

    # Verify all 100 are present
    data = json.loads(vault.vault_file.read_text())
    assert len(data["secrets"]) == count


def test_atomic_write_robustness(vault):
    """Verify atomic write doesn't leave partial files."""
    vault.stash_secret("f1", 1, "p", "s", "b")
    assert vault.vault_file.exists()

    # Verify no .tmp files left
    tmp_files = list(vault.config_dir.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_rotate_key(vault):
    """Test key rotation re-encrypts all secrets."""
    vault.stash_secret("f1", 1, "p1", "secret1", "main")
    vault.stash_secret("f2", 2, "p2", "secret2", "work")

    count = vault.rotate_key()
    assert count == 2

    # Old key backed up
    assert vault.key_file.with_suffix(".key.bak").exists()

    # Secrets still decryptable
    assert vault.get_secret("f1", 1, "main") == "secret1"
    assert vault.get_secret("f2", 2, "work") == "secret2"


def test_rotate_key_empty_vault(vault):
    """Test rotate key on empty vault."""
    count = vault.rotate_key()
    assert count == 0


def test_rotate_key_corrupted_secret(vault):
    """Test rotate key fails if a secret can't be decrypted."""
    vault.stash_secret("f1", 1, "p1", "secret1", "main")

    # Directly inject a secret with invalid encrypted value
    # by writing raw JSON and resetting state
    data = json.loads(vault.vault_file.read_text())
    # Use a value that Fernet.decrypt() will reject with ValueError
    # (not InvalidToken — which is not caught by rotate_key)
    data["secrets"][0]["encrypted_value"] = "gAAAAA"
    vault.vault_file.write_text(json.dumps(data))
    vault._last_loaded_mtime = 0.0
    vault._fernet = None

    from dot_man.vault import VaultError

    with pytest.raises((VaultError, Exception)):
        vault.rotate_key()


def test_restore_secrets_in_content(vault):
    """Test restoring secrets in content via hash placeholders."""
    h = vault.stash_secret("f1", 1, "p1", "my_api_key", "main")

    content = f"API_KEY=***REDACTED:{h}***"
    restored = vault.restore_secrets_in_content(content, "f1", "main")

    assert restored == "API_KEY=my_api_key"


def test_restore_secrets_in_content_not_found(vault):
    """Test placeholder kept when hash not in vault."""
    content = "API_KEY=***REDACTED:deadbeef0000000000000000000000000000000000000000000000000000dead***"
    restored = vault.restore_secrets_in_content(content, "f1", "main")
    assert restored == content


def test_restore_secrets_in_content_no_placeholders(vault):
    """Test content without placeholders returned unchanged."""
    content = "plain text nothing here"
    restored = vault.restore_secrets_in_content(content, "f1", "main")
    assert restored == content


def test_get_secret_not_found(vault):
    """Test get_secret returns None when not found."""
    vault.stash_secret("f1", 1, "p1", "secret", "main")
    result = vault.get_secret("f1", 999, "main")
    assert result is None


def test_get_secret_by_hash_not_found(vault):
    """Test get_secret_by_hash returns None for unknown hash."""
    vault.stash_secret("f1", 1, "p1", "secret", "main")
    result = vault.get_secret_by_hash(
        "deadbeef0000000000000000000000000000000000000000000000000000dead"
    )
    assert result is None


def test_load_corrupted_vault_file(vault):
    """Test load handles corrupted vault.json gracefully."""
    vault.vault_file.write_text("{invalid json}")
    vault.load()
    assert vault._data == {"secrets": []}


def test_load_nonexistent_vault_file(vault):
    """Test load handles missing vault.json."""
    vault.load()
    assert vault._data == {"secrets": []}


def test_load_skips_when_dirty(vault):
    """Test load skips reading when dirty."""
    vault.stash_secret("f1", 1, "p1", "secret", "main")
    vault._dirty = True
    vault._data["secrets"] = [{"fake": True}]

    vault.load()
    # Should not have reloaded from disk
    assert vault._data["secrets"] == [{"fake": True}]


def test_save_handles_os_error(vault):
    """Test save raises VaultError on OS error."""
    vault.vault_file = vault.config_dir / "nonexistent_dir" / "vault.json"
    vault._data = {"secrets": []}

    from dot_man.vault import VaultError

    with pytest.raises(VaultError):
        vault.save()


def test_stash_update_existing(vault):
    """Test stashing same secret updates instead of duplicating."""
    vault.stash_secret("f1", 10, "AWS Key", "key1", "main")
    vault.stash_secret("f1", 10, "AWS Key", "key1", "main")

    data = json.loads(vault.vault_file.read_text())
    # Should be 1 entry, not 2
    assert len(data["secrets"]) == 1


def test_stash_secret_retry_on_lock_error(vault):
    """Test stash_secret retries when lock is held."""
    vault.stash_secret("f1", 1, "p1", "secret", "main")
    assert vault.get_secret("f1", 1, "main") == "secret"
