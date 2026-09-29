import subprocess
import sys

import pytest

from dot_man.cli import complete_branches
from dot_man.cli.common import _clear_all_caches, _set_git_runner


@pytest.fixture(autouse=True)
def _isolated_completion_cache(tmp_path, monkeypatch):
    """Redirect the completion cache file away from the real repo.

    NOTE: `dot_man.cli.completions` as an attribute is the `completions`
    *command* (it shadows the module), so patch targets must go through
    sys.modules to reach the real module.
    """
    import dot_man.cli.completions  # noqa: F401 — ensures sys.modules entry

    mod = sys.modules["dot_man.cli.completions"]
    monkeypatch.setattr(
        mod, "COMPLETION_CACHE_FILE", tmp_path / "completion_cache.json"
    )
    monkeypatch.setattr(mod, "REPO_DIR", tmp_path)
    _clear_all_caches()
    yield
    _clear_all_caches()


def make_mock_result(stdout="", returncode=0):
    """Create a mock subprocess result."""
    result = subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )
    return result


def test_complete_branches_filtering():
    """Test that completion filters branches based on input."""
    _clear_all_caches()

    def mock_runner(args, cwd=None, timeout=2):
        if "branch" in args:
            return make_mock_result("main\nmaster\ndev\nfeature/abc\n")
        return make_mock_result()

    _set_git_runner(mock_runner)
    result = complete_branches(None, None, "")
    assert result == ["main", "master", "dev", "feature/abc"]

    result = complete_branches(None, None, "m")
    assert result == ["main", "master"]

    result = complete_branches(None, None, "feat")
    assert result == ["feature/abc"]

    result = complete_branches(None, None, "z")
    assert result == []
    _set_git_runner(None)


def test_complete_branches_error_handling():
    """Test that completion returns empty list on error."""
    _clear_all_caches()

    def mock_runner_error(args, cwd=None, timeout=2):
        raise Exception("Git error")

    _set_git_runner(mock_runner_error)
    result = complete_branches(None, None, "")
    assert result == []
    _set_git_runner(None)
