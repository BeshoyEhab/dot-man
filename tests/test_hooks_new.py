"""Tests for the hooks module."""

import os

import pytest

from dot_man.hooks import (
    create_hook,
    delete_hook,
    ensure_hooks_dir,
    get_hook_path,
    list_hooks,
    run_hook,
)


@pytest.fixture
def mock_dot_man_dir(tmp_path):
    """Create mock dot-man directory."""
    dot_man = tmp_path / ".config" / "dot-man"
    dot_man.mkdir(parents=True)
    return dot_man


class TestHookPaths:
    """Test hook path utilities."""

    def test_get_hook_path(self, mock_dot_man_dir, monkeypatch):
        """Test getting hook path."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        path = get_hook_path("switch", "pre")
        assert path.name == "pre_switch"
        assert "hooks" in str(path)

    def test_ensure_hooks_dir(self, mock_dot_man_dir, monkeypatch):
        """Test hooks directory creation."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        result = ensure_hooks_dir()
        assert result.exists()
        assert result.is_dir()


class TestHookLifecycle:
    """Test hook creation and deletion."""

    def test_create_hook(self, mock_dot_man_dir, monkeypatch):
        """Test creating a new hook."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        path = create_hook("switch", "pre")
        assert path.exists()
        assert os.access(path, os.X_OK)

        content = path.read_text()
        assert "# dot-man pre_switch hook" in content

    def test_delete_hook(self, mock_dot_man_dir, monkeypatch):
        """Test deleting a hook."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        path = create_hook("checkout", "post")
        assert path.exists()

        deleted = delete_hook("checkout", "post")
        assert deleted is True
        assert not path.exists()

    def test_delete_nonexistent_hook(self, mock_dot_man_dir, monkeypatch):
        """Test deleting a hook that doesn't exist."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        deleted = delete_hook("nonexistent", "pre")
        assert deleted is False


class TestListHooks:
    """Test listing hooks."""

    def test_list_hooks_empty(self, mock_dot_man_dir, monkeypatch):
        """Test listing hooks when none exist."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        hooks_list = list_hooks()
        assert len(hooks_list) > 0
        assert all(not h["exists"] for h in hooks_list)

    def test_list_hooks_with_created(self, mock_dot_man_dir, monkeypatch):
        """Test listing hooks after creating some."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        create_hook("switch", "pre")
        create_hook("deploy", "post")

        hooks_list = list_hooks()
        switch_pre = next(
            h for h in hooks_list if h["command"] == "switch" and h["phase"] == "pre"
        )
        deploy_post = next(
            h for h in hooks_list if h["command"] == "deploy" and h["phase"] == "post"
        )

        assert switch_pre["exists"] is True
        assert deploy_post["exists"] is True


class TestRunHook:
    """Test running hooks."""

    def test_run_nonexistent_hook(self, mock_dot_man_dir, monkeypatch):
        """Test running a hook that doesn't exist returns True."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        result = run_hook("switch", "pre")
        assert result is True

    def test_run_executable_hook(self, mock_dot_man_dir, monkeypatch, capsys):
        """Test running an executable hook."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        hook_path = create_hook("test", "pre")
        hook_path.write_text("#!/bin/bash\necho 'Hook ran successfully'\n")
        hook_path.chmod(0o755)

        result = run_hook("test", "pre")
        assert result is True

        captured = capsys.readouterr()
        assert "Hook ran successfully" in captured.out

    def test_run_hook_with_env(self, mock_dot_man_dir, monkeypatch, capsys):
        """Test running hook with environment variables."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        hook_path = create_hook("env_test", "post")
        hook_path.write_text(
            '#!/bin/bash\necho "COMMAND: $DOTMAN_HOOK_COMMAND"\necho "PHASE: $DOTMAN_HOOK_PHASE"\n'
        )
        hook_path.chmod(0o755)

        result = run_hook("env_test", "post")
        assert result is True

        captured = capsys.readouterr()
        assert "COMMAND: env_test" in captured.out
        assert "PHASE: post" in captured.out

    def test_run_hook_failure(self, mock_dot_man_dir, monkeypatch):
        """Test running a hook that fails returns False."""
        from dot_man import hooks

        monkeypatch.setattr(hooks, "HOOKS_DIR", mock_dot_man_dir / "hooks")

        hook_path = create_hook("fail_test", "pre")
        hook_path.write_text("#!/bin/bash\nexit 1\n")
        hook_path.chmod(0o755)

        result = run_hook("fail_test", "pre")
        assert result is False
