"""Vault command for managing the secret vault."""

import click

from .. import ui
from .common import AliasedCommand, error, require_init, success, warn
from .interface import cli as main


@main.command("vault", cls=AliasedCommand, aliases=["vlt"])
@click.argument(
    "action",
    type=click.Choice(["rotate-key", "status"]),
)
@require_init
def vault_cmd(action: str):
    """Manage the secret vault.

    Actions:
      rotate-key  - Generate a new encryption key and re-encrypt all secrets
      status      - Show vault statistics

    Examples:
        dot-man vault rotate-key   # Rotate the Fernet encryption key
        dot-man vault status       # Show vault info
    """
    if action == "rotate-key":
        _rotate_key()
    elif action == "status":
        _vault_status()


def _rotate_key():
    """Rotate the vault encryption key."""
    from ..vault import SecretVault

    vault = SecretVault()
    vault.load()

    count = len(vault._data.get("secrets", []))
    if count == 0:
        warn("Vault is empty — nothing to re-encrypt.")
        return

    ui.console.print(f"Found [cyan]{count}[/cyan] encrypted secret(s).")
    if not ui.confirm("Generate a new key and re-encrypt all secrets?"):
        ui.console.print("[dim]Aborted.[/dim]")
        return

    try:
        reencrypted = vault.rotate_key()
        success(f"Key rotated. Re-encrypted {reencrypted} secret(s).")
        ui.console.print("[dim]Old key backed up to .key.bak[/dim]")
    except Exception as e:
        error(f"Key rotation failed: {e}", exit_code=1)


def _vault_status():
    """Show vault statistics."""
    from ..constants import DOT_MAN_DIR
    from ..vault import SecretVault

    vault = SecretVault()
    vault.load()

    key_file = DOT_MAN_DIR / ".key"
    vault_file = DOT_MAN_DIR / "vault.json"
    backup_file = DOT_MAN_DIR / ".key.bak"

    count = len(vault._data.get("secrets", []))

    ui.console.print("[bold]Vault Status[/bold]")
    ui.console.print()

    if key_file.exists():
        ui.console.print(f"  Key:      [green]✓[/green] {key_file}")
    else:
        ui.console.print("  Key:      [red]✗[/red] Not found")

    if backup_file.exists():
        ui.console.print(f"  Backup:   [yellow]✓[/yellow] {backup_file}")

    if vault_file.exists():
        size = vault_file.stat().st_size
        ui.console.print(f"  Vault:    [green]✓[/green] {vault_file} ({size} bytes)")
    else:
        ui.console.print("  Vault:    [dim]Empty[/dim]")

    ui.console.print(f"  Secrets:  [cyan]{count}[/cyan]")

    if count > 0:
        branches = set(s.get("branch", "unknown") for s in vault._data["secrets"])
        ui.console.print(f"  Branches: {', '.join(sorted(branches))}")
