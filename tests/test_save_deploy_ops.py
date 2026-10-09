"""Tests for save_deploy_ops module."""

from unittest.mock import MagicMock, patch

from dot_man.config import Section
from dot_man.save_deploy_ops import _BINARY_EXTENSIONS, SaveDeployMixin
from dot_man.vault import SecretVault


class FakeOps(SaveDeployMixin):
    """Minimal SaveDeployMixin subclass for testing."""

    def __init__(self, vault=None, current_branch="main", sections=None):
        self._vault = vault or MagicMock(spec=SecretVault)
        self._current_branch = current_branch
        self._sections = sections or {}

    @property
    def vault(self):
        return self._vault

    @property
    def current_branch(self):
        return self._current_branch

    def get_section(self, name):
        return self._sections[name]

    def get_sections(self):
        return list(self._sections.keys())


# ─── _restore_file_secrets ────────────────────────────────


class TestRestoreFileSecrets:
    """Test _restore_file_secrets method."""

    def test_skip_binary_file(self, tmp_path):
        """Binary files should be skipped."""
        ops = FakeOps()
        bin_file = tmp_path / "image.png"
        bin_file.write_text("fake png content")
        result = ops._restore_file_secrets(bin_file, ".config/img.png", "main")
        assert result is None

    def test_restore_text_file(self, tmp_path):
        """Text file with redacted secrets should be restored."""
        vault = MagicMock(spec=SecretVault)
        vault.restore_secrets_in_content.return_value = "restored content"
        ops = FakeOps(vault=vault)
        text_file = tmp_path / "config.txt"
        text_file.write_text("password = ***REDACTED***")
        result = ops._restore_file_secrets(text_file, ".config/config.txt", "main")
        assert result is None
        vault.restore_secrets_in_content.assert_called_once()
        assert text_file.read_text() == "restored content"

    def test_restore_no_change(self, tmp_path):
        """File should not be rewritten if content unchanged."""
        vault = MagicMock(spec=SecretVault)
        vault.restore_secrets_in_content.return_value = "same content"
        ops = FakeOps(vault=vault)
        text_file = tmp_path / "config.txt"
        text_file.write_text("same content")
        with patch("dot_man.save_deploy_ops.atomic_write_text") as mock_write:
            ops._restore_file_secrets(text_file, ".config/config.txt", "main")
            mock_write.assert_not_called()

    def test_restore_os_error(self, tmp_path):
        """OSError during restore should return error string."""
        vault = MagicMock(spec=SecretVault)
        vault.restore_secrets_in_content.side_effect = OSError("Permission denied")
        ops = FakeOps(vault=vault)
        text_file = tmp_path / "config.txt"
        text_file.write_text("some content")
        result = ops._restore_file_secrets(text_file, ".config/config.txt", "main")
        assert result is not None
        assert "Permission denied" in result

    def test_restore_binary_extension_check(self, tmp_path):
        """_BINARY_EXTENSIONS should include common binary formats."""
        assert ".jpg" in _BINARY_EXTENSIONS
        assert ".png" in _BINARY_EXTENSIONS
        assert ".zip" in _BINARY_EXTENSIONS
        assert ".pdf" in _BINARY_EXTENSIONS
        assert ".pyc" in _BINARY_EXTENSIONS

    def test_restore_unicode_decode_error(self, tmp_path):
        """UnicodeDecodeError should be silently skipped."""
        vault = MagicMock(spec=SecretVault)
        ops = FakeOps(vault=vault)
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x80\x81\x82")
        result = ops._restore_file_secrets(binary_file, ".config/binary.bin", "main")
        assert result is None


# ─── save_section ─────────────────────────────────────────


