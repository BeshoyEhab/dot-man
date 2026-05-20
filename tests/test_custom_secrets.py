"""Tests for custom secret patterns."""

from dot_man.cli.interface import cli
from dot_man.constants import REPO_DIR
from dot_man.operations import get_operations
from dot_man.secrets import (
    Severity,
    filter_secrets,
    get_custom_scanner,
    load_custom_patterns,
)


def test_load_custom_patterns():
    """Test parsing of custom patterns from config dictionaries."""
    config_data = {
        "security": {
            "patterns": [
                {
                    "name": "Custom Key",
                    "pattern": r"custom_[0-9]+",
                    "severity": "CRITICAL",
                    "description": "My custom key description",
                },
                {
                    "name": "Invalid Pattern",
                    "pattern": r"[invalid",  # invalid regex
                    "severity": "HIGH",
                },
                {
                    "name": "Missing Pattern",
                    "severity": "LOW",
                },
            ]
        }
    }

    patterns = load_custom_patterns(config_data, ["security", "patterns"])

    # Invalid and missing patterns should be ignored, leaving only one
    assert len(patterns) == 1
    assert patterns[0].name == "Custom Key"
    assert patterns[0].pattern.pattern == r"custom_[0-9]+"
    assert patterns[0].severity == Severity.CRITICAL
    assert patterns[0].description == "My custom key description"


def test_get_custom_scanner_with_defaults(integration_runner):
    """Test custom scanner compiles correctly with default and custom configs."""
    ops = get_operations()

    # Add a custom pattern to the global config data dictionary
    ops.global_config._data["security"] = {
        "patterns": [
            {
                "name": "Global Special",
                "pattern": r"global_spec_[a-z]+",
                "severity": "MEDIUM",
            }
        ]
    }
    ops.global_config._dirty = True
    ops.global_config.save()

    # Add a custom pattern to the repository config data dictionary
    ops.dotman_config._data["secrets"] = {
        "patterns": [
            {
                "name": "Repo Special",
                "pattern": r"repo_spec_[0-9]+",
                "severity": "HIGH",
            }
        ]
    }
    ops.dotman_config._dirty = True
    ops.dotman_config.save()

    scanner = get_custom_scanner()
    pattern_names = [p.name for p in scanner.patterns]

    # Should contain default patterns + global patterns + repo patterns
    assert "Private Key" in pattern_names
    assert "Global Special" in pattern_names
    assert "Repo Special" in pattern_names


def test_get_custom_scanner_disable_defaults(integration_runner):
    """Test that default patterns can be disabled via use_default_patterns."""
    ops = get_operations()

    # Disable default patterns globally, add a custom one
    ops.global_config._data["security"] = {
        "use_default_patterns": False,
        "patterns": [
            {
                "name": "Global Special Only",
                "pattern": r"global_spec_[a-z]+",
                "severity": "MEDIUM",
            }
        ],
    }
    ops.global_config._dirty = True
    ops.global_config.save()

    scanner = get_custom_scanner()
    pattern_names = [p.name for p in scanner.patterns]

    # Should NOT contain default patterns, but should contain the custom one
    assert "Private Key" not in pattern_names
    assert "Global Special Only" in pattern_names


def test_filter_secrets_uses_custom_patterns(integration_runner):
    """Test that filter_secrets correctly detects and redacts custom patterns."""
    ops = get_operations()

    ops.global_config._data["security"] = {
        "use_default_patterns": False,
        "patterns": [
            {
                "name": "Custom Super Password",
                "pattern": r"my_super_pass_\w+",
                "severity": "CRITICAL",
            }
        ],
    }
    ops.global_config._dirty = True
    ops.global_config.save()

    content = "This is a line with my_super_pass_123456 inside it."
    filtered, matches = filter_secrets(content)

    assert "my_super_pass_123456" not in filtered
    assert "***REDACTED***" in filtered
    assert len(matches) == 1
    assert matches[0].pattern_name == "Custom Super Password"


def test_cli_audit_with_custom_patterns(integration_runner):
    """Test that CLI audit command detects custom secrets in repository files."""
    ops = get_operations()

    # Configure custom pattern globally
    ops.global_config._data["security"] = {
        "patterns": [
            {
                "name": "Internal ID",
                "pattern": r"internal_id_token_[a-f0-9]{8}",
                "severity": "HIGH",
            }
        ]
    }
    ops.global_config._dirty = True
    ops.global_config.save()

    # Write a file containing a secret inside the repo directory
    secret_file = REPO_DIR / "secret_data.txt"
    secret_file.write_text("Here is my internal_id_token_ab12cd34 code.")

    # Run audit command via runner
    result = integration_runner.invoke(cli, ["audit"])

    # Should detect the secret
    assert result.exit_code == 0
    assert "Internal ID" in result.output
    assert "internal_id_token_ab12cd34" in result.output
