"""Secret detection patterns and filtering logic."""

__all__ = [
    "SecretScanner",
    "SecretMatch",
    "SecretPattern",
    "SecretGuard",
    "PermanentRedactGuard",
    "Severity",
    "filter_secrets",
    "get_custom_scanner",
    "load_custom_patterns",
]

import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, TypedDict

from .constants import DOT_MAN_DIR, SECRET_REDACTION_TEXT
from .utils import sha256_hex


def _canonicalize_path(file_path: Path | str) -> str:
    """Resolve path to canonical absolute form for consistent matching.

    This ensures that ~/file, /home/user/file, and ./file all resolve
    to the same canonical path for reliable secret ignore list matching.
    """
    path = Path(file_path).expanduser()
    try:
        # resolve() handles symlinks and .. components
        return str(path.resolve())
    except OSError:
        # File might not exist yet, just expand and convert to absolute
        return str(path.absolute())


class AllowedSecret(TypedDict):
    """Structure for an allowed secret entry."""

    file_path: str
    secret_hash: str
    pattern_name: str
    added_at: str


class BaseSecretGuard:
    """Base class for managing secret lists (allow list, redact list)."""

    def __init__(
        self,
        config_dir: Path | None = None,
        path: Path | None = None,
        default_filename: str = "secrets.json",
    ):
        self.config_dir = config_dir or DOT_MAN_DIR
        self.list_path = path or (self.config_dir / default_filename)
        self._secrets: list[AllowedSecret] = self._load()

    def _load(self) -> list[AllowedSecret]:
        """Load secrets from disk."""
        if not self.list_path.exists():
            return []
        try:
            content = self.list_path.read_text(encoding="utf-8")
            from typing import cast

            return cast(list[AllowedSecret], json.loads(content))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        except OSError:
            return []

    def save(self) -> None:
        """Save secrets to disk."""
        try:
            # Ensure directory exists
            self.list_path.parent.mkdir(parents=True, exist_ok=True)

            content = json.dumps(self._secrets, indent=2)
            self.list_path.write_text(content, encoding="utf-8")
        except OSError as e:
            logging.warning(f"Could not save secrets list: {e}")

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of the content."""
        return sha256_hex(content)

    def _is_in_list(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> bool:
        """Check if a secret is in the list."""
        path_str = _canonicalize_path(file_path)
        content_hash = self._compute_hash(line_content)

        for secret in self._secrets:
            if (
                secret["file_path"] == path_str
                and secret["secret_hash"] == content_hash
                and secret["pattern_name"] == pattern_name
            ):
                return True
        return False

    def _add_to_list(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> None:
        """Add a secret to the list."""
        if self._is_in_list(file_path, line_content, pattern_name):
            return

        entry: AllowedSecret = {
            "file_path": _canonicalize_path(file_path),
            "secret_hash": self._compute_hash(line_content),
            "pattern_name": pattern_name,
            "added_at": datetime.now().isoformat(),
        }
        self._secrets.append(entry)
        self.save()


class SecretGuard(BaseSecretGuard):
    """Manages the list of allowed (skipped) secrets."""

    def __init__(self, config_dir: Path | None = None, path: Path | None = None):
        super().__init__(
            config_dir, path, default_filename=".dotman-allowed-secrets.json"
        )

    def is_allowed(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> bool:
        """Check if a secret is in the allow list."""
        return self._is_in_list(file_path, line_content, pattern_name)

    def add_allowed(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> None:
        """Add a secret to the allow list."""
        self._add_to_list(file_path, line_content, pattern_name)


class PermanentRedactGuard(BaseSecretGuard):
    """Manages the list of secrets that should always be redacted."""

    def __init__(self, config_dir: Path | None = None, path: Path | None = None):
        super().__init__(
            config_dir, path, default_filename=".dotman-permanent-redact.json"
        )

    def should_redact(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> bool:
        """Check if a secret should be permanently redacted."""
        return self._is_in_list(file_path, line_content, pattern_name)

    def add_permanent_redact(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> None:
        """Add a secret to the permanent redact list."""
        self._add_to_list(file_path, line_content, pattern_name)


class Severity(Enum):
    """Secret severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class SecretPattern:
    """A secret detection pattern."""

    name: str
    pattern: re.Pattern
    severity: Severity
    description: str


@dataclass
class SecretMatch:
    """A detected secret match."""

    file: Path
    line_number: int
    line_content: str
    pattern_name: str
    severity: Severity
    matched_text: str
    history_ref: str = ""

    @property
    def masked_line(self) -> str:
        """Line content with the matched secret replaced by ``***``.

        Never print ``line_content`` directly: it contains the live secret.
        """
        if self.matched_text:
            return self.line_content.replace(self.matched_text, "***")
        return self.line_content


# ============================================================================
# Default Patterns
# ============================================================================

