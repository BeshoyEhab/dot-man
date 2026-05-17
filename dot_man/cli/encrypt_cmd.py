"""Encryption command for encrypting/decrypting sensitive dotfiles."""

from pathlib import Path
from typing import Literal

import click

from .. import ui
from ..encryption import (
    EncryptionError,
    EncryptionManager,
    detect_available_encryption,
)
from .common import error, require_init, success, warn
from .interface import cli as main


@main.command("encrypt")
@click.argument("action", type=click.Choice(["encrypt", "decrypt", "status"]))
@click.argument("section", required=False)
@click.option(
    "--method",
    "-m",
    type=click.Choice(["gpg", "age"]),
    default="gpg",
    help="Encryption method to use",
)
@click.option(
    "--recipient",
    "-r",
    help="Encryption recipient (GPG key ID or AGE recipient)",
)
@require_init
def encrypt_cmd(action: str, section: str | None, method: str, recipient: str | None):
    """Encrypt or decrypt sensitive dotfile sections.

    Actions:
      encrypt  - Encrypt a section's files
      decrypt  - Decrypt a section's files
      status   - Show encryption status of all sections

    Examples:
        dot-man encrypt status                # Show encryption status
        dot-man encrypt encrypt ssh-config   # Encrypt ssh-config section
        dot-man encrypt decrypt ssh-config   # Decrypt ssh-config section
        dot-man encrypt encrypt secrets -r age1...  # Use AGE encryption
    """
    available = detect_available_encryption()
    if not available:
        error(
            "No encryption tools available. Install GPG or AGE:\n"
            "  GPG: brew install gpg\n"
            "  AGE: brew install age",
            exit_code=1,
        )

    if method not in available:
        warn(f"{method} not available. Using {available[0]} instead.")
        method = available[0]  # type: ignore[assignment]

    if action == "status":
        _show_encryption_status()
    elif action == "encrypt":
        _encrypt_section(section, method, recipient)  # type: ignore[arg-type]
    elif action == "decrypt":
        _decrypt_section(section, method, recipient)  # type: ignore[arg-type]


def _show_encryption_status():
    """Show encryption status of all sections."""
    from ..operations import get_operations

    ops = get_operations()

    ui.console.print("[bold]Encryption Status:[/bold]")
    ui.console.print()

    has_encrypted = False

    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        if section.encrypted:
            has_encrypted = True
            ui.console.print(f"  [green]✓[/green] [{section_name}]")
            ui.console.print(f"      Method: {section.encryption_method}")
            if section.encryption_recipient:
                ui.console.print(f"      Recipient: {section.encryption_recipient}")
        else:
            ui.console.print(f"  [dim]-[/dim] [{section_name}] (not encrypted)")

    if not has_encrypted:
        ui.console.print("[dim]No encrypted sections configured[/dim]")
        ui.console.print()
        ui.console.print("To encrypt a section, add to dot-man.toml:")
        ui.console.print("  [cyan][ssh-config][/cyan]")
        ui.console.print("  [cyan]encrypted = true[/cyan]")
        ui.console.print('  [cyan]encryption_method = "gpg"[/cyan]')
        ui.console.print('  [cyan]encryption_recipient = "your@email.com"[/cyan]')


def _encrypt_section(
    section_name: str | None, method: Literal["gpg", "age"], recipient: str | None
):
    """Encrypt a section's files."""
    if not section_name:
        error("Section name required for encryption", exit_code=1)

    from ..dotman_config import DotManConfig
    from ..operations import get_operations

    ops = get_operations()
    config = DotManConfig()

    assert section_name is not None
    section = ops.get_section(section_name)
    if not section:
        error(f"Section not found: {section_name}", exit_code=1)

    if recipient is None:
        if section.encryption_recipient:
            recipient = section.encryption_recipient
        else:
            error(
                "No recipient specified. Use --recipient or set encryption_recipient in config",
                exit_code=1,
            )

    ui.console.print(f"[dim]Encrypting section: {section_name}[/dim]")

    enc = EncryptionManager(method)

    for path_str in section.paths:
        local_path = Path(path_str).expanduser()
        repo_dir_str = ops.git.repo.working_dir
        assert repo_dir_str is not None
        repo_path = section.get_repo_path(local_path, Path(repo_dir_str))

        if not local_path.exists():
            warn(f"File not found: {local_path}")
            continue

        encrypted_path = repo_path.with_suffix(repo_path.suffix + ".gpg")

        try:
            enc.encrypt_file(local_path, encrypted_path, recipient)
            ui.console.print(f"  [green]✓[/green] Encrypted: {local_path.name}")
        except EncryptionError as e:
            warn(f"Failed to encrypt {local_path.name}: {e}")

    config.update_section(
        section_name,
        encrypted=True,
        encryption_method=method,
        encryption_recipient=recipient,
    )
    config.save()

    success(f"Encrypted section '{section_name}'")


def _decrypt_section(
    section_name: str | None, method: Literal["gpg", "age"], recipient: str | None
):
    """Decrypt a section's files."""
    if not section_name:
        error("Section name required for decryption", exit_code=1)

    from ..dotman_config import DotManConfig
    from ..operations import get_operations

    ops = get_operations()
    config = DotManConfig()

    assert section_name is not None
    section = ops.get_section(section_name)
    if not section:
        error(f"Section not found: {section_name}", exit_code=1)

    ui.console.print(f"[dim]Decrypting section: {section_name}[/dim]")

    enc = EncryptionManager(method)

    for path_str in section.paths:
        local_path = Path(path_str).expanduser()
        repo_dir_str = ops.git.repo.working_dir
        assert repo_dir_str is not None
        repo_path = section.get_repo_path(local_path, Path(repo_dir_str))

        encrypted_path = repo_path.with_suffix(repo_path.suffix + ".gpg")

        if not encrypted_path.exists():
            warn(f"Encrypted file not found: {encrypted_path}")
            continue

        try:
            enc.decrypt_file(encrypted_path, local_path, recipient)
            ui.console.print(f"  [green]✓[/green] Decrypted: {local_path.name}")
        except EncryptionError as e:
            warn(f"Failed to decrypt {local_path.name}: {e}")

    assert section_name is not None
    config.update_section(section_name, encrypted=False)
    config.save()

    success(f"Decrypted section '{section_name}'")
