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
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        """Integration check against the real host: {{OS}} must equal
        platform.system() verbatim on whatever machine runs the suite."""
        dc = cfg_env('[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{OS}}"\n')
        assert dc.get_section("nvim").post_deploy == f"echo {platform.system()}"

    def test_machine_var_renders_pinned_darwin(self, cfg_env):
        """Pin the observed machine variable to Darwin so the exact
        substitution (`echo Darwin`) is proven on every host — the real-host
        test above alone cannot show what value a different platform would
        produce."""
        with patch("platform.system", return_value="Darwin"):
            dc = cfg_env('[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{OS}}"\n')
            assert dc.get_section("nvim").post_deploy == "echo Darwin"

    def test_hostname_var_renders_pinned(self, cfg_env):
        """{{HOSTNAME}} must equal the host name verbatim. Patch getfqdn too:
        it is evaluated during rendering and would otherwise reverse-DNS the
        pinned hostname, hanging on DNS instead of asserting."""
        with (
            patch("socket.getfqdn", return_value="pinned-host"),
            patch("socket.gethostname", return_value="pinned-host"),
        ):
            dc = cfg_env(
                '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{HOSTNAME}}"\n'
            )
            assert dc.get_section("nvim").post_deploy == "echo pinned-host"


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
    @pytest.mark.parametrize(
        ("system_name", "expected"),
        [
            ("darwin", "got-mac"),
            ("Darwin", "got-mac"),  # the real macOS spelling
            ("Linux", "got-"),
        ],
        ids=["darwin", "Darwin-real-macos", "linux"],
    )
    def test_conditional_renders_pinned(self, cfg_env, system_name, expected):
        """Pin the machine OS so BOTH branches of `if OS == "darwin"` are
        proven on every host. Case-insensitive: the real macOS spelling
        ("Darwin") must satisfy the canonical lowercase literal from the
        substitute_templates docstring."""
        toml_content = (
            "[nvim]\n"
            "paths = ['/tmp/x']\n"
            "post_deploy = 'got-{{ if OS == \"darwin\" }}mac{{ endif }}'\n"
        )
        with patch("platform.system", return_value=system_name):
            dc = cfg_env(toml_content)
            assert dc.get_section("nvim").post_deploy == expected

    @pytest.mark.parametrize(
        ("system_name", "expected"),
        [
            ("darwin", "got-"),
            ("Darwin", "got-"),  # the real macOS spelling
            ("Linux", "got-other"),
        ],
        ids=["darwin", "Darwin-real-macos", "linux"],
    )
    def test_conditional_negation_renders_pinned(self, cfg_env, system_name, expected):
        """Pin the machine OS for `if OS != "darwin"` so both branches
        (negation-taken on the matching OS, negation-skipped on a different
        OS) are proven regardless of the host running the suite — including
        the real macOS spelling via case-insensitive comparison."""
        toml_content = (
            "[nvim]\n"
            "paths = ['/tmp/x']\n"
            "post_deploy = 'got-{{ if OS != \"darwin\" }}other{{ endif }}'\n"
        )
        with patch("platform.system", return_value=system_name):
            dc = cfg_env(toml_content)
            assert dc.get_section("nvim").post_deploy == expected

    def test_conditional_match_is_case_insensitive(self, cfg_env):
        """The real macOS spelling ("Darwin") must satisfy `== "darwin"`.

        platform.system() returns "Darwin" on macOS while the canonical
        docstring example writes the lowercase literal — a case-sensitive
        compare made the documented mac branch unreachable on real Macs.
        Comparison is now case-insensitive in both directions."""
        with patch("platform.system", return_value="Darwin"):
            dc = cfg_env(
                "[nvim]\n"
                "paths = ['/tmp/x']\n"
                "post_deploy = 'got-{{ if OS == \"darwin\" }}mac{{ endif }}'\n"
            )
            assert dc.get_section("nvim").post_deploy == "got-mac"

    def test_conditional_match_uppercase_literal(self, cfg_env):
        """Case-insensitivity works in the other direction too: an
        uppercase literal still matches the lowercase actual value."""
        with patch("platform.system", return_value="linux"):
            dc = cfg_env(
                "[nvim]\n"
                "paths = ['/tmp/x']\n"
                "post_deploy = 'got-{{ if OS == \"LINUX\" }}tux{{ endif }}'\n"
            )
            assert dc.get_section("nvim").post_deploy == "got-tux"


class TestMultiVarComposition:
    def test_multiple_vars_in_one_string(self, cfg_env):
        """Two different vars in ONE value must both substitute in a single
        render — guards against a first-match-only renderer that would drop
        the second variable."""
        with patch("platform.system", return_value="Darwin"):
            dc = cfg_env(
                '[nvim]\npaths = ["/tmp/x"]\n'
                'post_deploy = "{{OS}}-{{section_name}}"\n'
            )
            assert dc.get_section("nvim").post_deploy == "Darwin-nvim"

    def test_exclude_list_items_render(self, cfg_env):
        """exclude is a second glob list besides include — template vars must
        render there too, not only in include."""
        dc = cfg_env('[nvim]\npaths = ["/tmp/x"]\nexclude = ["*.{{section_name}}"]\n')
        assert dc.get_section("nvim").exclude == ["*.nvim"]

    def test_template_var_composes_with_config_root(self, cfg_env):
        """Both syntaxes on one value: {{section_name}} renders in the
        template pass, then the {config_root} hook placeholder composes
        afterward — neither pass may eat the other's braces."""
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\n'
            'post_deploy = "echo {{section_name}} {config_root}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo nvim /tmp"


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

    def test_single_brace_left_for_hook_pass(self, cfg_env):
        """Single-brace {section_name} is the hook-placeholder spelling: the
        template pass must leave it alone and the hook pass resolves it at
        get_section() — proving render-then-compose ordering."""
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {section_name}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo nvim"

    def test_single_brace_not_rendered_by_template_pass(self, cfg_env):
        """In paths — a field the template pass demonstrably rewrites for
        {{ }} — a single-brace value survives verbatim, proving the template
        engine understands only double braces and leaves {x} for the later
        hook pass."""
        dc = cfg_env('[nvim]\npaths = ["{section_name}"]\n')
        assert str(dc.get_section("nvim").paths[0]) == "{section_name}"

    def test_whitespace_inside_braces_stays_literal(self, cfg_env):
        """Brace syntax admits no inner whitespace: {{ section_name }} is an
        unknown var and passes through verbatim, so a typo surfaces instead
        of silently rendering."""
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{ section_name }}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo {{ section_name }}"

    def test_adjacent_braces_render_inner_only(self, cfg_env):
        """For {{{{section_name}}}} the inner {{section_name}} occurrence
        matches and renders to nvim while the surrounding outer braces pass
        through unchanged — nested-looking braces do not confuse the match."""
        dc = cfg_env(
            '[nvim]\npaths = ["/tmp/x"]\npost_deploy = "echo {{{{section_name}}}}"\n'
        )
        assert dc.get_section("nvim").post_deploy == "echo {{nvim}}"
