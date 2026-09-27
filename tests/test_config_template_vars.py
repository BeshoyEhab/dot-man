"""Tests for `{{ }}` template variables in section config values.

Rendered at `get_section()` time with section context merged over
machine variables, before `Section` construction (so `{x}` hook
placeholders compose afterward).
"""

import platform
from unittest.mock import patch

import pytest

from dot_man.config import GlobalConfig
from dot_man.dotman_config import DotManConfig
from dot_man.exceptions import ConfigValidationError


@pytest.fixture
def cfg_env(tmp_path):
    """DotManConfig backed by a tmp repo dir + default global config."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def _load(toml_content: str) -> DotManConfig:
        (repo_dir / "dot-man.toml").write_text(toml_content)
        global_toml = tmp_path / "global.toml"
        with (
            patch("dot_man.global_config.GLOBAL_TOML", global_toml),
            patch("dot_man.config.REPO_DIR", repo_dir),
        ):
            gc = GlobalConfig()
            gc.create_default()
            gc.load()
            dc = DotManConfig(repo_path=repo_dir, global_config=gc)
            dc.load()
            return dc

    return _load


class TestSectionNameSubstitution:
    def test_section_name_renders_in_hook(self, cfg_env):
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{section_name}}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo nvim"

    def test_machine_var_renders(self, cfg_env):
        dc = cfg_env('[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{OS}}"\n')
        assert dc.get_section("nvim").post_deploy == f"echo {platform.system()}"


class TestTwoPassDerivation:
    def test_config_name_derives_from_rendered_path(self, cfg_env, tmp_path):
        dc = cfg_env(
            "[nvim]\n"
            f'paths = ["{tmp_path}/{{{{section_name}}}}"]\n'
            'post_deploy = "echo {{config_name}}"\n'
        )
        section = dc.get_section("nvim")
        assert section.paths[0].name == "nvim"
        assert section.post_deploy == "echo nvim"

    def test_paths_render_machine_vars(self, cfg_env, tmp_path):
        dc = cfg_env(f'[nvim]\npaths = ["{tmp_path}/{{{{OS}}}}"]\n')
        assert dc.get_section("nvim").paths[0].name == platform.system()


class TestConditionals:
    def test_conditional_renders(self, cfg_env):
        toml_content = (
            "[nvim]\n"
            "paths = ['/tmp/x']\n"
            "post_deploy = 'got-{{ if OS == \"darwin\" }}mac{{ endif }}'\n"
        )
        dc = cfg_env(toml_content)
        expected = "got-mac" if platform.system() == "darwin" else "got-"
        assert dc.get_section("nvim").post_deploy == expected

    def test_conditional_negation_renders(self, cfg_env):
        toml_content = (
            "[nvim]\n"
            "paths = ['/tmp/x']\n"
            "post_deploy = 'got-{{ if OS != \"darwin\" }}other{{ endif }}'\n"
        )
        dc = cfg_env(toml_content)
        expected = "got-other" if platform.system() != "darwin" else "got-"
        assert dc.get_section("nvim").post_deploy == expected


class TestPassthroughAndOrder:
    def test_unknown_variable_stays_literal(self, cfg_env):
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{NOPE_NOT_A_VAR}}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo {{NOPE_NOT_A_VAR}}"

    def test_validation_runs_after_render(self, cfg_env):
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\nupdate_strategy = "{{NOPE_NOT_A_VAR}}"\n'
        )
        with pytest.raises(ConfigValidationError):
            dc.get_section("nvim")

    def test_hook_braces_compose_after_templates(self, cfg_env):
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{section_name}} {paths}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo nvim /tmp/x"

    def test_include_list_items_render(self, cfg_env):
        dc = cfg_env('[nvim]\npaths = ["/tmp/x"]\ninclude = ["*.{{section_name}}"]\n')
        assert dc.get_section("nvim").include == ["*.nvim"]
