import pytest
import os
from pathlib import Path
from dot_man.files import copy_directory
from dot_man.config import GlobalConfig, Section, DotManConfig
from dot_man.constants import DEFAULT_IGNORED_DIRECTORIES

class TestPerformanceLogic:
    """Test verification of performance optimizations and configuration logic."""

    def test_copy_directory_prunes_ignored(self, tmp_path):
        """Verify that copy_directory actually prunes ignored directories."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()

        # Structure:
        # src/
        #   valid.txt
        #   node_modules/
        #     ignored.txt
        #     subdir/
        #       ignored_deep.txt

        (src / "valid.txt").write_text("valid")
        (src / "node_modules").mkdir()
        (src / "node_modules" / "ignored.txt").write_text("ignored")
        (src / "node_modules" / "subdir").mkdir()
        (src / "node_modules" / "subdir" / "ignored_deep.txt").write_text("ignored")

        # Copy with exclude
        copy_directory(
            src,
            dest,
            exclude_patterns=["node_modules"]
        )

        assert (dest / "valid.txt").exists()
        assert not (dest / "node_modules").exists()

        # Verify it didn't just filter but actually pruned?
        # Hard to verify pruning vs filtering without mocking os.walk or timing.
        # But we can verify correctness first.

    def test_copy_directory_follow_symlinks(self, tmp_path):
        """Verify follow_symlinks behavior."""
        src = tmp_path / "src"
        dest_no_follow = tmp_path / "dest_no_follow"
        dest_follow = tmp_path / "dest_follow"
        src.mkdir()

        # Create a separate directory linked into src
        external = tmp_path / "external"
        external.mkdir()
        (external / "linked_file.txt").write_text("linked content")

        (src / "link_dir").symlink_to(external)

        # 1. Test NO follow (default)
        copy_directory(src, dest_no_follow, follow_symlinks=False)
        # Should not have copied the content of the link if it's a directory link
        # shutil.copytree default follows symlinks=False (copies link itself)
        # os.walk default followlinks=False (dirs)

        # If follow_symlinks=False, os.walk returns the link in 'dirs' but doesn't walk into it.
        # copy_directory iterates 'files'. Wait. os.walk behavior:
        # By default, walk() will not walk down into symbolic links that resolve to directories.
        # So 'link_dir' appears in 'dirs'.
        # But we don't process 'dirs' for copying, we iterate 'files'.
        # So 'link_dir' is skipped effectively?
        # NO. copy_directory iterates 'files'. os.walk puts symlinks to dirs in 'dirs'.
        # So it won't copy the directory link content.

        assert not (dest_no_follow / "link_dir" / "linked_file.txt").exists()

        # 2. Test FOLLOW
        copy_directory(src, dest_follow, follow_symlinks=True)
        assert (dest_follow / "link_dir" / "linked_file.txt").exists()

    def test_config_overrides(self, tmp_path):
        """Verify GlobalConfig -> Section overrides."""
        # Mock GlobalConfig
        global_conf = GlobalConfig()
        global_conf._data = {
            "defaults": {
                "ignored_directories": ["global_ignore"],
                "follow_symlinks": True
            }
        }

        # Mock DotManConfig with GlobalConfig
        config = DotManConfig(repo_path=tmp_path, global_config=global_conf)
        config._data = {
            "section1": {
                "paths": ["~/.config/section1"],
            },
            "section2": {
                "paths": ["~/.config/section2"],
                "ignored_directories": ["local_ignore"],
                "follow_symlinks": False
            }
        }

        s1 = config.get_section("section1")
        assert s1.ignored_directories == ["global_ignore"]
        assert s1.follow_symlinks is True

        s2 = config.get_section("section2")
        assert s2.ignored_directories == ["local_ignore"]
        assert s2.follow_symlinks is False

    def test_default_constants(self):
        """Verify defaults are loaded if nothing specified."""
        global_conf = GlobalConfig()
        # Mock empty load
        global_conf._data = {}

        defaults = global_conf.get_defaults()
        assert defaults["ignored_directories"] == DEFAULT_IGNORED_DIRECTORIES
        assert defaults["follow_symlinks"] is False
