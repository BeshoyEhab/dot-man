"""Secret detection patterns and filtering logic."""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Callable, Generator

from .constants import SECRET_REDACTION_TEXT

import json
import hashlib
from datetime import datetime
from typing import TypedDict


class AllowedSecret(TypedDict):
    """Structure for an allowed secret entry."""

    file_path: str
    secret_hash: str
    pattern_name: str
    added_at: str


class SecretGuard:
    """Manages the list of allowed (skipped) secrets."""

    def __init__(self, config_dir: Path | None = None, path: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "dot-man"
        self.allow_list_path = path or (
            self.config_dir / ".dotman-allowed-secrets.json"
        )
        self._allowed_secrets: list[AllowedSecret] = self._load()

    def _load(self) -> list[AllowedSecret]:
        """Load allowed secrets from disk."""
        if not self.allow_list_path.exists():
            return []
        try:
            content = self.allow_list_path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception:
            return []

    def save(self) -> None:
        """Save allowed secrets to disk."""
        try:
            # Ensure directory exists
            self.allow_list_path.parent.mkdir(parents=True, exist_ok=True)

            content = json.dumps(self._allowed_secrets, indent=2)
            self.allow_list_path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of the content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_allowed(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> bool:
        """Check if a secret is in the allow list."""
        path_str = str(file_path)
        content_hash = self._compute_hash(line_content)

        for secret in self._allowed_secrets:
            if (
                secret["file_path"] == path_str
                and secret["secret_hash"] == content_hash
                and secret["pattern_name"] == pattern_name
            ):
                return True
        return False

    def add_allowed(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> None:
        """Add a secret to the allow list."""
        if self.is_allowed(file_path, line_content, pattern_name):
            return

        entry: AllowedSecret = {
            "file_path": str(file_path),
            "secret_hash": self._compute_hash(line_content),
            "pattern_name": pattern_name,
            "added_at": datetime.now().isoformat(),
        }
        self._allowed_secrets.append(entry)
        self.save()


class PermanentRedactGuard:
    """Manages the list of secrets that should always be redacted."""

    def __init__(self, config_dir: Path | None = None, path: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "dot-man"
        self.redact_list_path = path or (
            self.config_dir / ".dotman-permanent-redact.json"
        )
        self._redact_secrets: list[AllowedSecret] = self._load()

    def _load(self) -> list[AllowedSecret]:
        """Load permanent redact secrets from disk."""
        if not self.redact_list_path.exists():
            return []
        try:
            content = self.redact_list_path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception:
            return []

    def save(self) -> None:
        """Save permanent redact secrets to disk."""
        try:
            # Ensure directory exists
            self.redact_list_path.parent.mkdir(parents=True, exist_ok=True)

            content = json.dumps(self._redact_secrets, indent=2)
            self.redact_list_path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of the content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def should_redact(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> bool:
        """Check if a secret should be permanently redacted."""
        path_str = str(file_path)
        content_hash = self._compute_hash(line_content)

        for secret in self._redact_secrets:
            if (
                secret["file_path"] == path_str
                and secret["secret_hash"] == content_hash
                and secret["pattern_name"] == pattern_name
            ):
                return True
        return False

    def add_permanent_redact(
        self, file_path: Path | str, line_content: str, pattern_name: str
    ) -> None:
        """Add a secret to the permanent redact list."""
        if self.should_redact(file_path, line_content, pattern_name):
            return

        entry: AllowedSecret = {
            "file_path": str(file_path),
            "secret_hash": self._compute_hash(line_content),
            "pattern_name": pattern_name,
            "added_at": datetime.now().isoformat(),
        }
        self._redact_secrets.append(entry)
        self.save()


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
]

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

    def is_false_positive(self, line: str) -> bool:
        """Check if a line is likely a false positive."""
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in FALSE_POSITIVE_INDICATORS)

    def is_binary_file(self, path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(path, "rb") as f:
                chunk = f.read(8192)
                return b"\x00" in chunk
        except Exception:
            return True

    def scan_content(
        self, content: str | Generator[str, None, None], file_path: Path | None = None
    ) -> Iterator[SecretMatch]:
        """Scan content for secrets.

        Args:
            content: Text content or generator yielding lines
            file_path: Optional path for context
        """
        file_path = file_path or Path("<string>")

        iterator = content.splitlines() if isinstance(content, str) else content

        for line_number, line in enumerate(iterator, start=1):
            # Skip likely false positives
            if self.is_false_positive(line):
                continue

            for pattern in self.patterns:
                match = pattern.pattern.search(line)
                if match:
                    yield SecretMatch(
                        file=file_path,
                        line_number=line_number,
                        line_content=line.strip(),
                        pattern_name=pattern.name,
                        severity=pattern.severity,
                        matched_text=match.group(0),
                    )

    def scan_file(self, path: Path) -> Iterator[SecretMatch]:
        """Scan a file for secrets using streaming to save memory."""
        if self.is_binary_file(path):
            return

        try:
            # Use a generator to read lines lazily
            def line_generator():
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        yield line

            yield from self.scan_content(line_generator(), path)
        except Exception:
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

    def redact_content_stream(
        self,
        line_generator: Iterator[str],
        callback: Callable[[SecretMatch], str] | None = None,
        file_path: Path | None = None,
    ) -> Generator[tuple[str, int], None, None]:
        """
        Redact secrets from content stream. Yields (redacted_line, count_in_line).
        """
        file_path = file_path or Path("<string>")
        line_number = 0

        for line in line_generator:
            line_number += 1

            # Skip likely false positives (but preserve line)
            if self.is_false_positive(line):
                yield line, 0
                continue

            current_line = line
            count_in_line = 0

            # Remove newline for processing, add back later if needed?
            # Usually line iteration includes newline. Pattern matching might be sensitive.
            # Let's strip newline for matching but keep it conceptually or rebuild it.
            # Standard 'for line in f' includes \n.

            # Clean line for regex matching
            line_stripped = current_line.rstrip('\n')

            line_modified = False

            for pattern in self.patterns:
                match = pattern.pattern.search(line_stripped)
                if match:
                    should_redact = True
                    if callback:
                        secret_match = SecretMatch(
                            file=file_path,
                            line_number=line_number,
                            line_content=line_stripped.strip(),
                            pattern_name=pattern.name,
                            severity=pattern.severity,
                            matched_text=match.group(0),
                        )
                        action = callback(secret_match)
                        should_redact = action == "REDACT"

                    if should_redact:
                        # Replace the matched text with redaction
                        current_line = pattern.pattern.sub(
                            SECRET_REDACTION_TEXT, current_line
                        )
                        count_in_line += 1
                        line_modified = True

            yield current_line, count_in_line


    def redact_content(
        self,
        content: str,
        callback: Callable[[SecretMatch], str] | None = None,
        file_path: Path | None = None,
    ) -> tuple[str, int]:
        """
        Redact secrets from content (string version).
        Kept for backward compatibility but uses streaming internally.
        """
        redacted_lines = []
        total_count = 0

        # Split keeping newlines helps reconstruction, but splitlines() discards them usually
        # Let's use splitlines(keepends=True) or just simple join later

        iterator = content.splitlines(keepends=True)

        for line, count in self.redact_content_stream(iterator, callback, file_path):
            redacted_lines.append(line)
            total_count += count

        return "".join(redacted_lines), total_count


def filter_secrets(
    content: str,
    callback: Callable[[SecretMatch], str] | None = None,
    file_path: Path | None = None,
) -> tuple[str, list[SecretMatch]]:
    """Filter secrets from content string (Legacy/Memory based).

    Warning: Loads everything into memory.
    """
    scanner = SecretScanner()
    # We re-scan for matches separately from redaction because we need the full list
    # for the return value, although scanning twice is inefficient.
    # But since this function signature returns matches list, we must.
    matches = list(scanner.scan_content(content, file_path))
    filtered_content, _ = scanner.redact_content(content, callback, file_path)
    return filtered_content, matches
