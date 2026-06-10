"""Tests for status_ops module."""

from unittest.mock import MagicMock, patch

from dot_man.config import Section
from dot_man.constants import REPO_DIR
from dot_man.status_ops import StatusMixin


class FakeOps(StatusMixin):
    """Minimal StatusMixin subclass for testing."""

    def __init__(
        self, sections=None, current_branch="main", global_config=None, repo_dir=None
    ):
        self._sections = sections or {}
        self._current_branch = current_branch
        self._global_config = global_config or MagicMock()
        self._repo_dir = repo_dir or REPO_DIR

    @property
    def global_config(self):
        return self._global_config

    @property
    def current_branch(self):
        return self._current_branch

    def get_sections(self):
        return list(self._sections.keys())

    def get_section(self, name):
        return self._sections[name]

    def iter_section_paths(self, section):
        for local_path in section.paths:
            repo_path = section.get_repo_path(local_path, self._repo_dir)
            if local_path.is_file() and repo_path.exists():
                yield local_path, repo_path, "MODIFIED"
            elif local_path.is_file() and not repo_path.exists():
                yield local_path, repo_path, "NEW"
            elif local_path.is_dir():
                if local_path.exists() and repo_path.exists():
                    yield local_path, repo_path, "MODIFIED"
            else:
                yield local_path, repo_path, "DELETED"


# ─── audit ───────────────────────────────────────────────


