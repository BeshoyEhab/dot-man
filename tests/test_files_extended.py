"""More tests for files module."""


class TestFilesBasic:
    """Test basic file functions."""

    def test_atomic_write_basic(self, tmp_path):
        """Test atomic write basic."""
        from dot_man.files import atomic_write_text

        test_file = tmp_path / "test.txt"
        atomic_write_text(test_file, "content")

        assert test_file.read_text() == "content"

    def test_atomic_write_overwrite(self, tmp_path):
        """Test atomic write overwrite."""
        from dot_man.files import atomic_write_text

        test_file = tmp_path / "test.txt"
        test_file.write_text("original")
        atomic_write_text(test_file, "new content")

        assert test_file.read_text() == "new content"

    def test_copy_file_basic(self, tmp_path):
        """Test basic file copy."""
        from dot_man.files import copy_file

        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"

        src.write_text("test content")
        copy_file(src, dst)

        assert dst.read_text() == "test content"

    def test_compare_files_identical(self, tmp_path):
        """Test comparing identical files."""
        from dot_man.files import compare_files

        file1 = tmp_path / "f1.txt"
        file2 = tmp_path / "f2.txt"

        file1.write_text("same")
        file2.write_text("same")

        assert compare_files(file1, file2) is True

    def test_compare_files_different(self, tmp_path):
        """Test comparing different files."""
        from dot_man.files import compare_files

        file1 = tmp_path / "f1.txt"
        file2 = tmp_path / "f2.txt"

        file1.write_text("content1")
        file2.write_text("content2")

        assert compare_files(file1, file2) is False

    def test_clear_comparison_cache(self):
        """Test clearing comparison cache."""
        from dot_man.files import clear_comparison_cache

        clear_comparison_cache()
