"""Tests for cli/deploy_cmd.py — deploy command."""

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
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, global_toml, home


def _init_repo(repo_dir):
    """Initialize a real git repo with initial commit, branch 'main'."""
    from git import Repo

    repo = Repo.init(repo_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@test.com")
    (repo_dir / ".gitkeep").write_text("")
    repo.index.add([".gitkeep"])
    repo.index.commit("Initial")
    repo.git.branch("-m", "main")
    return repo


def _setup_global_toml(global_toml, branch="main"):
    """Write a minimal global.toml."""
    global_toml.parent.mkdir(parents=True, exist_ok=True)
    global_toml.write_text(f'[dot-man]\ncurrent_branch = "{branch}"\n')


def _setup_empty_config(repo_dir):
    """Create a dot-man.toml with zero sections so get_sections returns []."""
    from git import Repo

    dot_man_toml = repo_dir / "dot-man.toml"
    dot_man_toml.write_text("# no sections yet\n")

    repo = Repo(repo_dir)
    repo.index.add(["dot-man.toml"])
    repo.index.commit("Empty config")


def _setup_bashrc_section(repo_dir, content='alias ll="ls -la"\n'):
    """Create dot-man.toml with a bashrc section and a .bashrc repo file.

    DotManConfig.get_section passes repo_base=settings.get("repo_base", name).
    Section name "bashrc" → repo_base defaults to "bashrc"
    → repo_path = repo_dir / "bashrc" / ".bashrc"
    """
    from git import Repo

    dot_man_toml = repo_dir / "dot-man.toml"
    dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]
""")

    repo_file = repo_dir / "bashrc" / ".bashrc"
    repo_file.parent.mkdir(parents=True)
    repo_file.write_text(content)

    repo = Repo(repo_dir)
    repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
    repo.index.commit("Add bashrc section")
    return repo


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestDeployHelp:
    def test_deploy_help(self, runner):
        result = runner.invoke(cli, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "deploy" in result.output
        assert "BRANCH" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output

    def test_deploy_alias(self, runner):
        result = runner.invoke(cli, ["dep", "--help"])
        assert result.exit_code == 0
        assert "deploy" in result.output


# ---------------------------------------------------------------------------
# Without init
# ---------------------------------------------------------------------------


class TestDeployWithoutInit:
    def test_deploy_without_init(self, runner):
        result = runner.invoke(cli, ["deploy", "main"])
        assert result.exit_code != 0

    def test_dep_without_init(self, runner):
        result = runner.invoke(cli, ["dep", "main"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Success / failure paths with a real repo
# ---------------------------------------------------------------------------


class TestDeployWithInit:
    def test_deploy_nonexistent_branch(self, clean_env):
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        result = runner.invoke(cli, ["deploy", "nonexistent-branch"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_deploy_dry_run_no_sections(self, clean_env):
        """Dry run when the branch has no sections warns the user."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_empty_config(repo_dir)

        result = runner.invoke(cli, ["deploy", "main", "--dry-run"])

        assert result.exit_code == 0
        assert "No files configured" in result.output

    def test_deploy_force_no_sections(self, clean_env):
        """Force deploy when the branch has no sections warns the user."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_empty_config(repo_dir)

        result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "No files configured" in result.output

    def test_deploy_dry_run_with_sections(self, clean_env):
        """Dry run lists files that would be deployed."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir)

        result = runner.invoke(cli, ["deploy", "main", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry Run Summary" in result.output
        assert ".bashrc" in result.output
        assert "CREATE" in result.output

    def test_deploy_dry_run_existing_file_shows_overwrite(self, clean_env):
        """Dry run marks existing files as OVERWRITE."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, content="repo content\n")

        (home / ".bashrc").write_text("old content\n")

        result = runner.invoke(cli, ["deploy", "main", "--dry-run"])

        assert result.exit_code == 0
        assert "OVERWRITE" in result.output

    def test_deploy_creates_files(self, clean_env):
        """Deploy with --force actually writes files to the home directory."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, content='alias ll="ls -la"\n')

        assert not (home / ".bashrc").exists()

        result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0, result.output
        assert "Deployment complete" in result.output
        assert (home / ".bashrc").exists()
        assert 'alias ll="ls -la"' in (home / ".bashrc").read_text()

    def test_deploy_force_no_changes_detected(self, clean_env):
        """Deploy when local already matches repo shows no changes."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, content="same content\n")

        (home / ".bashrc").write_text("same content\n")

        result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "No changes detected" in result.output

    def test_deploy_cancelled_first_prompt(self, clean_env):
        """Destructive-operation prompt declines: deploy is aborted."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir)

        with patch("dot_man.cli.deploy_cmd.ui.confirm", return_value=False):
            result = runner.invoke(cli, ["deploy", "main"])

        assert result.exit_code == 0
        assert "Aborted" in result.output

    def test_deploy_confirms_and_proceeds(self, clean_env):
        """Both prompts confirmed, deploy proceeds."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, content="confirmed\n")

        with patch("dot_man.cli.deploy_cmd.ui.confirm", return_value=True):
            result = runner.invoke(cli, ["deploy", "main"])

        assert result.exit_code == 0
        assert "Deployment complete" in result.output
        assert (home / ".bashrc").exists()
        assert "confirmed" in (home / ".bashrc").read_text()

    def test_deploy_second_confirm_decline(self, clean_env):
        """Second confirmation (N files to deploy) declines."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, content="declined\n")

        confirm_calls = iter([True, False])

        with patch(
            "dot_man.cli.deploy_cmd.ui.confirm",
            side_effect=lambda msg: next(confirm_calls),
        ):
            result = runner.invoke(cli, ["deploy", "main"])

        assert result.exit_code == 0
        assert "Aborted" in result.output
        assert not (home / ".bashrc").exists()

    def test_deploy_dry_run_shows_hooks(self, clean_env):
        """Dry run displays pre and post hooks."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        dot_man_toml = repo_dir / "dot-man.toml"
        dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]
pre_deploy = "echo pre-hook"
post_deploy = "echo post-hook"
""")

        repo_file = repo_dir / "bashrc" / ".bashrc"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("content\n")

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
        repo.index.commit("Add with hooks")

        result = runner.invoke(cli, ["deploy", "main", "--dry-run"])

        assert result.exit_code == 0
        assert "Pre-Hooks" in result.output
        assert "Post-Hooks" in result.output
        assert "echo pre-hook" in result.output
        assert "echo post-hook" in result.output

    def test_deploy_with_hook(self, clean_env):
        """Deploy executes post-deploy hook."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        dot_man_toml = repo_dir / "dot-man.toml"
        dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]
post_deploy = "echo 'deploy hook ran'"
""")

        repo_file = repo_dir / "bashrc" / ".bashrc"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("hook_test\n")

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
        repo.index.commit("Add with hook")

        result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "post-deploy hooks" in result.output.lower()

    def test_deploy_multiple_sections(self, clean_env):
        """Deploy processes multiple sections."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        dot_man_toml = repo_dir / "dot-man.toml"
        dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]

[vimrc]
paths = ["~/.vimrc"]
""")

        bash_repo = repo_dir / "bashrc" / ".bashrc"
        bash_repo.parent.mkdir(parents=True)
        bash_repo.write_text("bash content\n")

        vim_repo = repo_dir / "vimrc" / ".vimrc"
        vim_repo.parent.mkdir(parents=True)
        vim_repo.write_text("vim content\n")

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["dot-man.toml", "bashrc/.bashrc", "vimrc/.vimrc"])
        repo.index.commit("Add multiple sections")

        result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "Deployment complete" in result.output
        assert (home / ".bashrc").exists()
        assert (home / ".vimrc").exists()

    def test_deploy_with_scan_error(self, clean_env):
        """Scan errors are printed to the user."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir)

        from dot_man.operations import get_operations

        ops = get_operations()
        with patch.object(
            ops,
            "scan_deployable_changes",
            return_value={
                "sections_to_deploy": [],
                "pre_hooks": [],
                "post_hooks": [],
                "errors": ["Scan failed for /some/path"],
            },
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "Scan failed" in result.output

    def test_deploy_keyboard_interrupt(self, clean_env):
        """KeyboardInterrupt is handled gracefully."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        with patch(
            "dot_man.operations.get_operations", side_effect=KeyboardInterrupt()
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code != 0

    def test_deploy_dotman_error(self, clean_env):
        """DotManError from operations is displayed."""
        from dot_man.exceptions import DotManError

        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        with patch(
            "dot_man.operations.get_operations",
            side_effect=DotManError("Config error", exit_code=5),
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code != 0
        assert "Config error" in result.output

    def test_deploy_generic_exception(self, clean_env):
        """Generic Exception from operations is handled."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        with patch(
            "dot_man.operations.get_operations",
            side_effect=RuntimeError("Unexpected failure"),
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code != 0
        assert "Unexpected failure" in result.output

    def test_deploy_with_pre_hook_failure(self, clean_env):
        """Pre-deploy hook failure is handled gracefully."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        dot_man_toml = repo_dir / "dot-man.toml"
        dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]
