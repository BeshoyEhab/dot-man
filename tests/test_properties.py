"""Property-based tests (hypothesis) for pure, invariant-bearing helpers.

These complement the example-based suite: instead of one hand-picked input,
each test asserts an invariant over hundreds of generated inputs, which is
exactly where the secret scanner and template substituter are most likely to
break (odd characters, long runs, braces).
"""

import math

from hypothesis import given
from hypothesis import strategies as st

from dot_man.global_config import substitute_templates
from dot_man.secrets import SecretScanner, shannon_entropy

# ``{{KEY}}`` / ``{{ KEY }}`` placeholders need a key that cannot collide with
# the replacement text.
keys = st.from_regex(r"[A-Z][A-Z0-9_]{0,12}", fullmatch=True)
# Values must not contain braces, or they could themselves look like templates.
no_braces = st.characters(blacklist_characters="{}")
values = st.text(alphabet=no_braces, min_size=1, max_size=40)
filler = st.text(alphabet=no_braces, max_size=40)


class TestTemplateSubstitutionProperties:
    """``substitute_templates`` replaces every occurrence of a known key."""

    @given(key=keys, value=values, filler=filler)
    def test_every_placeholder_is_replaced(self, key, value, filler):
        text = f"{filler}{{{{{key}}}}}{filler}{{{{{key}}}}}"

        result = substitute_templates(text, {key: value})

        assert f"{{{{{key}}}}}" not in result
        assert result.count(value) >= 2

    @given(key=keys, value=values)
    def test_unrelated_text_is_left_untouched(self, key, value):
        plain = f"no placeholders here, only {key} bare"

        assert substitute_templates(plain, {key: value}) == plain

    @given(text=st.text(max_size=80))
    def test_no_key_means_no_crash(self, text):
        # With no user templates the call must still be total.
        assert isinstance(substitute_templates(text, {}), str)


class TestEntropyProperties:
    """``shannon_entropy`` is bounded, non-negative and permutation invariant."""

    @given(text=st.text(max_size=200))
    def test_entropy_is_non_negative_and_bounded(self, text):
        entropy = shannon_entropy(text)

        assert entropy >= 0.0
        if len(text) > 1:
            # Maximum entropy is log2(n) for n i.i.d. symbols.
            assert entropy <= math.log2(len(text)) + 1e-9

    @given(text=st.text(min_size=1, max_size=120), seed=st.integers())
    def test_entropy_is_permutation_invariant(self, text, seed):
        shuffled = "".join(sorted(text, key=lambda c: (seed + ord(c)) % 7))

        # Floating-point summation order differs, so compare with tolerance.
        assert math.isclose(
            shannon_entropy(text), shannon_entropy(shuffled), rel_tol=1e-9
        )

    def test_entropy_of_a_single_symbol_is_zero(self):
        assert shannon_entropy("a" * 50) == 0.0


class TestSecretScannerProperties:
    """Scanning arbitrary content is total and never leaks a match."""

    @given(content=st.text(max_size=400))
    def test_scanning_never_raises_and_masked_line_hides_match(self, content):
        scanner = SecretScanner()

        for match in scanner.scan_content(content):
            # The reported match really is a substring of the line it came from.
            if match.matched_text:
                assert match.matched_text in match.line_content
                # ``masked_line`` must never contain the live secret.
                assert match.matched_text not in match.masked_line
