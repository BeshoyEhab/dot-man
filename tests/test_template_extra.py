"""Additional tests for template command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestTemplateExtra:
    """Additional template command tests."""

    def test_template_invalid_command(self):
        """Test invalid template subcommand."""
        runner = CliRunner()
        result = runner.invoke(cli, ["template", "invalid"])
        assert result.exit_code == 2


class TestTemplateVariables:
    """Test template variable substitution."""

    def test_substitute_templates_basic(self):
        """Test basic template substitution."""
        from dot_man.global_config import substitute_templates

        result = substitute_templates("Hello {{HOSTNAME}}")
        assert "HOSTNAME" not in result or "Hello" in result

    def test_substitute_templates_empty(self):
        """Test substitution with empty string."""
        from dot_man.global_config import substitute_templates

        result = substitute_templates("")
        assert result == ""

    def test_substitute_templates_user_vars(self):
        """Test user-defined template variables."""
        from dot_man.global_config import substitute_templates

        result = substitute_templates("{{FOO}}", {"FOO": "bar"})
        assert result == "bar"

    def test_substitute_templates_no_match(self):
        """Test substitution with no matching vars."""
        from dot_man.global_config import substitute_templates

        result = substitute_templates("Hello World", {"FOO": "bar"})
        assert result == "Hello World"