class TestAudit:
    """Test audit method."""

    def test_audit_no_sections(self):
        """audit with no sections should return empty list."""
        ops = FakeOps(sections={})
        result = ops.audit()
        assert result == []

    def test_audit_clean_section(self, tmp_path):
        """audit should return empty for section with no secrets."""
        config_dir = tmp_path / ".config"
        config_dir.mkdir(parents=True)
        nvim_file = config_dir / "init.lua"
        nvim_file.write_text("-- safe config")

        section = Section(
            name="nvim",
            paths=[nvim_file],
            secrets_filter=False,
        )
        ops = FakeOps(sections={"nvim": section}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", tmp_path):
            result = ops.audit()
            assert result == []

    def test_audit_with_secrets(self, tmp_path):
        """audit should detect secrets in files using known patterns."""
        secret_file = tmp_path / "test_secret"
        # Use a known detectible secret pattern: private key
        secret_file.write_text(
            "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA\n-----END OPENSSH PRIVATE KEY-----\n"
        )

        section = Section(
            name="test",
            paths=[secret_file],
            repo_path="test_secret",
            secrets_filter=True,
        )
        ops = FakeOps(sections={"test": section}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", tmp_path):
            result = ops.audit()
            section_name, matches = result[0]
            assert section_name == "test"
            assert len(matches) == 1
            assert matches[0].pattern_name == "Private Key"


# ─── pre_push_audit ──────────────────────────────────────


class TestPrePushAudit:
    """Test pre_push_audit method."""

    def test_pre_push_clean(self):
        """pre_push_audit should return True when no secrets."""
        ops = FakeOps(sections={})
        with patch.object(ops, "audit", return_value=[]):
            assert ops.pre_push_audit() is True

    def test_pre_push_strict_mode(self):
        """pre_push_audit should return False in strict mode with secrets."""
        gc = MagicMock()
        gc.strict_mode = True
        ops = FakeOps(global_config=gc)
        with patch.object(ops, "audit", return_value=[("test", [MagicMock()])]):
            assert ops.pre_push_audit() is False


# ─── get_detailed_status ─────────────────────────────────


class TestGetDetailedStatus:
    """Test get_detailed_status method."""

    def test_no_sections(self):
        """No sections should yield nothing."""
        ops = FakeOps(sections={})
        result = list(ops.get_detailed_status())
        assert result == []

    def test_single_section_file(self, tmp_path):
        """Single file section should yield status item."""
        repo = tmp_path / "repo" / "bashrc" / ".bashrc"
        repo.parent.mkdir(parents=True)
        repo.write_text("content")

        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(sections={"bash": section}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", tmp_path / "repo"):
            items = list(ops.get_detailed_status())
            assert len(items) == 1
            assert items[0]["section"] == "bash"
            assert items[0]["inherits"] == []

    def test_multiple_sections(self, tmp_path):
        """Multiple sections should all appear in status."""
        repo = tmp_path / "repo"
        (repo / "bashrc" / ".bashrc").parent.mkdir(parents=True)
        (repo / "bashrc" / ".bashrc").write_text("bash")
        (repo / "nvim" / "nvim" / "init.lua").parent.mkdir(parents=True)
        (repo / "nvim" / "nvim" / "init.lua").write_text("nvim")

        local_bash = tmp_path / "local" / ".bashrc"
        local_bash.parent.mkdir(parents=True)
        local_bash.write_text("bash")

        local_nvim = tmp_path / "local" / ".config" / "nvim"
        local_nvim.mkdir(parents=True)
        (local_nvim / "init.lua").write_text("nvim")

        bash_section = Section(
            name="bash",
            paths=[local_bash],
            repo_base="bashrc",
            secrets_filter=False,
        )
        nvim_section = Section(
            name="nvim",
            paths=[local_nvim],
            repo_base="nvim",
            secrets_filter=False,
        )
        ops = FakeOps(
            sections={"bash": bash_section, "nvim": nvim_section},
            current_branch="main",
            repo_dir=repo,
        )
        with patch("dot_man.status_ops.REPO_DIR", repo):
            items = list(ops.get_detailed_status())
            sections = {i["section"] for i in items}
            assert "bash" in sections
            assert "nvim" in sections


# ─── get_status_summary ──────────────────────────────────


class TestGetStatusSummary:
    """Test get_status_summary method."""

    def test_empty_summary(self):
        """Empty state should have zero counts."""
        ops = FakeOps(sections={})
        summary = ops.get_status_summary()
        assert summary["sections"] == 0
        assert summary["total_paths"] == 0
        assert summary["branch"] == "main"

    def test_summary_with_data(self, tmp_path):
        """Summary should count files by status."""
        repo = tmp_path / "repo"
        (repo / "bashrc" / ".bashrc").parent.mkdir(parents=True)
        (repo / "bashrc" / ".bashrc").write_text("content")

        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(sections={"bash": section}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo):
            summary = ops.get_status_summary()
            assert summary["sections"] == 1
            assert summary["total_paths"] == 1
            assert summary["branch"] == "main"


# ─── get_orphaned_files ──────────────────────────────────


class TestGetOrphanedFiles:
    """Test get_orphaned_files method."""

    def test_no_orphans(self, tmp_path):
        """No orphaned files when all repo files are tracked."""
        repo_dir = tmp_path / "repo"
        tracked_file = repo_dir / "bashrc" / ".bashrc"
        tracked_file.parent.mkdir(parents=True)
        tracked_file.write_text("content")

        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(sections={"bash": section}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo_dir):
            orphans = ops.get_orphaned_files()
            assert tracked_file not in orphans

    def test_with_orphans(self, tmp_path):
        """Files not tracked by any section should be orphans."""
        repo_dir = tmp_path / "repo"
        (repo_dir / "bashrc" / ".bashrc").parent.mkdir(parents=True)
        (repo_dir / "bashrc" / ".bashrc").write_text("tracked")
        (repo_dir / "orphan.txt").write_text("orphan")

        local = tmp_path / "local" / ".bashrc"
        local.parent.mkdir(parents=True)
        local.write_text("content")

        section = Section(
            name="bash",
            paths=[local],
            repo_base="bashrc",
            secrets_filter=False,
        )
        ops = FakeOps(sections={"bash": section}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo_dir):
            orphans = ops.get_orphaned_files()
            assert any("orphan.txt" in str(o) for o in orphans)

    def test_orphans_internal_files_excluded(self, tmp_path):
        """Internal files like .gitignore should not be orphans."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / ".gitignore").write_text("*.swp")
        (repo_dir / "dot-man.toml").write_text("[test]")

        ops = FakeOps(sections={}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo_dir):
            orphans = ops.get_orphaned_files()
            assert not any(".gitignore" in str(o) for o in orphans)
            assert not any("dot-man.toml" in str(o) for o in orphans)


# ─── clean_orphaned_files ────────────────────────────────


class TestCleanOrphanedFiles:
    """Test clean_orphaned_files method."""

    def test_dry_run(self, tmp_path):
        """Dry run should return orphans without deleting."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(parents=True)
        orphan = repo_dir / "orphan.txt"
        orphan.write_text("orphan")

        ops = FakeOps(sections={}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo_dir):
            result = ops.clean_orphaned_files(dry_run=True)
            assert orphan in result
            assert orphan.exists()

    def test_delete_orphans(self, tmp_path):
        """Clean should delete orphaned files."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(parents=True)
        orphan = repo_dir / "orphan.txt"
        orphan.write_text("orphan")

        ops = FakeOps(sections={}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo_dir):
            result = ops.clean_orphaned_files(dry_run=False)
            assert orphan in result
            assert not orphan.exists()

    def test_delete_empty_parent(self, tmp_path):
        """Clean should remove empty parent directories."""
        repo_dir = tmp_path / "repo"
        nested = repo_dir / "empty_dir" / "orphan.txt"
        nested.parent.mkdir(parents=True)
        nested.write_text("orphan")

        ops = FakeOps(sections={}, current_branch="main")
        with patch("dot_man.status_ops.REPO_DIR", repo_dir):
            ops.clean_orphaned_files(dry_run=False)
            assert not nested.exists()
            assert not nested.parent.exists()

    def test_clean_os_error_logged(self, tmp_path):
        """OSError during clean should be caught and logged."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(parents=True)
        orphan = repo_dir / "orphan.txt"
        orphan.write_text("orphan")

        ops = FakeOps(sections={}, current_branch="main")
        with (
            patch("dot_man.status_ops.REPO_DIR", repo_dir),
            patch(
                "dot_man.status_ops.Path.unlink",
                side_effect=OSError("Permission denied"),
            ),
        ):
            result = ops.clean_orphaned_files(dry_run=False)
            assert result == []
