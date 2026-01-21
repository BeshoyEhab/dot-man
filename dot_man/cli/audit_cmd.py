"""Audit command for dot-man CLI."""

import click

from .. import ui
from ..constants import REPO_DIR
from ..core import GitManager
from ..secrets import SecretScanner, SecretGuard, PermanentRedactGuard
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, require_init


@main.command()
@click.option(
    "--strict", is_flag=True, help="Exit with error if secrets found (for CI/CD)"
)
@click.option("--fix", is_flag=True, help="Automatically redact found secrets")
@require_init
def audit(strict: bool, fix: bool):
    """Scan repository for accidentally committed secrets.

    Scans all files in the repository for API keys, passwords,
    private keys, and other sensitive data.

    Use --strict in CI/CD pipelines to fail builds if secrets are found.
    """
    try:
        scanner = SecretScanner()
        guard = SecretGuard()
        permanent_guard = PermanentRedactGuard()

        ui.console.print("🔒 [bold]Security Audit[/bold]")
        ui.console.print()
        ui.console.print(f"Scanning [cyan]{REPO_DIR}[/cyan]...")
        ui.console.print()

        all_matches = list(scanner.scan_directory(REPO_DIR))

        # Filter out allowed or permanently redacted secrets
        matches = [
            match
            for match in all_matches
            if not guard.is_allowed(match.file, match.line_content, match.pattern_name)
            and not permanent_guard.should_redact(
                match.file, match.line_content, match.pattern_name
            )
        ]

        if not matches:
            success("No secrets detected. Repository is clean!")
            return

        # Group by severity
        by_severity = {}
        for match in matches:
            severity = match.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(match)

        # Display results
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        severity_colors = {
            "CRITICAL": "red",
            "HIGH": "yellow",
            "MEDIUM": "blue",
            "LOW": "dim",
        }

        for severity in severity_order:
            if severity not in by_severity:
                continue

            color = severity_colors[severity]
            items = by_severity[severity]

            ui.console.print(f"[{color}]{severity}[/{color}] ({len(items)} findings)")
            ui.console.print("─" * 50)

            for match in items:
                rel_path = match.file.relative_to(REPO_DIR)
                ui.console.print(f"  File: [cyan]{rel_path}[/cyan]")
                ui.console.print(
                    f"  Line {match.line_number}: {match.line_content[:60]}..."
                )
                ui.console.print(f"  Pattern: {match.pattern_name}")
                ui.console.print()

        # Summary
        ui.console.print("─" * 50)
        ui.console.print(
            f"[bold]Total:[/bold] {len(matches)} secrets in {len(set(m.file for m in matches))} files"
        )
        ui.console.print()

        # Recommendations
        ui.console.print("[bold]Recommendations:[/bold]")
        ui.console.print(
            "  1. Enable [cyan]secrets_filter = true[/cyan] for affected files"
        )
        ui.console.print("  2. Move credentials to environment variables")
        ui.console.print("  3. Run [cyan]dot-man audit --fix[/cyan] to auto-redact")

        if fix:
            ui.console.print()
            if not ui.confirm("Auto-redact all detected secrets?"):
                ui.info("Aborted.")
                return

            # Perform redaction
            fixed_files = set()
            for match in matches:
                if match.file in fixed_files:
                    continue

                content = match.file.read_text()
                redacted, count = scanner.redact_content(content)
                if count > 0:
                    match.file.write_text(redacted)
                    fixed_files.add(match.file)
                    ui.console.print(
                        f"  [green]✓[/green] Redacted {count} secrets in {match.file.name}"
                    )

            # Commit changes
            git = GitManager()
            git.commit("Security: Auto-redacted secrets detected by audit")
            success(f"Redacted secrets in {len(fixed_files)} files")

        if strict:
            error("Secrets detected (strict mode)", exit_code=50)

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Audit failed: {e}")
