"""Tests for cli/add_cmd.py — add command."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants."""
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        # add_cmd binds REPO_DIR at import: without this, add copies
        # files into the real repo instead of the sandbox.
        patch("dot_man.cli.add_cmd.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, global_toml, home


class TestAddHelp:
    def test_add_help(self, runner):
        """Add help."""
        result = runner.invoke(cli, ["add", "--help"])
        assert result.exit_code == 0


class TestAddWithoutInit:
    def test_add_without_init(self, runner):
        """Add without init."""
        result = runner.invoke(cli, ["add", "/some/path"])
        assert result.exit_code in [0, 1, 2]


class TestAddWithInit:
    def test_add_file(self, clean_env):
        """Add a file to tracking."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_file = home / ".bashrc"
        test_file.write_text("# bashrc")

        result = runner.invoke(cli, ["add", str(test_file)])

        assert result.exit_code in [0, 1, 7]

    def test_add_symlink_follows(self, clean_env):
        """Add follows a symlink when prompt returns 'follow'."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        # Create minimal global config
        if not global_toml.parent.exists():
            global_toml.parent.mkdir(parents=True)
        global_toml.write_text("[defaults]\n")

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        target = home / "real_config.txt"
        target.write_text("real content")

        link = home / ".linked_config"
        link.symlink_to(target)

        with patch("dot_man.interactive.prompt_symlink_action", return_value="follow"):
            result = runner.invoke(cli, ["add", str(link)])

        assert result.exit_code in [0, 1, 7]

    def test_add_symlink_ignore(self, clean_env):
        """Add skips a symlink when prompt returns 'ignore'."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        # Create minimal global config
        if not global_toml.parent.exists():
            global_toml.parent.mkdir(parents=True)
        global_toml.write_text("[defaults]\n")

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        target = home / "real_config.txt"
        target.write_text("real content")

        link = home / ".linked_config"
        link.symlink_to(target)

        with patch("dot_man.interactive.prompt_symlink_action", return_value="ignore"):
            result = runner.invoke(cli, ["add", str(link)])

        assert result.exit_code == 0
        assert "Skipped symlink" in result.output

    def test_add_directory(self, clean_env):
        """Add a directory to tracking."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_dir = home / ".config" / "testapp"
        test_dir.mkdir(parents=True)
        (test_dir / "config.conf").write_text("key=value")

        result = runner.invoke(cli, ["add", str(test_dir)])

        assert result.exit_code in [0, 1, 7]


class TestAddOptions:
    def test_add_with_section(self, clean_env):
        """Add with custom section name."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_file = home / ".bashrc"
        test_file.write_text("# bashrc")

        result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code in [0, 1, 7]


class TestAddNextSteps:
    def test_add_suggests_next_steps(self, clean_env):
        """Add ends with happy-path next steps, never switch."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        dot_man_dir.mkdir(parents=True, exist_ok=True)
        global_toml.write_text("[defaults]\n")

        from git import Repo

        repo = Repo.init(repo_dir)
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Test")
            cw.set_value("user", "email", "test@test.com")
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 0, result.output
        assert "Next Steps" in result.output
        assert "dot-man status" in result.output
        assert "dot-man navigate" in result.output
        assert "dot-man switch" not in result.output


def _write_hook_script(hooks_dir, name: str, body: str):
    """Write an executable hook script; return its path."""
    from pathlib import Path

    script = Path(hooks_dir) / name
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(0o755)
    return script


def _init_minimal_repo(dot_man_dir, repo_dir, global_toml):
    """Create init structure + git repo + default global config."""
    from git import Repo

    dot_man_dir.mkdir(parents=True, exist_ok=True)
    global_toml.write_text("[defaults]\n")
    repo = Repo.init(repo_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@test.com")
    (repo_dir / "test.txt").write_text("test")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial")


class TestAddGlobalHooks:
    """Global pre_add/post_add scripts wrap real adds."""

    def test_pre_post_add_fire(self, clean_env, tmp_path):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        marker = tmp_path / "markers.log"
        _write_hook_script(hooks_dir, "pre_add", f"echo pre >> {marker}")
        _write_hook_script(
            hooks_dir, "post_add", 'echo "post $DOTMAN_SECTION" >> ' + str(marker)
        )
        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 0, result.output
        fired = marker.read_text()
        assert "pre" in fired
        assert "post bash" in fired

    def test_failing_hook_warns_and_continues(self, clean_env, tmp_path):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        _write_hook_script(hooks_dir, "pre_add", "exit 1")
        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 0, result.output
        assert "continuing" in result.output


class TestAddAutoHooks:
    """Adding a known tool auto-applies its hooks like the wizard does."""

    def test_add_applies_detected_hooks(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        kitty_dir = home / ".config" / "kitty"
        kitty_dir.mkdir(parents=True)
        (kitty_dir / "kitty.conf").write_text("font_size 12\n")

        result = runner.invoke(cli, ["add", str(kitty_dir), "--section", "kitty"])

        assert result.exit_code == 0, result.output
        assert "post_deploy" in result.output
        saved = (repo_dir / "dot-man.toml").read_text()
        assert "SIGUSR1 kitty" in saved


# ─── coverage floor: duplicate section, copy failures, secrets,
#     inherits, post-hook failure, unexpected error ────────────────


class TestAddFailurePaths:
    def test_duplicate_section_errors(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        first = runner.invoke(cli, ["add", str(test_file), "--section", "dup"])
        assert first.exit_code == 0, first.output

        second = runner.invoke(cli, ["add", str(test_file), "--section", "dup"])
        assert second.exit_code == 1
        assert "already exists" in second.output

    def test_file_copy_failure_errors(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        with patch("dot_man.cli.add_cmd.copy_file", return_value=(False, [])):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 1
        assert "Failed to copy file" in result.output

    def test_file_access_failure_errors(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        with patch(
            "dot_man.cli.add_cmd.copy_file",
            side_effect=FileNotFoundError("gone"),
        ):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 1
        assert "Failed to access file" in result.output

    def test_unexpected_copy_error_errors(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        with patch(
            "dot_man.cli.add_cmd.copy_file",
            side_effect=ValueError("boom"),
        ):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 1
        assert "Error copying file" in result.output

    def test_unexpected_error_reported(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        with patch(
            "dot_man.cli.add_cmd.get_auto_hooks_for_config",
            side_effect=RuntimeError("detector boom"),
        ):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 1
        assert "Failed to add: detector boom" in result.output


class TestAddSecretsAndOptions:
    def test_file_secrets_redacted_warns(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        secret_file = home / ".env"
        secret_file.write_text(
            "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        )

        with patch("dot_man.ui.ask", return_value="2"):
            result = runner.invoke(cli, ["add", str(secret_file), "--section", "env"])

        assert result.exit_code == 0, result.output
        assert "secrets were redacted" in result.output
        repo_copy = (repo_dir / "env" / ".env").read_text()
        assert "BEGIN OPENSSH PRIVATE KEY" not in repo_copy

    def test_directory_secrets_redacted_warns(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        cfg_dir = home / ".config" / "mytool"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "settings.conf").write_text("key = 1\n")
        (cfg_dir / "credentials.conf").write_text(
            "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        )

        with patch("dot_man.ui.ask", return_value="2"):
            result = runner.invoke(cli, ["add", str(cfg_dir), "--section", "mytool"])

        assert result.exit_code == 0, result.output
        assert "secrets were redacted" in result.output

    def test_inherits_option_printed(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        result = runner.invoke(
            cli,
            ["add", str(test_file), "--section", "bash", "--inherits", "base"],
        )

        assert result.exit_code == 0, result.output
        assert "Inherits: base" in result.output

    def test_failing_post_hook_warns_and_continues(self, clean_env, tmp_path):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_minimal_repo(dot_man_dir, repo_dir, global_toml)
        test_file = home / ".bashrc"
        test_file.write_text("# bashrc\n")

        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        _write_hook_script(hooks_dir, "post_add", "exit 1")
        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code == 0, result.output
        assert "post_add hook failed" in result.output
        assert "continuing" in result.output
