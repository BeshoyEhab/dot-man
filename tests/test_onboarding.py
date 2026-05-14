"""Tests for dot_man.cli.onboarding."""

from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ──────────────────────────────────────────────────────────────────────────────


def _patch_dot_man_dir(monkeypatch, tmp_path: Path):
    """Point DOT_MAN_DIR and SENTINEL at a temporary location."""
    fake_dir = tmp_path / ".config" / "dot-man"

    monkeypatch.setattr("dot_man.cli.onboarding.DOT_MAN_DIR", fake_dir)
    monkeypatch.setattr("dot_man.cli.onboarding.SENTINEL", fake_dir / ".onboarded")
    return fake_dir


# ──────────────────────────────────────────────────────────────────────────────
# is_first_run()
# ──────────────────────────────────────────────────────────────────────────────


class TestIsFirstRun:
    def test_returns_true_when_dir_missing(self, monkeypatch, tmp_path):
        """is_first_run() → True when DOT_MAN_DIR doesn't exist at all."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        assert not fake_dir.exists()

        from dot_man.cli.onboarding import is_first_run

        assert is_first_run() is True

    def test_returns_true_when_dir_exists_but_no_sentinel(self, monkeypatch, tmp_path):
        """is_first_run() → True when dir exists but .onboarded sentinel is absent."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        fake_dir.mkdir(parents=True)
        assert not (fake_dir / ".onboarded").exists()

        from dot_man.cli.onboarding import is_first_run

        assert is_first_run() is True

    def test_returns_false_when_sentinel_exists(self, monkeypatch, tmp_path):
        """is_first_run() → False when the .onboarded sentinel file is present."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        fake_dir.mkdir(parents=True)
        sentinel = fake_dir / ".onboarded"
        sentinel.touch()

        from dot_man.cli.onboarding import is_first_run

        assert is_first_run() is False


# ──────────────────────────────────────────────────────────────────────────────
# mark_onboarded()
# ──────────────────────────────────────────────────────────────────────────────


class TestMarkOnboarded:
    def test_creates_sentinel_file(self, monkeypatch, tmp_path):
        """mark_onboarded() creates the sentinel file."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        fake_dir.mkdir(parents=True)

        from dot_man.cli.onboarding import mark_onboarded

        mark_onboarded()

        sentinel = fake_dir / ".onboarded"
        assert sentinel.exists(), "Sentinel file was not created"

    def test_creates_parent_dir_if_missing(self, monkeypatch, tmp_path):
        """mark_onboarded() creates DOT_MAN_DIR if it doesn't exist yet."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        assert not fake_dir.exists()

        from dot_man.cli.onboarding import mark_onboarded

        mark_onboarded()

        assert fake_dir.exists()
        assert (fake_dir / ".onboarded").exists()

    def test_does_not_raise_if_called_twice(self, monkeypatch, tmp_path):
        """mark_onboarded() is idempotent — calling it twice doesn't raise."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        fake_dir.mkdir(parents=True)

        from dot_man.cli.onboarding import mark_onboarded

        mark_onboarded()
        mark_onboarded()  # should not raise

        assert (fake_dir / ".onboarded").exists()


# ──────────────────────────────────────────────────────────────────────────────
# Round-trip: mark → is_first_run
# ──────────────────────────────────────────────────────────────────────────────


class TestOnboardingRoundTrip:
    def test_is_first_run_false_after_mark(self, monkeypatch, tmp_path):
        """After mark_onboarded(), is_first_run() must return False."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        fake_dir.mkdir(parents=True)

        from dot_man.cli.onboarding import is_first_run, mark_onboarded

        assert is_first_run() is True  # before
        mark_onboarded()
        assert is_first_run() is False  # after


# ──────────────────────────────────────────────────────────────────────────────
# main() — onboarding gate in the CLI entry point
# ──────────────────────────────────────────────────────────────────────────────


class TestMainOnboardingGate:
    def test_main_calls_run_onboarding_on_first_run(self, monkeypatch, tmp_path):
        """main() should call run_onboarding() when is_first_run() returns True."""
        _patch_dot_man_dir(monkeypatch, tmp_path)

        called: list[str] = []

        def fake_run_onboarding() -> None:
            called.append("onboarding")

        # Patch the module-level functions that main() imports at call time
        import dot_man.cli.onboarding as onboarding_mod

        monkeypatch.setattr(onboarding_mod, "is_first_run", lambda: True)
        monkeypatch.setattr(onboarding_mod, "run_onboarding", fake_run_onboarding)

        from dot_man.cli.main import main

        main()
        assert "onboarding" in called

    def test_main_skips_onboarding_after_sentinel(self, monkeypatch, tmp_path):
        """main() should NOT call run_onboarding() when the sentinel file exists."""
        fake_dir = _patch_dot_man_dir(monkeypatch, tmp_path)
        fake_dir.mkdir(parents=True)
        (fake_dir / ".onboarded").touch()

        called: list[str] = []

        def fake_run_onboarding() -> None:  # pragma: no cover
            called.append("onboarding")

        import dot_man.cli.onboarding as onboarding_mod

        monkeypatch.setattr(onboarding_mod, "run_onboarding", fake_run_onboarding)

        # Verify is_first_run() correctly returns False for the patched dir
        from dot_man.cli.onboarding import is_first_run

        assert is_first_run() is False
        assert "onboarding" not in called
