"""Tests for completions_cmd.py."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.interface import cli


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

    def test_run_install_skips_existing(self, tmp_path):
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
        bash_dest.write_text("# existing")
        import dot_man.completions as pkg

        with (
            patch.object(pkg, "__file__", str(src_dir / "__init__.py")),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            from dot_man.cli.completions_cmd import run_install

            run_install()

        assert bash_dest.read_text() == "# existing"
