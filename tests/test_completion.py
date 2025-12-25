
import pytest
from unittest.mock import patch, MagicMock
from dot_man.cli import complete_branches

@patch("dot_man.cli.GitManager")
def test_complete_branches_filtering(mock_git):
    """Test that completion filters branches based on input."""
    # Setup mock
    mock_instance = mock_git.return_value
    mock_instance.list_branches.return_value = ["main", "master", "dev", "feature/abc"]
    
    # Test empty input (should return all)
    # Note: click passes incomplete="" for empty, logic checks startswith
    assert complete_branches(None, None, "") == ["main", "master", "dev", "feature/abc"]
    
    # Test partial match
    assert complete_branches(None, None, "m") == ["main", "master"]
    
    # Test specific match
    assert complete_branches(None, None, "feat") == ["feature/abc"]
    
    # Test no match
    assert complete_branches(None, None, "z") == []

@patch("dot_man.cli.GitManager")
def test_complete_branches_error_handling(mock_git):
    """Test that completion returns empty list on error."""
    mock_instance = mock_git.return_value
    mock_instance.list_branches.side_effect = Exception("Git error")
    
    assert complete_branches(None, None, "") == []
