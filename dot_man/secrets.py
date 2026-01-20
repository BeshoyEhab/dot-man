"""Secret detection patterns and filtering logic."""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from pathlib import Path
from typing import Iterable, Iterator, Callable

from .constants import SECRET_REDACTION_TEXT, DOT_MAN_DIR

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
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        except OSError:
            return []

    def save(self) -> None:
        """Save allowed secrets to disk."""
        try:
            # Ensure directory exists
            self.allow_list_path.parent.mkdir(parents=True, exist_ok=True)

            content = json.dumps(self._allowed_secrets, indent=2)
            self.allow_list_path.write_text(content, encoding="utf-8")
        except OSError:
            pass  # Fail silently if we can't write, likely permissions

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
        self.config_dir = config_dir or DOT_MAN_DIR
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
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        except OSError:
            return []

    def save(self) -> None:
        """Save permanent redact secrets to disk."""
        try:
            # Ensure directory exists
            self.redact_list_path.parent.mkdir(parents=True, exist_ok=True)

            content = json.dumps(self._redact_secrets, indent=2)
            self.redact_list_path.write_text(content, encoding="utf-8")
        except OSError:
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
        except OSError:
            return True  # Assume binary if we can't read it

    def scan_lines(
        self, lines: Iterable[str], file_path: Path | None = None
    ) -> Iterator[SecretMatch]:
        """Scan lines for secrets."""
        file_path = file_path or Path("<string>")

        for line_number, line in enumerate(lines, start=1):
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

        for line_number, line in enumerate(content.splitlines(), start=1):
            # precise matching logic needed to handle multiple secrets in one line appropriately
            # checking for false positives first
            if self.is_false_positive(line):
                redacted_lines.append(line)
                continue

            current_line = line
            line_modified = False

            for pattern in self.patterns:
                match = pattern.pattern.search(current_line)
                if match:
                    replacement_text = SECRET_REDACTION_TEXT
                    should_redact = True
                    matched_text = match.group(0)

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
                        
                        if result == "KEEP":
                            should_redact = False
                        elif result == "REDACT":
                            should_redact = True
                        else:
                            # Use custom replacement
                            should_redact = True
                            replacement_text = result

                    if should_redact:
                        # Replace the matched text with redaction
                        current_line = pattern.pattern.sub(
                            replacement_text, current_line
                        )
                        count += 1
                        line_modified = True

            redacted_lines.append(current_line)

        return "\n".join(redacted_lines), count


def filter_secrets(
    content: str,
    callback: Callable[[SecretMatch], str] | None = None,
    file_path: Path | None = None,
) -> tuple[str, list[SecretMatch]]:
    """Filter secrets from content before saving.

    Returns:
        Tuple of (filtered_content, list_of_matches)
    """
    scanner = SecretScanner()
    # Note: We aren't returning the matches list here perfectly if we use the callback
    # because the callback might Skip/Ignore them.
    # But usually we return the list of *detected* secrets for logging.
    matches = list(scanner.scan_content(content, file_path))
    filtered_content, _ = scanner.redact_content(content, callback, file_path)
    return filtered_content, matches