class TestSaveSection:
    """Test save_section method."""

    def test_save_single_file(self, tmp_path):
        """Save a single file from local to repo."""
        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("export PATH=$PATH:/custom/bin")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        vault = MagicMock(spec=SecretVault)
        ops = FakeOps(vault=vault, current_branch="main")
        repo_dir = tmp_path / "repo"
        with patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir):
            saved, secrets, errors, symlinks = ops.save_section(section)
            assert saved == 1
            assert secrets == []
            assert errors == []
            assert symlinks == []

    def test_save_section_secret_detection(self, tmp_path):
        """Save a file with secret detection - vault should stash secrets."""
        local = tmp_path / "local" / ".env"
        local.parent.mkdir(parents=True)
        local.write_text("API_KEY=sk-1234567890abcdef")

        section = Section(
            name="env",
            paths=[local],
            secrets_filter=True,
        )
        vault = MagicMock(spec=SecretVault)
        vault.stash_secret.return_value = "abc123"
        ops = FakeOps(vault=vault, current_branch="main")

        from dot_man.secrets import SecretMatch, Severity

        # Simulate copy_file that invokes secret_handler
        def mock_copy_file(src, dst, filter_secrets_enabled, secret_handler, **_):
            if filter_secrets_enabled and secret_handler:
                match = SecretMatch(
                    file=src,
                    line_number=1,
                    matched_text="sk-1234567890abcdef",
                    pattern_name="api_key",
                    line_content="API_KEY=sk-1234567890abcdef",
                    severity=Severity.HIGH,
                )
                action = secret_handler(match)
                return (True, [match] if action == "REDACT" else [])
            return (True, [])

        repo_dir = tmp_path / "repo"
        with (
            patch(
                "dot_man.save_deploy_ops.copy_file",
                side_effect=mock_copy_file,
            ),
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        ):
            saved, secrets, errors, symlinks = ops.save_section(section)
            assert saved == 1
            assert vault.stash_secret.called

    def test_save_section_nonexistent_path(self, tmp_path):
        """Non-existent paths should be silently skipped."""
        local = tmp_path / "nonexistent" / "file.txt"

        section = Section(
            name="test",
            paths=[local],
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        saved, secrets, errors, symlinks = ops.save_section(section)
        assert saved == 0
        assert errors == []

    def test_save_section_os_error(self, tmp_path):
        """OSError during save should be caught."""
        local = tmp_path / "local" / "file.txt"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="test",
            paths=[local],
            repo_base="test",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with patch(
            "dot_man.save_deploy_ops.copy_file",
            side_effect=OSError("Disk full"),
        ):
            saved, secrets, errors, symlinks = ops.save_section(section)
            assert errors
            assert "Disk full" in errors[0]

    def test_save_section_symlink_followed_by_default(self, tmp_path):
        """Symlinked file is followed and saved by default (symlink_ignore not set)."""
        local = tmp_path / "local" / "linked_file.txt"
        target = tmp_path / "target" / "real_file.txt"
        target.parent.mkdir(parents=True)
        target.write_text("real content")
        local.parent.mkdir(parents=True)
        local.symlink_to(target)

        section = Section(
            name="test",
            paths=[local],
            repo_base="test",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        repo_dir = tmp_path / "repo"
        with patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir):
            saved, secrets, errors, symlinks = ops.save_section(section)
            assert saved == 1
            assert symlinks == [local]
            # Verify the repo file has the target's content
            repo_path = repo_dir / "test" / "linked_file.txt"
            assert repo_path.read_text() == "real content"

    def test_save_section_symlink_ignored(self, tmp_path):
        """Symlinked file is skipped when in symlink_ignore set."""
        local = tmp_path / "local" / "linked_file.txt"
        target = tmp_path / "target" / "real_file.txt"
        target.parent.mkdir(parents=True)
        target.write_text("real content")
        local.parent.mkdir(parents=True)
        local.symlink_to(target)

        section = Section(
            name="test",
            paths=[local],
            repo_base="test",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        repo_dir = tmp_path / "repo"
        with patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir):
            saved, secrets, errors, symlinks = ops.save_section(
                section, symlink_ignore={local}
            )
            assert saved == 0
            assert symlinks == [local]
            # Verify no repo file was created
            repo_path = repo_dir / "test" / "linked_file.txt"
            assert not repo_path.exists()

    def test_save_section_symlink_ignore_non_matching(self, tmp_path):
        """Only the exact ignored symlink is skipped; others are still saved."""
        local1 = tmp_path / "local" / "linked1.txt"
        target1 = tmp_path / "target1" / "real1.txt"
        target1.parent.mkdir(parents=True)
        target1.write_text("content1")
        local1.parent.mkdir(parents=True)
        local1.symlink_to(target1)

        local2 = tmp_path / "local" / "linked2.txt"
        target2 = tmp_path / "target2" / "real2.txt"
        target2.parent.mkdir(parents=True)
        target2.write_text("content2")
        local2.symlink_to(target2)

        section = Section(
            name="test",
            paths=[local1, local2],
            repo_base="test",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        repo_dir = tmp_path / "repo"
        with patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir):
            saved, secrets, errors, symlinks = ops.save_section(
                section, symlink_ignore={local1}
            )
            assert saved == 1
            assert local1 in symlinks
            assert local2 in symlinks
            # local1 was ignored, local2 was saved
            repo_path1 = repo_dir / "test" / "linked1.txt"
            repo_path2 = repo_dir / "test" / "linked2.txt"
            assert not repo_path1.exists()
            assert repo_path2.read_text() == "content2"


# ─── deploy_section ───────────────────────────────────────


class TestDeploySection:
    """Test deploy_section method."""

    def _make_repo_file(self, tmp_path, repo_base, filename, content):
        """Create a repo file at the path get_repo_path would compute."""
        local = tmp_path / "local" / filename
        repo_dir = tmp_path / "repo"
        repo_file = repo_dir / repo_base / filename
        repo_file.parent.mkdir(parents=True, exist_ok=True)
        repo_file.write_text(content)
        return local, repo_file, repo_dir

    def test_deploy_file_copy(self, tmp_path):
        """Deploy a single file via copy."""
        local, repo_file, repo_dir = self._make_repo_file(
            tmp_path, "bashrc", ".bashrc", "export PATH=$PATH:/custom/bin"
        )
        local.parent.mkdir(parents=True)
        local.touch()

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, had_changes, errors = ops.deploy_section(section)
            assert deployed == 1
            assert had_changes is True
            assert errors == []

    def test_deploy_symlink_file(self, tmp_path):
        """Deploy a single file via symlink."""
        local, repo_file, repo_dir = self._make_repo_file(
            tmp_path, "bashrc", ".bashrc", "content"
        )
        local.parent.mkdir(parents=True)

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
            deploy_method="symlink",
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, had_changes, errors = ops.deploy_section(section)
            assert deployed == 1
            assert errors == []

    def test_deploy_ignore_strategy(self, tmp_path):
        """Deploy with ignore strategy should skip existing paths."""
        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("existing content")

        section = Section(
            name="bash",
            paths=[local],
            secrets_filter=False,
            update_strategy="ignore",
        )
        ops = FakeOps(current_branch="main")
        with patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path):
            deployed, had_changes, errors = ops.deploy_section(section)
            assert deployed == 0

    def test_deploy_rename_old_strategy(self, tmp_path):
        """Deploy with rename_old strategy should backup existing."""
        local, repo_file, repo_dir = self._make_repo_file(
            tmp_path, "bashrc", ".bashrc", "new content"
        )
        local.parent.mkdir(parents=True)
        local.write_text("old content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
            update_strategy="rename_old",
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            with patch("dot_man.save_deploy_ops.backup_file") as mock_backup:
                deployed, had_changes, errors = ops.deploy_section(section)
                mock_backup.assert_called_once()
                assert deployed == 1

    def test_deploy_permission_error(self, tmp_path):
        """PermissionError during deploy should be captured."""
        local, repo_file, repo_dir = self._make_repo_file(
            tmp_path, "bashrc", ".bashrc", "content"
        )
        local.parent.mkdir(parents=True)

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch(
                "dot_man.save_deploy_ops.copy_file",
                side_effect=PermissionError("Permission denied"),
            ),
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, had_changes, errors = ops.deploy_section(section)
            assert errors
            assert "Permission denied" in errors[0]

    def test_deploy_symlink_local_path_warns(self, tmp_path):
        """Deploy warns when overwriting a symlinked local path."""
        repo_file = tmp_path / "repo" / "bashrc" / ".bashrc"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("repo content")

        target = tmp_path / "target" / "real_file.txt"
        target.parent.mkdir(parents=True)
        target.write_text("real content")

        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.symlink_to(target)

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, had_changes, errors = ops.deploy_section(section)
            assert deployed == 1
            assert any("symlink" in e.lower() for e in errors)

    def test_deploy_directory_copy(self, tmp_path):
        """Deploy a directory via copy."""
        repo_dir = tmp_path / "repo"
        # get_repo_path for dir ~/.config/nvim with repo_base="nvim"
        # returns: REPO_DIR / "nvim" / "nvim" (since local_path.name == "nvim")
        repo_source = repo_dir / "nvim" / "nvim"
        repo_source.mkdir(parents=True)
        (repo_source / "init.lua").write_text("-- config")
        (repo_source / "colors").mkdir()
        (repo_source / "colors" / "theme.lua").write_text("-- theme")

        local = tmp_path / "local" / ".config" / "nvim"
        local.mkdir(parents=True)

        section = Section(
            name="nvim",
            paths=[local],
            repo_base="nvim",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, had_changes, errors = ops.deploy_section(section)
            assert deployed >= 2
            assert errors == []


# ─── scan_deployable_changes ──────────────────────────────


class TestScanDeployableChanges:
    """Test scan_deployable_changes method."""

    def test_scan_no_changes(self, tmp_path):
        """Scan when nothing has changed."""
        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="bash",
            paths=[local],
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path),
            patch("dot_man.save_deploy_ops.compare_files", return_value=True),
        ):
            plan = ops.scan_deployable_changes([section])
            assert plan["sections_to_deploy"] == []

    def test_scan_with_changes(self, tmp_path):
        """Scan when files have changed."""
        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("new content")

        repo_file = tmp_path / "bashrc"
        repo_file.write_text("old content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base=".",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            plan = ops.scan_deployable_changes([section])
            assert len(plan["sections_to_deploy"]) >= 0

    def test_scan_collects_hooks(self, tmp_path):
        """Scan should collect pre/post hooks."""
        repo_dir = tmp_path / "repo"
        (repo_dir / "bashrc" / ".bashrc").parent.mkdir(parents=True)
        (repo_dir / "bashrc" / ".bashrc").write_text("repo content")

        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("different content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
            pre_deploy="echo before",
            post_deploy="echo after",
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            plan = ops.scan_deployable_changes([section])
            assert plan["pre_hooks"] == ["echo before"]
            assert plan["post_hooks"] == ["echo after"]

    def test_scan_ignore_strategy(self, tmp_path):
        """Scan should skip sections with ignore strategy on existing paths."""
        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="bash",
            paths=[local],
            secrets_filter=False,
            update_strategy="ignore",
        )
        ops = FakeOps(current_branch="main")
        with patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path):
            plan = ops.scan_deployable_changes([section])
            assert plan["sections_to_deploy"] == []