pre_deploy = "exit 1"
""")

        repo_file = repo_dir / "bashrc" / ".bashrc"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("hook_fail\n")

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
        repo.index.commit("Add with failing pre-hook")

        with patch(
            "dot_man.cli.deploy_cmd.subprocess.run",
            side_effect=OSError("command not found"),
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "Failed to run command" in result.output

    def test_deploy_with_post_hook_failure(self, clean_env):
        """Post-deploy hook failure is handled gracefully."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        dot_man_toml = repo_dir / "dot-man.toml"
        dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]
post_deploy = "exit 1"
""")

        repo_file = repo_dir / "bashrc" / ".bashrc"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("hook_fail\n")

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
        repo.index.commit("Add with failing post-hook")

        with patch(
            "dot_man.cli.deploy_cmd.subprocess.run",
            side_effect=OSError("command not found"),
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "Failed to run command" in result.output

    def test_deploy_with_pre_hook(self, clean_env):
        """Pre-deploy hook is executed."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        dot_man_toml = repo_dir / "dot-man.toml"
        dot_man_toml.write_text("""\
[bashrc]
paths = ["~/.bashrc"]
pre_deploy = "echo 'pre-hook ran'"
""")

        repo_file = repo_dir / "bashrc" / ".bashrc"
        repo_file.parent.mkdir(parents=True)
        repo_file.write_text("pre_hook_test\n")

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
        repo.index.commit("Add with pre-hook")

        result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "pre-deploy hooks" in result.output.lower()

    def test_deploy_with_execution_errors(self, clean_env):
        """Deployment errors are printed after execution."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir)

        from dot_man.operations import get_operations

        ops = get_operations()
        with patch.object(
            ops,
            "execute_deployment_plan",
            return_value={
                "deployed": 0,
                "pre_hooks": [],
                "post_hooks": [],
                "errors": ["Failed to copy /repo/file to /local/file"],
            },
        ):
            result = runner.invoke(cli, ["deploy", "main", "--force"])

        assert result.exit_code == 0
        assert "Error:" in result.output
        assert "Failed to copy" in result.output