DEFAULT_PATTERNS: list[SecretPattern] = [
    # CRITICAL - System/Cloud compromise
    SecretPattern(
        name="Private Key",
        pattern=re.compile(
            r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE KEY-----"
        ),
        severity=Severity.CRITICAL,
        description="SSH/GPG private key header detected",
    ),
    SecretPattern(
        name="AWS Access Key ID",
        pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
        severity=Severity.CRITICAL,
        description="AWS Access Key ID format",
    ),
    SecretPattern(
        name="AWS Secret Key",
        pattern=re.compile(r"aws_secret_access_key\s*[=:]\s*\S+", re.IGNORECASE),
        severity=Severity.CRITICAL,
        description="AWS Secret Access Key assignment",
    ),
    # HIGH - Service compromise
    SecretPattern(
        name="GitHub Token",
        pattern=re.compile(r"gh[ps]_[a-zA-Z0-9]{36}"),
        severity=Severity.HIGH,
        description="GitHub Personal Access Token",
    ),
    SecretPattern(
        name="GitHub Fine-Grained PAT",
        pattern=re.compile(r"github_pat_[A-Za-z0-9_]{22,}"),
        severity=Severity.HIGH,
        description="GitHub fine-grained personal access token",
    ),
    SecretPattern(
        name="GitLab Token",
        pattern=re.compile(r"glpat-[A-Za-z0-9_-]{20,}"),
        severity=Severity.HIGH,
        description="GitLab personal access token",
    ),
    SecretPattern(
        name="Slack Token",
        pattern=re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
        severity=Severity.HIGH,
        description="Slack API token",
    ),
    SecretPattern(
        name="AWS Session Token",
        pattern=re.compile(r"ASIA[0-9A-Z]{16}"),
        severity=Severity.CRITICAL,
        description="AWS temporary (STS) access key ID",
    ),
    SecretPattern(
        name="Generic API Key",
        pattern=re.compile(
            r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?[\w-]{20,}['\"]?", re.IGNORECASE
        ),
        severity=Severity.HIGH,
        description="Generic API key assignment",
    ),
    SecretPattern(
        name="Password Assignment",
        pattern=re.compile(
            r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?.+['\"]?", re.IGNORECASE
        ),
        severity=Severity.HIGH,
        description="Password assignment detected",
    ),
    SecretPattern(
        name="Bearer Token",
        pattern=re.compile(r"bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE),
        severity=Severity.HIGH,
        description="Bearer token detected",
    ),
    SecretPattern(
        name="Auth Token",
        pattern=re.compile(
            r"(?:auth[_-]?token|token)\s*[=:]\s*['\"]?[\w-]{20,}['\"]?", re.IGNORECASE
        ),
        severity=Severity.HIGH,
        description="Authentication token assignment",
    ),
    # MEDIUM - Potential exposure
    SecretPattern(
        name="JWT Token",
        pattern=re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        severity=Severity.MEDIUM,
        description="JSON Web Token detected",
    ),
    SecretPattern(
        name="Generic Secret",
        pattern=re.compile(
            r"(?:secret|credential)\s*[=:]\s*['\"]?.+['\"]?", re.IGNORECASE
        ),
        severity=Severity.MEDIUM,
        description="Generic secret assignment",
    ),
    SecretPattern(
        name="High Entropy String",
        pattern=re.compile(r"[A-Za-z0-9+/=_\-]{32,}"),
        severity=Severity.MEDIUM,
        description="Long random-looking string (entropy scored)",
    ),
]


def shannon_entropy(value: str) -> float:
    """Return Shannon entropy (bits per character) of ``value``.

    Random secrets score high (~4+ for base64-ish text); repeated or
    sequential filler scores low. Used to keep the generic
    "High Entropy String" pattern from flagging hashes-as-documentation or
    long-but-repetitive blobs.
    """
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(value)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


# Minimum bits/char for the "High Entropy String" pattern to be reported.
MIN_ENTROPY_BITS_PER_CHAR = 3.0
# Pattern names whose value must pass the entropy threshold.
ENTROPY_SCORED_PATTERNS = {"High Entropy String"}

# False positive indicators - lines containing these are skipped
FALSE_POSITIVE_INDICATORS = [
    "example",
    "dummy",
    "sample",
    "your_key_here",
    "your-key-here",
    "xxx",
    "placeholder",
    "<your",
    "${",  # Environment variable substitution
    "{{",  # Template variable
]


class SecretScanner:
    """Scans files for secrets."""

    def __init__(self, patterns: list[SecretPattern] | None = None):
        self.patterns = patterns or DEFAULT_PATTERNS

    def is_false_positive(self, line: str, value: str | None = None) -> bool:
        """Check if a detected value (or line) is likely a false positive.

        Indicators are matched against the detected *value* when one is
        supplied, so a comment containing "example" no longer hides a real
        secret elsewhere on the line.
        """
        target = (value if value is not None else line).lower()
        return any(indicator in target for indicator in FALSE_POSITIVE_INDICATORS)

    def _passes_entropy(self, name: str, value: str) -> bool:
        if name not in ENTROPY_SCORED_PATTERNS:
            return True
        return shannon_entropy(value) >= MIN_ENTROPY_BITS_PER_CHAR

    def is_binary_file(self, path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(path, "rb") as f:
                chunk = f.read(8192)
                return b"\x00" in chunk
        except OSError:
            return True  # Assume binary if we can't read it

    def scan_lines(
        self, lines: Iterable[str], file_path: Path | None = None
    ) -> Iterator[SecretMatch]:
        """Scan lines for secrets."""
        file_path = file_path or Path("<string>")

        for line_number, line in enumerate(lines, start=1):
            for pattern in self.patterns:
                match = pattern.pattern.search(line)
                if not match:
                    continue
                value = match.group(0)
                if self.is_false_positive(line, value=value):
                    continue
                if not self._passes_entropy(pattern.name, value):
                    continue
                yield SecretMatch(
                    file=file_path,
                    line_number=line_number,
                    line_content=line.strip(),
                    pattern_name=pattern.name,
                    severity=pattern.severity,
                    matched_text=value,
                )

    def scan_content(
        self, content: str, file_path: Path | None = None
    ) -> Iterator[SecretMatch]:
        """Scan content for secrets."""
        return self.scan_lines(content.splitlines(), file_path)

    def scan_file(self, path: Path) -> Iterator[SecretMatch]:
        """Scan a file for secrets."""
        if self.is_binary_file(path):
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                yield from self.scan_lines(f, path)
        except (OSError, UnicodeDecodeError):
            # Skip files we can't read
            pass

    def scan_directory(
        self, directory: Path, exclude_patterns: list[str] | None = None
    ) -> Iterator[SecretMatch]:
        """Scan all files in a directory for secrets."""
        exclude_patterns = exclude_patterns or []

        for path in directory.rglob("*"):
            # Skip directories
            if path.is_dir():
                continue

            # Skip .git directory
            if ".git" in path.parts:
                continue

            # Skip excluded patterns
            if any(path.match(pattern) for pattern in exclude_patterns):
                continue

            yield from self.scan_file(path)

    def scan_git_history(
        self, repo: Any, include_index: bool = True
    ) -> Iterator[SecretMatch]:
        """Scan git history and (optionally) the index for secrets.

        A working-tree-only scan misses secrets that were committed and later
        removed (or are staged but not yet committed). Blobs are deduplicated
        by object id, so each unique version of a file is scanned once.
        Results carry ``history_ref`` (short commit sha, ``"index"`` for staged
        content) and ``file`` is the path *inside* the repo, not on disk.
        Never raises: unreadable objects are skipped.
        """
        seen: set[str] = set()

        def scan_blob(hexsha: str, path: Path, ref: str) -> Iterator[SecretMatch]:
            if hexsha in seen:
                return
            seen.add(hexsha)
            try:
                text = repo.git.cat_file("blob", hexsha)
            except Exception:
                return
            if "\x00" in text[:8192]:
                return
            for match in self.scan_lines(text.splitlines(), path):
                match.history_ref = ref
                yield match

        if include_index:
            try:
                for entry in repo.index.entries.values():
                    yield from scan_blob(entry.hexsha, Path(entry.path), "index")
            except Exception:
                pass

        try:
            commits = repo.iter_commits("--all")
        except Exception:
            return

        for commit in commits:
            try:
                tree = commit.tree
            except Exception:
                continue
            try:
                for item in tree.traverse():
                    if item.type != "blob":
                        continue
                    yield from scan_blob(
                        item.hexsha, Path(item.path), commit.hexsha[:8]
                    )
            except Exception:
                continue

    def redact_content(
        self,
        content: str,
        callback: Callable[[SecretMatch], str] | None = None,
        file_path: Path | None = None,
    ) -> tuple[str, int]:
        """
        Redact secrets from content. Returns (redacted_content, count).

        Args:
            content: Text content to redact
            callback: Optional function that takes a SecretMatch and returns a string action ("REDACT")
                      OR the replacement string itself.
                      If it returns "REDACT", default redaction text is used.
                      If it returns anything else (and not "KEEP"), that string is used as replacement.
            file_path: Path to the file being scanned (for context in callback)
        """
        redacted_lines = []
        count = 0
        file_path = file_path or Path("<string>")

        for line_number, line in enumerate(content.splitlines(keepends=True), start=1):
            current_line = line

            for pattern in self.patterns:
                # Detect against the pristine line: redaction substitutions
                # (e.g. the vault's ***REDACTED:<hash>*** marker) must not be
                # re-scanned by later patterns as if they were new secrets.
                match = pattern.pattern.search(line)
                if not match:
                    continue

                matched_text = match.group(0)
                # Indicators are matched against the value, not the whole
                # line, so a trailing comment ("# example") cannot mask a
                # real secret.
                if self.is_false_positive(line, value=matched_text):
                    continue
                if not self._passes_entropy(pattern.name, matched_text):
                    continue

                replacement_text = SECRET_REDACTION_TEXT
                should_redact = True

                if callback:
                    secret_match = SecretMatch(
                        file=file_path,
                        line_number=line_number,
                        line_content=line.strip(),
                        pattern_name=pattern.name,
                        severity=pattern.severity,
                        matched_text=matched_text,
                    )
                    result = callback(secret_match)

                    if result == "KEEP" or result == "IGNORE":
                        should_redact = False
                    elif result == "REDACT":
                        should_redact = True
                    else:
                        # Use custom replacement (e.g., hashed redaction)
                        should_redact = True
                        replacement_text = result

                if should_redact:
                    # Replace the matched text with redaction
                    current_line = pattern.pattern.sub(replacement_text, current_line)
                    count += 1

            redacted_lines.append(current_line)

        return "".join(redacted_lines), count


def filter_secrets(
    content: str,
    callback: Callable[[SecretMatch], str] | None = None,
    file_path: Path | None = None,
) -> tuple[str, list[SecretMatch]]:
    """Filter secrets from content before saving.

    Returns:
        Tuple of (filtered_content, list_of_redacted_secrets)
        Note: Only secrets that were actually redacted are returned, not ignored ones.
    """
    scanner = get_custom_scanner()

    # Track which secrets were actually redacted
    redacted_secrets: list[SecretMatch] = []

    def tracking_callback(match: SecretMatch) -> str:
        if callback:
            result = callback(match)
            # Only add to redacted list if not ignored/kept
            if result not in ("KEEP", "IGNORE"):
                redacted_secrets.append(match)
            return result
        else:
            # No callback = always redact
            redacted_secrets.append(match)
            return "REDACT"

    filtered_content, _ = scanner.redact_content(content, tracking_callback, file_path)
    return filtered_content, redacted_secrets


def load_custom_patterns(config_data: dict, key_path: list[str]) -> list[SecretPattern]:
    """Load custom secret patterns from a configuration dictionary.

    Expects the config dictionary to have a list of pattern dicts at key_path:
    e.g., ['security', 'patterns'] or ['secrets', 'patterns']

    Each pattern entry should look like:
    { "name": "...", "pattern": "...", "severity": "...", "description": "..." }
    """
    data = config_data
    for key in key_path:
        if isinstance(data, dict):
            data = data.get(key, {})
        else:
            return []

    if not isinstance(data, list):
        return []

    patterns = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        pattern_str = item.get("pattern")
        if not name or not pattern_str:
            continue

        severity_str = str(item.get("severity", "HIGH")).upper()
        try:
            severity = Severity[severity_str]
        except KeyError:
            severity = Severity.HIGH

        description = str(item.get("description", f"Custom pattern {name}"))
        try:
            compiled = re.compile(pattern_str)
            patterns.append(
                SecretPattern(
                    name=name,
                    pattern=compiled,
                    severity=severity,
                    description=description,
                )
            )
        except re.error as e:
            logging.warning(
                f"Failed to compile custom regex pattern '{pattern_str}': {e}"
            )

    return patterns


def get_custom_scanner() -> SecretScanner:
    """Instantiate a SecretScanner populated with default and custom patterns."""
    try:
        from .operations import get_operations

        ops = get_operations()

        # Check if default patterns should be used
        use_default = True
        if ops.global_config and ops.global_config._data:
            use_default = ops.global_config._data.get("security", {}).get(
                "use_default_patterns", True
            )
        if ops.dotman_config and ops.dotman_config._data:
            use_default = ops.dotman_config._data.get("secrets", {}).get(
                "use_default_patterns", use_default
            )

        # Load global custom patterns
        global_patterns = []
        if ops.global_config and ops.global_config._data:
            global_patterns = load_custom_patterns(
                ops.global_config._data, ["security", "patterns"]
            )

        # Load repo custom patterns
        repo_patterns = []
        if ops.dotman_config and ops.dotman_config._data:
            repo_patterns = load_custom_patterns(
                ops.dotman_config._data, ["secrets", "patterns"]
            )

        base_patterns = DEFAULT_PATTERNS if use_default else []
        all_patterns = base_patterns + global_patterns + repo_patterns
        return SecretScanner(patterns=all_patterns)
    except Exception as e:
        # Fallback to default patterns if operations can't be loaded/fail
        logging.debug(f"Failed to load custom secret patterns: {e}")

    return SecretScanner()