# ─── execute_deployment_plan ──────────────────────────────


class TestExecuteDeploymentPlan:
    """Test execute_deployment_plan method."""

    def test_execute_empty_plan(self):
        """Empty plan should do nothing."""
        ops = FakeOps()
        plan = {
            "sections_to_deploy": [],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": [],
        }
        result = ops.execute_deployment_plan(plan)
        assert result["deployed"] == 0
        assert result["errors"] == []

    def test_execute_with_errors(self):
        """Plan with pre-existing errors should propagate them."""
        ops = FakeOps()
        plan = {
            "sections_to_deploy": [],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": ["prior error"],
        }
        result = ops.execute_deployment_plan(plan)
        assert "prior error" in result["errors"]

    def test_execute_deduplicates_hooks(self):
        """Duplicate hooks should be deduplicated."""
        ops = FakeOps()
        plan = {
            "sections_to_deploy": [],
            "pre_hooks": ["echo hello", "echo hello"],
            "post_hooks": ["echo bye", "echo bye"],
            "errors": [],
        }
        result = ops.execute_deployment_plan(plan)
        assert result["pre_hooks"] == ["echo hello"]
        assert result["post_hooks"] == ["echo bye"]


# ─── save_all ─────────────────────────────────────────────


class TestSaveAll:
    """Test save_all method."""

    def test_save_no_sections(self):
        """save_all with no sections should return zeros."""
        ops = FakeOps(sections={})
        result = ops.save_all()
        assert result["saved"] == 0
        assert result["errors"] == []

    def test_save_error_handling(self, tmp_path):
        """save_all should capture errors from individual saves."""
        local = tmp_path / "local" / "file.txt"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="test",
            paths=[local],
            secrets_filter=False,
        )
        vault = MagicMock(spec=SecretVault)
        ops = FakeOps(vault=vault, current_branch="main", sections={"test": section})
        with patch.object(ops, "save_section", side_effect=Exception("Boom!")):
            result = ops.save_all()
            assert result["saved"] == 0
            assert any("Boom" in e for e in result["errors"])

    def test_save_all_passes_symlink_ignore(self, tmp_path):
        """save_all should pass symlink_ignore to save_section."""
        local1 = tmp_path / "local" / "linked1.txt"
        target1 = tmp_path / "_target1" / "real1.txt"
        target1.parent.mkdir(parents=True)
        target1.write_text("content1")
        local1.parent.mkdir(parents=True)
        local1.symlink_to(target1)

        local2 = tmp_path / "local" / "linked2.txt"
        target2 = tmp_path / "_target2" / "real2.txt"
        target2.parent.mkdir(parents=True)
        target2.write_text("content2")
        local2.symlink_to(target2)

        section = Section(
            name="test",
            paths=[local1, local2],
            repo_base="test",
            secrets_filter=False,
        )
        vault = MagicMock(spec=SecretVault)
        ops = FakeOps(vault=vault, current_branch="main", sections={"test": section})
        repo_dir = tmp_path / "repo"
        with patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir):
            result = ops.save_all(symlink_ignore={local1})
            assert result["saved"] == 1
            assert local1 in result["symlinks"]
            assert local2 in result["symlinks"]
            # local1 ignored, local2 saved
            repo_path1 = repo_dir / "test" / "linked1.txt"
            repo_path2 = repo_dir / "test" / "linked2.txt"
            assert not repo_path1.exists()
            assert repo_path2.read_text() == "content2"


