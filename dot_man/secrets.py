"""Secret detection patterns and filtering logic."""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator

from .constants import SECRET_REDACTION_TEXT, DOTMAN_REDACTION_TEXT


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
        pattern=re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE KEY-----"),
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
        pattern=re.compile(r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?[\w-]{20,}['\"]?", re.IGNORECASE),
        severity=Severity.HIGH,
        description="Generic API key assignment",
    ),
    SecretPattern(
        name="Password Assignment",
        pattern=re.compile(r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?.+['\"]?", re.IGNORECASE),
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
        pattern=re.compile(r"(?:auth[_-]?token|token)\s*[=:]\s*['\"]?[\w-]{20,}['\"]?", re.IGNORECASE),
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
        pattern=re.compile(r"(?:secret|credential)\s*[=:]\s*['\"]?.+['\"]?", re.IGNORECASE),
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
        self, content: str, file_path: Path | None = None
    ) -> Iterator[SecretMatch]:
        """Scan content for secrets."""
        file_path = file_path or Path("<string>")

        for line_number, line in enumerate(content.splitlines(), start=1):
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
        """Scan a file for secrets."""
        if self.is_binary_file(path):
            return

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            yield from self.scan_content(content, path)
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

    def redact_content(self, content: str) -> tuple[str, int]:
        """Redact secrets from content. Returns (redacted_content, count)."""
        redacted = content
        count = 0

        for line_number, line in enumerate(content.splitlines()):
            if self.is_false_positive(line):
                continue

            for pattern in self.patterns:
                match = pattern.pattern.search(line)
                if match:
                    # Replace the matched text with redaction
                    redacted_line = pattern.pattern.sub(SECRET_REDACTION_TEXT, line)
                    redacted = redacted.replace(line, redacted_line, 1)
                    count += 1

        return redacted, count


def filter_secrets(content: str) -> tuple[str, list[SecretMatch]]:
    """Filter secrets from content before saving.

    Returns:
        Tuple of (filtered_content, list_of_matches)
    """
    scanner = SecretScanner()
    matches = list(scanner.scan_content(content))
    filtered_content, _ = scanner.redact_content(content)
    return filtered_content, matches
