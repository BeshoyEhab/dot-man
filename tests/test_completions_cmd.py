"""Tests for completions_cmd.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestCompletionsPackage:
    """The completions directory must be a real importable package.

    Without an ``__init__.py`` it is only a namespace package, so ``__file__``
    is ``None`` and the completions command crashes locating its scripts.
    """

    def test_package_has_file_and_scripts(self):
        import importlib

        pkg = importlib.import_module("dot_man.completions")
        assert pkg.__file__ is not None
        scripts = Path(pkg.__file__).parent
        assert (scripts / "dot-man.bash").is_file()
        assert (scripts / "_dot-man.zsh").is_file()
        assert (scripts / "dot-man.fish").is_file()

    def test_source_only_command_works_unpatched(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = CliRunner().invoke(cli, ["completions", "--source-only"])
        assert result.exit_code == 0, result.output
        assert "dot-man.bash" in result.output


class TestCompletionsCommand:
    def _setup(self, tmp_path):
        """Create mock completions scripts and return module ref."""
        src_dir = tmp_path / "completions_src"
        src_dir.mkdir()
        (src_dir / "dot-man.bash").write_text("# bash completion")
        (src_dir / "_dot-man.zsh").write_text("# zsh completion")
        (src_dir / "dot-man.fish").write_text("# fish completion")
        import dot_man.completions as pkg

        return src_dir, pkg

    def test_source_only_bash(self, tmp_path):
        src_dir, pkg = self._setup(tmp_path)
        runner = CliRunner()
        with patch.object(pkg, "__file__", str(src_dir / "__init__.py")):
            result = runner.invoke(
                cli, ["completions", "--source-only", "--shell", "bash"]
            )
        assert result.exit_code == 0
        assert "source" in result.output

    def test_source_only_zsh(self, tmp_path):
        src_dir, pkg = self._setup(tmp_path)
        runner = CliRunner()
        with patch.object(pkg, "__file__", str(src_dir / "__init__.py")):
            result = runner.invoke(
                cli, ["completions", "--source-only", "--shell", "zsh"]
            )
        assert result.exit_code == 0
        assert "source" in result.output

    def test_source_only_fish(self, tmp_path):
        src_dir, pkg = self._setup(tmp_path)
        runner = CliRunner()
        with patch.object(pkg, "__file__", str(src_dir / "__init__.py")):
            result = runner.invoke(
                cli, ["completions", "--source-only", "--shell", "fish"]
            )
        assert result.exit_code == 0
        assert "source" in result.output

    def test_source_only_all(self, tmp_path):
        src_dir, pkg = self._setup(tmp_path)
        runner = CliRunner()
        with patch.object(pkg, "__file__", str(src_dir / "__init__.py")):
            result = runner.invoke(
                cli, ["completions", "--source-only", "--shell", "all"]
            )
        assert result.exit_code == 0
        assert "bash" in result.output.lower()
        assert "zsh" in result.output.lower()
        assert "fish" in result.output.lower()

    def test_install_bash(self, tmp_path):
        src_dir, pkg = self._setup(tmp_path)
        runner = CliRunner()
        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            result = runner.invoke(cli, ["completions", "--shell", "bash"])
        assert result.exit_code == 0
        bash_dest = (
            tmp_path
            / ".local"
            / "share"
            / "bash-completion"
            / "completions"
            / "dot-man"
        )
        assert bash_dest.exists()
        assert bash_dest.read_text() == "# bash completion"

    def test_install_all(self, tmp_path):
        src_dir, pkg = self._setup(tmp_path)
        runner = CliRunner()
        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            result = runner.invoke(cli, ["completions"])
        assert result.exit_code == 0
        bash_dest = (
            tmp_path
            / ".local"
            / "share"
            / "bash-completion"
            / "completions"
            / "dot-man"
        )
        zsh_dest = tmp_path / ".local" / "share" / "zsh" / "site-functions" / "_dot-man"
        fish_dest = tmp_path / ".config" / "fish" / "completions" / "dot-man.fish"
        assert bash_dest.exists()
        assert zsh_dest.exists()
        assert fish_dest.exists()
        assert "Restart your shell" in result.output


class TestRunInstall:
    def test_run_install_bash(self, tmp_path):
        src_dir = tmp_path / "completions_src"
        src_dir.mkdir()
        (src_dir / "dot-man.bash").write_text("# bash")
        import dot_man.completions as pkg

        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            from dot_man.cli.completions_cmd import run_install

            run_install()

        bash_dest = (
            tmp_path
            / ".local"
            / "share"
            / "bash-completion"
            / "completions"
            / "dot-man"
        )
        assert bash_dest.exists()
        assert bash_dest.read_text() == "# bash"

    def test_run_install_zsh(self, tmp_path):
        src_dir = tmp_path / "completions_src"
        src_dir.mkdir()
        (src_dir / "_dot-man.zsh").write_text("# zsh")
        import dot_man.completions as pkg

        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            from dot_man.cli.completions_cmd import run_install

            run_install()

        zsh_dest = tmp_path / ".local" / "share" / "zsh" / "site-functions" / "_dot-man"
        assert zsh_dest.exists()
        assert zsh_dest.read_text() == "# zsh"

    def test_run_install_fish(self, tmp_path):
        src_dir = tmp_path / "completions_src"
        src_dir.mkdir()
        (src_dir / "dot-man.fish").write_text("# fish")
        import dot_man.completions as pkg

        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            from dot_man.cli.completions_cmd import run_install

            run_install()

        fish_dest = tmp_path / ".config" / "fish" / "completions" / "dot-man.fish"
        assert fish_dest.exists()
        assert fish_dest.read_text() == "# fish"

    def test_run_install_overwrites_stale_existing(self, tmp_path):
        """Stale completions from older versions must be replaced on install."""
        src_dir = tmp_path / "completions_src"
        src_dir.mkdir()
        (src_dir / "dot-man.bash").write_text("# new version")
        bash_dest = (
            tmp_path
            / ".local"
            / "share"
            / "bash-completion"
            / "completions"
            / "dot-man"
        )
        bash_dest.parent.mkdir(parents=True)
        bash_dest.write_text("# old broken version")
        import dot_man.completions as pkg

        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            from dot_man.cli.completions_cmd import run_install

            run_install()

        assert bash_dest.read_text() == "# new version"

    def test_run_install_skips_identical_existing(self, tmp_path):
        """Identical installed scripts are left untouched (no rewrite)."""
        src_dir = tmp_path / "completions_src"
        src_dir.mkdir()
        (src_dir / "dot-man.bash").write_text("# same")
        bash_dest = (
            tmp_path
            / ".local"
            / "share"
            / "bash-completion"
            / "completions"
            / "dot-man"
        )
        bash_dest.parent.mkdir(parents=True)
        bash_dest.write_text("# same")
        dest_mtime = bash_dest.stat().st_mtime_ns
        import dot_man.completions as pkg

        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            from dot_man.cli.completions_cmd import run_install

            run_install()

        assert bash_dest.read_text() == "# same"
        assert bash_dest.stat().st_mtime_ns == dest_mtime