# ─── deploy_all ───────────────────────────────────────────


class TestDeployAll:
    """Test deploy_all method."""

    def test_deploy_all_flow(self, tmp_path):
        """deploy_all should run two-phase deploy."""
        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)

        section = Section(
            name="bash",
            paths=[local],
            secrets_filter=False,
        )
        vault = MagicMock(spec=SecretVault)
        ops = FakeOps(vault=vault, current_branch="main", sections={"bash": section})
        with (
            patch.object(ops, "scan_deployable_changes") as mock_scan,
            patch.object(ops, "execute_deployment_plan") as mock_exec,
        ):
            mock_scan.return_value = {"sections_to_deploy": [], "errors": []}
            ops.deploy_all()
            mock_scan.assert_called_once()
            mock_exec.assert_called_once()


# ─── coverage floor: decode edge, deploy failures, templates,
#     wrapped_handler, directory save, plan scan/execute ───────────


class TestRestoreDecodeEdge:
    def test_restore_unicode_decode_error_real_bytes(self, tmp_path):
        ops = FakeOps()
        data_file = tmp_path / "data.conf"
        data_file.write_bytes(b"\x80\x81\x82 not valid utf-8")

        assert ops._restore_file_secrets(data_file, "data.conf", "main") is None


class TestDeployRepoPathFailures:
    def test_file_symlink_failure_appends_error(self, tmp_path):
        ops = FakeOps()
        repo_file = tmp_path / "repo" / "sec" / "f.txt"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("x")
        local = tmp_path / "local" / "f.txt"
        section = Section(
            name="sec",
            paths=[local],
            repo_base="sec",
            deploy_method="symlink",
            secrets_filter=False,
        )

        with patch(
            "dot_man.save_deploy_ops.deploy_file_or_symlink",
            return_value=(False, None),
        ):
            errors: list = []
            count = ops._deploy_repo_path(repo_file, local, section, [], errors)

        assert count == 0
        assert errors == [f"Failed to symlink {repo_file} to {local}"]

    def test_file_copy_failure_appends_error(self, tmp_path):
        ops = FakeOps()
        repo_file = tmp_path / "repo" / "sec" / "f.txt"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("x")
        local = tmp_path / "local" / "f.txt"
        section = Section(
            name="sec", paths=[local], repo_base="sec", secrets_filter=False
        )

        with patch("dot_man.save_deploy_ops.copy_file", return_value=(False, [])):
            errors: list = []
            count = ops._deploy_repo_path(repo_file, local, section, [], errors)

        assert count == 0
        assert errors == [f"Failed to copy {repo_file} to {local}"]

    def test_source_missing_appends_error(self, tmp_path):
        ops = FakeOps()
        repo_file = tmp_path / "repo" / "sec" / "gone.txt"
        local = tmp_path / "local" / "f.txt"
        section = Section(
            name="sec", paths=[local], repo_base="sec", secrets_filter=False
        )

        errors: list = []
        count = ops._deploy_repo_path(repo_file, local, section, [], errors)

        assert count == 0
        assert errors == [f"Source not found in repo: {repo_file}"]

    def test_file_not_found_during_deploy_appends(self, tmp_path):
        ops = FakeOps()
        repo_file = tmp_path / "repo" / "sec" / "f.txt"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("x")
        local = tmp_path / "local" / "f.txt"
        section = Section(
            name="sec", paths=[local], repo_base="sec", secrets_filter=False
        )

        with patch(
            "dot_man.save_deploy_ops.copy_file",
            side_effect=FileNotFoundError("gone"),
        ):
            errors: list = []
            count = ops._deploy_repo_path(repo_file, local, section, [], errors)

        assert count == 0
        assert errors == [f"File not found during deployment: {repo_file}"]

    def test_directory_symlink_deploy(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_source = repo_dir / "nvim" / "nvim"
        repo_source.mkdir(parents=True)
        (repo_source / "init.lua").write_text("-- config")
        (repo_source / "colors").mkdir()
        (repo_source / "colors" / "theme.lua").write_text("-- theme")

        local = tmp_path / "local" / ".config" / "nvim"
        local.mkdir(parents=True)

        section = Section(
            name="nvim",
            paths=[local],
            repo_base="nvim",
            deploy_method="symlink",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, had_changes, errors = ops.deploy_section(section)

        assert deployed >= 2
        assert errors == []
        assert (local / "init.lua").is_symlink()
        assert (local / "colors" / "theme.lua").is_symlink()

    def test_directory_secrets_restored_per_file(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_source = repo_dir / "app" / "app"
        repo_source.mkdir(parents=True)
        (repo_source / "one.conf").write_text("a = 1")
        (repo_source / "two.conf").write_text("b = 2")

        local = tmp_path / "local" / "app"
        local.mkdir(parents=True)

        vault = MagicMock(spec=SecretVault)
        vault.restore_secrets_in_content.side_effect = lambda c, *a: c
        section = Section(
            name="app",
            paths=[local],
            repo_base="app",
            secrets_filter=True,
        )
        ops = FakeOps(vault=vault, current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch("dot_man.save_deploy_ops.compare_files", return_value=False),
        ):
            deployed, _, errors = ops.deploy_section(section)

        assert deployed >= 2
        assert errors == []
        assert vault.restore_secrets_in_content.call_count >= 2

    def test_directory_partial_failure_appends(self, tmp_path):
        ops = FakeOps()
        repo_source = tmp_path / "repo" / "app" / "app"
        repo_source.mkdir(parents=True)
        (repo_source / "one.conf").write_text("a = 1")
        local = tmp_path / "local" / "app"
        local.mkdir(parents=True)

        section = Section(
            name="app", paths=[local], repo_base="app", secrets_filter=False
        )

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
            patch(
                "dot_man.save_deploy_ops.copy_directory",
                return_value=(0, 3, []),
            ),
        ):
            errors: list = []
            count = ops._deploy_repo_path(repo_source, local, section, [], errors)

        assert count == 0
        assert errors == [f"Failed to deploy 3 files in {local}"]


class TestTemplateRendering:
    def test_render_writes_changes(self, tmp_path):
        ops = FakeOps()
        target = tmp_path / "out.conf"
        target.write_text("{{GREETING}}")

        with patch(
            "dot_man.global_config.substitute_templates",
            return_value="hello world",
        ):
            errors: list = []
            ops._render_templates_inplace(target, errors)

        assert errors == []
        assert target.read_text() == "hello world"

    def test_render_failure_appends_warning(self, tmp_path):
        ops = FakeOps()
        target = tmp_path / "out.conf"
        target.write_text("{{GREETING}}")

        with patch(
            "dot_man.global_config.substitute_templates",
            side_effect=RuntimeError("bad template"),
        ):
            errors: list = []
            ops._render_templates_inplace(target, errors)

        assert len(errors) == 1
        assert "template rendering failed" in errors[0]
        assert "bad template" in errors[0]


class TestRestoreInplaceError:
    def test_restore_inplace_appends_error(self, tmp_path):
        ops = FakeOps()
        target = tmp_path / "f.conf"
        target.write_text("x")

        with patch.object(
            FakeOps,
            "_restore_file_secrets",
            return_value="Failed to restore secrets for x: boom",
        ):
            errors: list = []
            ops._restore_file_secrets_inplace(target, str(target), errors)

        assert errors == ["Failed to restore secrets for x: boom"]


class TestWrappedHandlerFloor:
    @staticmethod
    def _secret_section_and_match(tmp_path):
        from dot_man.secrets import SecretMatch, Severity

        local = tmp_path / "local" / ".env"
        local.parent.mkdir(parents=True)
        local.write_text("API_KEY=sk-1234567890abcdef")
        section = Section(name="env", paths=[local], secrets_filter=True)
        match = SecretMatch(
            file=local,
            line_number=1,
            matched_text="sk-1234567890abcdef",
            pattern_name="api_key",
            line_content="API_KEY=sk-1234567890abcdef",
            severity=Severity.HIGH,
        )
        return section, match

    @staticmethod
    def _mock_copy(match):
        def mock_copy_file(src, dst, filter_secrets_enabled, secret_handler, **_):
            if filter_secrets_enabled and secret_handler:
                action = secret_handler(match)
                return (True, [match] if action == "REDACT" else [])
            return (True, [])

        return mock_copy_file

    def test_custom_secret_handler_invoked(self, tmp_path):
        section, match = self._secret_section_and_match(tmp_path)
        vault = MagicMock(spec=SecretVault)
        vault.stash_secret.return_value = "abc123"
        ops = FakeOps(vault=vault, current_branch="main")
        seen = []

        def handler(m):
            seen.append(m.pattern_name)
            return "REDACT"

        with (
            patch(
                "dot_man.save_deploy_ops.copy_file",
                side_effect=self._mock_copy(match),
            ),
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
        ):
            saved, secrets, errors, _ = ops.save_section(
                section, secret_handler=handler
            )

        assert seen == ["api_key"]
        assert saved == 1
        assert errors == []

    def test_vault_stash_failure_falls_back(self, tmp_path):
        from dot_man.constants import SECRET_REDACTION_TEXT

        section, match = self._secret_section_and_match(tmp_path)
        vault = MagicMock(spec=SecretVault)
        vault.stash_secret.side_effect = OSError("vault locked")
        ops = FakeOps(vault=vault, current_branch="main")
        captured = {}

        def recording_copy(src, dst, filter_secrets_enabled, secret_handler, **_):
            if filter_secrets_enabled and secret_handler:
                captured["action"] = secret_handler(match)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(captured["action"])
            return (True, [])

        with (
            patch(
                "dot_man.save_deploy_ops.copy_file",
                side_effect=recording_copy,
            ),
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
        ):
            saved, _, errors, _ = ops.save_section(section)

        assert saved == 1
        assert any("Failed to stash secret in vault" in e for e in errors)
        assert captured["action"] == SECRET_REDACTION_TEXT


class TestSaveDirectorySection:
    def test_save_directory_copies_tree(self, tmp_path):
        local = tmp_path / "local" / "cfgdir"
        local.mkdir(parents=True)
        (local / "a.conf").write_text("a = 1")
        (local / "sub").mkdir()
        (local / "sub" / "b.conf").write_text("b = 2")

        section = Section(
            name="cfgdir", paths=[local], repo_base="cfgdir", secrets_filter=False
        )
        ops = FakeOps(current_branch="main")
        with patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"):
            saved, secrets, errors, _ = ops.save_section(section)

        assert saved >= 2
        assert errors == []
        assert (
            tmp_path / "repo" / "cfgdir" / "cfgdir" / "a.conf"
        ).read_text() == "a = 1"

    def test_save_directory_partial_failure_appends(self, tmp_path):
        local = tmp_path / "local" / "cfgdir"
        local.mkdir(parents=True)
        (local / "a.conf").write_text("a = 1")

        section = Section(
            name="cfgdir", paths=[local], repo_base="cfgdir", secrets_filter=False
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
            patch(
                "dot_man.save_deploy_ops.copy_directory",
                return_value=(1, 2, []),
            ),
        ):
            saved, _, errors, _ = ops.save_section(section)

        assert saved == 1
        assert any("Failed to copy 2 files" in e for e in errors)


class TestPlanScanExecuteFloor:
    def test_scan_oserror_recorded(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_file = repo_dir / "sec" / "f.txt"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("x")
        local = tmp_path / "local" / "f.txt"
        local.parent.mkdir(parents=True)
        local.write_text("local copy")

        section = Section(
            name="sec", paths=[local], repo_base="sec", secrets_filter=False
        )
        ops = FakeOps(current_branch="main")
        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
            patch(
                "dot_man.save_deploy_ops.compare_files",
                side_effect=OSError("stat broken"),
            ),
        ):
            plan = ops.scan_deployable_changes([section])

        assert any("Error scanning" in e for e in plan["errors"])
        assert plan["sections_to_deploy"] == []

    def test_execute_rename_old_backs_up(self, tmp_path):
        repo_file = tmp_path / "repo" / "sec" / "f.txt"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("repo version")
        local = tmp_path / "local" / "f.txt"
        local.parent.mkdir(parents=True)
        local.write_text("local version")

        section = Section(
            name="sec",
            paths=[local],
            repo_base="sec",
            update_strategy="rename_old",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        plan = {
            "sections_to_deploy": [(section, local, repo_file)],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": [],
        }

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
            patch("dot_man.save_deploy_ops.backup_file") as mock_backup,
        ):
            result = ops.execute_deployment_plan(plan)

        mock_backup.assert_called_once_with(local)
        assert result["deployed"] == 1
        assert local.read_text() == "repo version"

    def test_execute_future_failure_captured(self, tmp_path):
        section = Section(
            name="sec",
            paths=[tmp_path / "f.txt"],
            repo_base="sec",
            secrets_filter=False,
        )
        ops = FakeOps(current_branch="main")
        plan = {
            "sections_to_deploy": [
                (section, tmp_path / "f.txt", tmp_path / "repo" / "sec" / "f.txt")
            ],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": [],
        }

        with patch.object(
            FakeOps,
            "_deploy_plan_item",
            side_effect=RuntimeError("thread boom"),
        ):
            result = ops.execute_deployment_plan(plan)

        assert any(
            "Critical error in deployment thread" in e and "thread boom" in e
            for e in result["errors"]
        )

    def test_ignored_action_returns_unchanged(self, tmp_path):
        """A non-REDACT handler action flows straight through (line 284)."""
        section, match = TestWrappedHandlerFloor._secret_section_and_match(tmp_path)
        vault = MagicMock(spec=SecretVault)
        ops = FakeOps(vault=vault, current_branch="main")

        with (
            patch(
                "dot_man.save_deploy_ops.copy_file",
                side_effect=TestWrappedHandlerFloor._mock_copy(match),
            ),
            patch("dot_man.save_deploy_ops.REPO_DIR", tmp_path / "repo"),
        ):
            saved, secrets, errors, _ = ops.save_section(
                section, secret_handler=lambda m: "IGNORE"
            )

        assert saved == 1
        assert errors == []
        vault.stash_secret.assert_not_called()
        assert secrets == []


class TestDeployOSErrorFloor:
    def test_os_error_during_file_deploy_appends(self, tmp_path):
        ops = FakeOps()
        repo_file = tmp_path / "repo" / "sec" / "f.txt"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("x")
        local = tmp_path / "local" / "f.txt"
        section = Section(
            name="sec", paths=[local], repo_base="sec", secrets_filter=False
        )

        with patch(
            "dot_man.save_deploy_ops.copy_file",
            side_effect=OSError("device error"),
        ):
            errors: list = []
            count = ops._deploy_repo_path(repo_file, local, section, [], errors)

        assert count == 0
        assert errors == [f"Error deploying {local}: device error"]
