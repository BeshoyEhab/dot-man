"""Tests for symlink deploy mode and deploy_method field."""

from pathlib import Path

from dot_man.files import (
    create_symlink,
    deploy_directory_with_symlinks,
    deploy_file_or_symlink,
)
from dot_man.section import Section


class TestCreateSymlink:
    """Tests for create_symlink function."""

    def test_create_symlink_basic(self, tmp_path):
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("hello")

        result = create_symlink(source, dest)
        assert result is True
        assert dest.is_symlink()
        assert dest.resolve() == source.resolve()
        assert dest.read_text() == "hello"

    def test_create_symlink_source_not_exists(self, tmp_path):
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"

        result = create_symlink(source, dest)
        assert result is False
        assert not dest.exists()

    def test_create_symlink_overwrites_existing(self, tmp_path):
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("new")
        dest.write_text("old")

        result = create_symlink(source, dest)
        assert result is True
        assert dest.is_symlink()
        assert dest.read_text() == "new"

    def test_create_symlink_skips_correct_symlink(self, tmp_path):
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("hello")
        dest.symlink_to(source)

        result = create_symlink(source, dest)
        assert result is True
        assert dest.is_symlink()

    def test_create_symlink_fixes_wrong_symlink(self, tmp_path):
        source = tmp_path / "source.txt"
        wrong = tmp_path / "wrong.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("correct")
        wrong.write_text("wrong")
        dest.symlink_to(wrong)

        result = create_symlink(source, dest)
        assert result is True
        assert dest.resolve() == source.resolve()


class TestDeployFileOrSymlink:
    """Tests for deploy_file_or_symlink function."""

    def test_deploy_copy(self, tmp_path):
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("content")

        success, secrets = deploy_file_or_symlink(source, dest, deploy_method="copy")
        assert success is True
        assert secrets == []
        assert dest.exists()
        assert dest.read_text() == "content"
        assert not dest.is_symlink()

    def test_deploy_symlink(self, tmp_path):
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("content")

        success, secrets = deploy_file_or_symlink(source, dest, deploy_method="symlink")
        assert success is True
        assert secrets == []
        assert dest.is_symlink()
        assert dest.read_text() == "content"


class TestDeployDirectoryWithSymlinks:
    """Tests for deploy_directory_with_symlinks."""

    def test_basic_directory_symlink(self, tmp_path):
        source = tmp_path / "source_dir"
        dest = tmp_path / "dest_dir"
        source.mkdir()
        (source / "file1.txt").write_text("one")
        (source / "file2.txt").write_text("two")

        symlinked, failed = deploy_directory_with_symlinks(source, dest)
        assert symlinked == 2
        assert failed == 0
        assert (dest / "file1.txt").is_symlink()
        assert (dest / "file2.txt").is_symlink()
        assert (dest / "file1.txt").read_text() == "one"

    def test_with_exclude_patterns(self, tmp_path):
        source = tmp_path / "source_dir"
        dest = tmp_path / "dest_dir"
        source.mkdir()
        (source / "keep.txt").write_text("keep")
        (source / "ignore.log").write_text("ignore")

        symlinked, failed = deploy_directory_with_symlinks(
            source, dest, exclude_patterns=["*.log"]
        )
        assert symlinked == 1
        assert failed == 0
        assert (dest / "keep.txt").exists()
        assert not (dest / "ignore.log").exists()

    def test_with_include_patterns(self, tmp_path):
        source = tmp_path / "source_dir"
        dest = tmp_path / "dest_dir"
        source.mkdir()
        (source / "file.conf").write_text("config")
        (source / "file.txt").write_text("text")

        symlinked, failed = deploy_directory_with_symlinks(
            source, dest, include_patterns=["*.conf"]
        )
        assert symlinked == 1
        assert failed == 0
        assert (dest / "file.conf").exists()
        assert not (dest / "file.txt").exists()


class TestSectionDeployMethod:
    """Tests for Section with deploy_method."""

    def test_section_default_deploy_method(self):
        section = Section(name="test", paths=[Path("/tmp/test")], repo_base="test")
        assert section.deploy_method == "copy"

    def test_section_symlink_deploy_method(self):
        section = Section(
            name="test",
            paths=[Path("/tmp/test")],
            repo_base="test",
            deploy_method="symlink",
        )
        assert section.deploy_method == "symlink"

    def test_section_to_dict_includes_deploy_method(self):
        section = Section(
            name="test",
            paths=[Path("/tmp/test")],
            repo_base="test",
            deploy_method="symlink",
        )
        data = section.to_dict()
        assert data.get("deploy_method") == "symlink"

    def test_section_to_dict_omits_default(self):
        section = Section(name="test", paths=[Path("/tmp/test")], repo_base="test")
        data = section.to_dict()
        assert "deploy_method" not in data
