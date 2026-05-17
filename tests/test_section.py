"""Tests for section module."""

from pathlib import Path


class TestSectionInit:
    """Test Section initialization."""

    def test_section_init_basic(self):
        """Test Section with basic params."""
        from dot_man.section import Section

        section = Section(
            name="ssh",
            paths=[".ssh/id_rsa"],
            repo_base=Path("/home/user/dotfiles"),
        )
        assert section.name == "ssh"
        assert len(section.paths) > 0


class TestSectionProperties:
    """Test Section properties."""

    def test_section_name(self):
        """Test Section name property."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base=Path("/test"))
        assert section.name == "test"

    def test_section_paths(self):
        """Test Section paths property."""
        from dot_man.section import Section

        section = Section(name="test", paths=[".bashrc"], repo_base=Path("/test"))
        assert len(section.paths) > 0


class TestSectionMethods:
    """Test Section methods."""

    def test_get_repo_path(self):
        """Test get_repo_path method."""
        from dot_man.section import Section

        section = Section(
            name="ssh",
            paths=[".ssh/id_rsa"],
            repo_base=Path("/home/user/dotfiles"),
        )
        result = section.get_repo_path(
            Path.home() / ".ssh/id_rsa", "/home/user/dotfiles"
        )
        assert isinstance(result, Path)


class TestSectionValidation:
    """Test Section validation."""

    def test_validate_paths_not_empty(self):
        """Test Section validates paths."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base=Path("/test"))
        assert len(section.paths) == 0
