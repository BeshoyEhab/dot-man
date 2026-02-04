import pytest
from pathlib import Path
from dot_man.files import iter_tracked_files


def test_iter_tracked_files_optimization(tmp_path):
    repo_dir = tmp_path / "repo"
    local_dir = tmp_path / "local"
    repo_dir.mkdir()
    local_dir.mkdir()

    # 1. Identical
    (repo_dir / "identical.txt").write_text("same")
    (local_dir / "identical.txt").write_text("same")

    # 2. Modified
    (repo_dir / "modified.txt").write_text("v1")
    (local_dir / "modified.txt").write_text("v2")

    # 3. New
    (local_dir / "new.txt").write_text("new")

    # 4. Deleted
    (repo_dir / "deleted.txt").write_text("deleted")

    # 5. Nested Identical
    (repo_dir / "subdir").mkdir()
    (local_dir / "subdir").mkdir()
    (repo_dir / "subdir/nested.txt").write_text("nested")
    (local_dir / "subdir/nested.txt").write_text("nested")

    config = [{"local_path": local_dir, "repo_path": repo_dir}]

    results = list(iter_tracked_files(config))

    # Convert to a dict for easier assertion {rel_path: status}
    result_map = {}
    for local, repo, status in results:
        rel = local.relative_to(local_dir)
        result_map[str(rel)] = status

    assert result_map["identical.txt"] == "IDENTICAL"
    assert result_map["modified.txt"] == "MODIFIED"
    assert result_map["new.txt"] == "NEW"
    assert result_map["deleted.txt"] == "DELETED"
    assert result_map["subdir/nested.txt"] == "IDENTICAL"

    assert len(results) == 5


def test_iter_tracked_files_empty_dirs(tmp_path):
    repo_dir = tmp_path / "repo"
    local_dir = tmp_path / "local"
    repo_dir.mkdir()
    local_dir.mkdir()

    config = [{"local_path": local_dir, "repo_path": repo_dir}]
    results = list(iter_tracked_files(config))
    assert len(results) == 0


def test_iter_tracked_files_single_file_config(tmp_path):
    # Verify the non-directory path works as before
    repo_file = tmp_path / "repo_file.txt"
    local_file = tmp_path / "local_file.txt"
    repo_file.write_text("content")
    local_file.write_text("content")

    config = [{"local_path": local_file, "repo_path": repo_file}]
    results = list(iter_tracked_files(config))

    assert len(results) == 1
    assert results[0][2] == "IDENTICAL"
