"""dot-man CLI: Dotfile manager with git-powered branching."""

import sys
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from . import __version__
from .constants import (
    DOT_MAN_DIR,
    REPO_DIR,
    BACKUPS_DIR,
    DEFAULT_BRANCH,
    FILE_PERMISSIONS,
)
from .config import GlobalConfig, DotManConfig
from .core import GitManager
from .files import copy_file, get_file_status, backup_file, compare_files
from .secrets import SecretScanner, Severity
from .utils import get_editor, open_in_editor, is_git_installed, confirm
from .exceptions import (
    DotManError,
    NotInitializedError,
    AlreadyInitializedError,
    GitNotFoundError,
    SecretsDetectedError,
)

console = Console()


def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        git = GitManager()
        branches = git.list_branches()
        return [b for b in branches if b.startswith(incomplete)]
    except Exception:
        return []


def error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit."""
    console.print(f"[red]✗ Error:[/red] {message}")
    sys.exit(exit_code)


def success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def warn(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def require_init(func):
    """Decorator to require initialization before running command."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not DOT_MAN_DIR.exists() or not REPO_DIR.exists():
            error("Not initialized. Run 'dot-man init' first.", exit_code=1)
        return func(*args, **kwargs)

    return wrapper


# ============================================================================
# Main CLI Group
# ============================================================================


@click.group()
@click.version_option(version=__version__, prog_name="dot-man")
def main():
    """dot-man: Dotfile manager with git-powered branching.

    Manage your dotfiles across multiple machines using git branches.
    Each branch represents a different configuration (work, personal, minimal).
    """
    pass


# ============================================================================
# init Command
# ============================================================================


@main.command()
@click.option("--force", is_flag=True, help="Reinitialize even if already exists")
def init(force: bool):
    """Initialize a new dot-man repository.

    Creates the repository structure at ~/.config/dot-man/ and sets up
    git for version control of your dotfiles.
    """
    # Pre-checks
    if not is_git_installed():
        error("Git not found. Please install git first.", exit_code=2)

    if DOT_MAN_DIR.exists() and not force:
        if not confirm("Repository already initialized. Reinitialize? (This will DELETE all data)"):
            console.print("Aborted.")
            sys.exit(1)

        import shutil
        shutil.rmtree(DOT_MAN_DIR)

    try:
        # Create directory structure
        DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
        DOT_MAN_DIR.chmod(FILE_PERMISSIONS)
        REPO_DIR.mkdir(parents=True, exist_ok=True)
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize git repository
        git = GitManager()
        git.init()

        # Create global configuration
        global_config = GlobalConfig()
        global_config.create_default()

        # Create default dot-man.ini
        dotman_config = DotManConfig()
        dotman_config.create_default()

        # Initial commit
        git.commit("dot-man: Initial commit")

        # Success message
        console.print()
        success("dot-man initialized successfully!")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print("  1. Edit configuration: [cyan]dot-man edit[/cyan]")
        console.print("  2. Add your dotfiles to dot-man.ini")
        console.print("  3. Save configuration: [cyan]dot-man switch main[/cyan]")
        console.print("  4. View status: [cyan]dot-man status[/cyan]")

    except Exception as e:
        error(f"Initialization failed: {e}")


# ============================================================================
# status Command
# ============================================================================


@main.command()
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
@click.option("--secrets", is_flag=True, help="Highlight files with detected secrets")
@require_init
def status(verbose: bool, secrets: bool):
    """Display current repository status.

    Shows the current branch, tracked files, and any pending changes
    that would be saved on the next switch.
    """
    try:
        # Load configurations
        global_config = GlobalConfig()
        global_config.load()

        dotman_config = DotManConfig()
        dotman_config.load()

        git = GitManager()

        # Repository info panel
        branch = global_config.current_branch
        remote = global_config.remote_url or "[dim]Not configured[/dim]"

        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column(style="cyan")
        info_table.add_column()
        info_table.add_row("Current Branch:", f"[bold]{branch}[/bold]")
        info_table.add_row("Remote:", remote)
        info_table.add_row("Repository:", str(REPO_DIR))

        console.print(Panel(info_table, title="[bold]Repository Status[/bold]", border_style="blue"))
        console.print()

        # File status table
        sections = dotman_config.get_sections()
        if not sections:
            console.print("[dim]No files tracked. Run 'dot-man edit' to add files.[/dim]")
            return

        file_table = Table(title="Tracked Files")
        file_table.add_column("File", style="cyan")
        file_table.add_column("Status")
        file_table.add_column("Details", style="dim")

        status_colors = {
            "NEW": "blue",
            "MODIFIED": "yellow",
            "DELETED": "red",
            "IDENTICAL": "green",
        }

        scanner = SecretScanner() if secrets else None
        secrets_found = []

        for section_name in sections:
            section = dotman_config.get_section(section_name)
            local_path = section["local_path"]
            repo_path = section["repo_path"]

            file_status = get_file_status(local_path, repo_path)
            color = status_colors.get(file_status, "white")

            details = ""
            if file_status == "MODIFIED" and verbose:
                # Could show line diff here
                details = "Content differs"

            # Check for secrets
            secret_indicator = ""
            if secrets and local_path.exists() and local_path.is_file():
                matches = list(scanner.scan_file(local_path))
                if matches:
                    secret_indicator = " [red]🔒[/red]"
                    secrets_found.extend(matches)

            file_table.add_row(
                str(local_path) + secret_indicator,
                f"[{color}]{file_status}[/{color}]",
                details,
            )

        console.print(file_table)

        # Secrets warning
        if secrets_found:
            console.print()
            warn(f"{len(secrets_found)} potential secrets detected. Run 'dot-man audit' for details.")

        # Git status
        if git.is_dirty():
            console.print()
            console.print("[yellow]Repository has uncommitted changes.[/yellow]")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Status check failed: {e}")


# ============================================================================
# switch Command
# ============================================================================


@main.command()
@click.argument("branch", shell_complete=complete_branches)
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@require_init
def switch(branch: str, dry_run: bool, force: bool):
    """Switch to a different configuration branch.

    Saves current changes to the current branch, then deploys files
    from the target branch. Creates the branch if it doesn't exist.

    Example: dot-man switch work
    """
    try:
        global_config = GlobalConfig()
        global_config.load()

        dotman_config = DotManConfig()
        dotman_config.load()

        git = GitManager()

        current_branch = global_config.current_branch

        # Check if already on target branch
        if current_branch == branch and not dry_run:
            console.print(f"Already on branch '[bold]{branch}[/bold]'")
            return

        if dry_run:
            console.print(f"[dim]Dry run - no changes will be made[/dim]")
            console.print()

        # Phase 1: Save current branch state
        console.print(f"[bold]Phase 1:[/bold] Saving current branch '{current_branch}'...")

        sections = dotman_config.get_sections()
        saved_count = 0
        secrets_detected = []

        for section_name in sections:
            section = dotman_config.get_section(section_name)
            local_path = section["local_path"]
            repo_path = section["repo_path"]
            filter_secrets = section.get("secrets_filter", True)

            if not local_path.exists():
                if repo_path.exists() and not dry_run:
                    # File deleted locally - remove from repo
                    repo_path.unlink()
                continue

            if dry_run:
                file_status = get_file_status(local_path, repo_path)
                console.print(f"  Would save: {local_path} [{file_status}]")
            else:
                success_copy, secrets = copy_file(local_path, repo_path, filter_secrets)
                if success_copy:
                    saved_count += 1
                secrets_detected.extend(secrets)

        if secrets_detected:
            warn(f"{len(secrets_detected)} secrets were redacted during save")

        if not dry_run:
            # Commit changes
            commit_msg = f"Auto-save from '{current_branch}' before switch to '{branch}'"
            commit_sha = git.commit(commit_msg)
            if commit_sha:
                console.print(f"  Committed: [dim]{commit_sha[:7]}[/dim]")

        # Phase 2: Switch branch
        console.print()
        console.print(f"[bold]Phase 2:[/bold] Switching to branch '{branch}'...")

        branch_exists = git.branch_exists(branch)
        if dry_run:
            if branch_exists:
                console.print(f"  Would checkout existing branch: {branch}")
            else:
                console.print(f"  Would create new branch: {branch}")
        else:
            git.checkout(branch, create=not branch_exists)

            if not branch_exists:
                console.print(f"  Created new branch: [cyan]{branch}[/cyan]")

        # Phase 3: Deploy new branch files
        console.print()
        console.print(f"[bold]Phase 3:[/bold] Deploying '{branch}' configuration...")

        # Reload config for new branch
        if not dry_run:
            dotman_config.load()

        deployed_count = 0
        pre_deploy_cmds = []
        post_deploy_cmds = []
        sections_to_deploy = []

        # Pass 1: Analyze changes and collect hooks
        for section_name in dotman_config.get_sections():
            section = dotman_config.get_section(section_name)
            local_path = section["local_path"]
            repo_path = section["repo_path"]
            strategy = section.get("update_strategy", "replace")
            post_deploy = section.get("post_deploy")
            pre_deploy = section.get("pre_deploy")

            if not repo_path.exists():
                continue

            # Check if file will change
            will_change = not local_path.exists() or not compare_files(repo_path, local_path)
            
            if will_change:
                if pre_deploy:
                    pre_deploy_cmds.append(pre_deploy)
                if post_deploy:
                    post_deploy_cmds.append(post_deploy)
            
            sections_to_deploy.append((section, will_change))

        # Run pre-deploy hooks
        if not dry_run and pre_deploy_cmds:
            console.print()
            console.print("[bold]Running pre-deploy hooks...[/bold]")
            unique_pre_cmds = list(dict.fromkeys(pre_deploy_cmds))
            for cmd in unique_pre_cmds:
                console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
            console.print()

        # Pass 2: Deploy files
        for section, will_change in sections_to_deploy:
            local_path = section["local_path"]
            repo_path = section["repo_path"]
            strategy = section.get("update_strategy", "replace")
            post_deploy = section.get("post_deploy")
            pre_deploy = section.get("pre_deploy")

            if dry_run:
                console.print(f"  Would deploy: {repo_path} -> {local_path}")
                if will_change:
                    if pre_deploy:
                        console.print(f"    [dim]Pre-hook:[/dim]  {pre_deploy}")
                    if post_deploy:
                        console.print(f"    [dim]Post-hook:[/dim] {post_deploy}")
                else:
                    console.print("    [dim](No changes needed)[/dim]")
            else:
                if not will_change:
                     # Optimization: Skip copy if identical
                     console.print(f"  [dim]-[/dim] {local_path} (unchanged)")
                     deployed_count += 1
                     continue

                if strategy == "rename_old" and local_path.exists():
                    backup_file(local_path)

                if strategy != "ignore":
                    success_copy, _ = copy_file(repo_path, local_path, filter_secrets_enabled=False)
                    if success_copy:
                        deployed_count += 1

        # Update global config
        if not dry_run:
            global_config.current_branch = branch
            global_config._config["dot-man"]["last_switch"] = datetime.now().isoformat()
            global_config.save()

            # Run post-deploy hooks
            if post_deploy_cmds:
                console.print()
                console.print("[bold]Running post-deploy hooks...[/bold]")
                unique_post_cmds = list(dict.fromkeys(post_deploy_cmds))
                
                for cmd in unique_post_cmds:
                    console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                    try:
                        subprocess.run(cmd, shell=True, check=False)
                    except Exception as e:
                        warn(f"Failed to run command '{cmd}': {e}")

        # Summary
        console.print()
        if dry_run:
            console.print("[dim]Dry run complete. No changes were made.[/dim]")
        else:
            success(f"Switched to '{branch}'")
            console.print()
            console.print(f"  • Saved {saved_count} files from '{current_branch}'")
            console.print(f"  • Deployed {deployed_count} files for '{branch}'")
            console.print()
            console.print("Run [cyan]dot-man status[/cyan] to verify.")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Switch failed: {e}")


# ============================================================================
# edit Command
# ============================================================================


@main.command()
@click.option("--editor", help="Editor to use (default: $VISUAL or $EDITOR)")
@click.option("--global", "edit_global", is_flag=True, help="Edit global configuration")
@require_init
def edit(editor: str | None, edit_global: bool):
    """Open the configuration file in your text editor.

    By default, opens the dot-man.ini file for the current branch.
    Use --global to edit the global configuration.
    """
    try:
        if edit_global:
            from .constants import GLOBAL_CONF
            target = GLOBAL_CONF
            desc = "global configuration"
        else:
            target = REPO_DIR / "dot-man.ini"
            desc = "dot-man.ini"

        if not target.exists():
            error(f"Configuration file not found: {target}")

        editor_cmd = editor or get_editor()
        console.print(f"Opening {desc} in [cyan]{editor_cmd}[/cyan]...")

        if not open_in_editor(target, editor_cmd):
            error(f"Editor '{editor_cmd}' exited with error")

        # Validate after edit
        if not edit_global:
            dotman_config = DotManConfig()
            try:
                dotman_config.load()
                warnings = dotman_config.validate()
                if warnings:
                    console.print()
                    warn("Configuration has warnings:")
                    for w in warnings:
                        console.print(f"  • {w}")
                else:
                    success("Configuration updated and validated")
            except Exception as e:
                warn(f"Configuration may have errors: {e}")
        else:
            success("Global configuration updated")

    except DotManError as e:
        error(str(e), e.exit_code)


# ============================================================================
# deploy Command
# ============================================================================


@main.command()
@click.argument("branch", shell_complete=complete_branches)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--dry-run", is_flag=True, help="Show what would be deployed")
@require_init
def deploy(branch: str, force: bool, dry_run: bool):
    """One-way deployment of a branch configuration.

    Deploys files from the specified branch to your home directory.
    Unlike 'switch', this does NOT save current local changes first.
    Typically used for setting up a new machine.

    Example: dot-man deploy main
    """
    try:
        git = GitManager()

        # Check branch exists
        if not git.branch_exists(branch):
            available = ", ".join(git.list_branches())
            error(f"Branch '{branch}' not found. Available: {available}")

        if not force and not dry_run:
            console.print(Panel(
                "[yellow]WARNING: Deploy will OVERWRITE local files![/yellow]\n\n"
                "This will:\n"
                f"• Deploy '{branch}' configuration\n"
                "• Overwrite existing dotfiles\n"
                "• Local changes will be LOST\n\n"
                "[dim]Typical use: Setting up a new machine[/dim]",
                title="⚠️  Destructive Operation",
                border_style="yellow"
            ))

            if not confirm("Continue?"):
                console.print("Aborted.")
                return

        # Checkout branch
        if not dry_run:
            git.checkout(branch)

        # Load config
        dotman_config = DotManConfig()
        dotman_config.load()

        sections = dotman_config.get_sections()
        if not sections:
            warn("No files configured in this branch")
            return

        # Deploy files
        console.print(f"Deploying [bold]{branch}[/bold] configuration...")
        console.print()

        deployed = 0
        skipped = 0
        pre_deploy_cmds = []
        post_deploy_cmds = []
        sections_to_deploy = []

        # Pass 1: Collect hooks and potential changes
        for section_name in sections:
            section = dotman_config.get_section(section_name)
            local_path = section["local_path"]
            repo_path = section["repo_path"]
            post_deploy = section.get("post_deploy")
            pre_deploy = section.get("pre_deploy")

            if not repo_path.exists():
                console.print(f"  [dim]Skip:[/dim] {repo_path} (missing)")
                skipped += 1
                continue

            # Check if file will change
            will_change = not local_path.exists() or not compare_files(repo_path, local_path)
            
            if will_change:
                if pre_deploy:
                    pre_deploy_cmds.append(pre_deploy)
                if post_deploy:
                    post_deploy_cmds.append(post_deploy)
            
            sections_to_deploy.append((section, will_change))

        # Run pre-deploy hooks
        if not dry_run and pre_deploy_cmds:
            console.print()
            console.print("[bold]Running pre-deploy hooks...[/bold]")
            unique_pre_cmds = list(dict.fromkeys(pre_deploy_cmds))
            for cmd in unique_pre_cmds:
                console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
            console.print()

        # Pass 2: Deploy files
        for section, will_change in sections_to_deploy:
            local_path = section["local_path"]
            repo_path = section["repo_path"]
            strategy = section.get("update_strategy", "replace")
            post_deploy = section.get("post_deploy")
            pre_deploy = section.get("pre_deploy")

            if dry_run:
                action = "OVERWRITE" if local_path.exists() else "CREATE"
                console.print(f"  Would {action}: {local_path}")
                if will_change:
                    if pre_deploy:
                        console.print(f"    [dim]Pre-hook:[/dim]  {pre_deploy}")
                    if post_deploy:
                        console.print(f"    [dim]Post-hook:[/dim] {post_deploy}")
                else:
                    console.print("    [dim](No changes needed)[/dim]")
            else:
                if not will_change:
                     # Optimization: Skip copy if identical
                     console.print(f"  [dim]-[/dim] {local_path} (unchanged)")
                     deployed += 1 
                     continue

                if strategy == "rename_old" and local_path.exists():
                    backup_file(local_path)

                if strategy != "ignore":
                    success_copy, _ = copy_file(repo_path, local_path, filter_secrets_enabled=False)
                    if success_copy:
                        console.print(f"  [green]✓[/green] {local_path}")
                        deployed += 1
                    else:
                        console.print(f"  [red]✗[/red] {local_path}")

        # Run post-deploy hooks (only if not dry_run)
        if not dry_run and post_deploy_cmds:
            console.print()
            console.print("[bold]Running post-deploy hooks...[/bold]")
            unique_cmds = list(dict.fromkeys(post_deploy_cmds))
            for cmd in unique_cmds:
                console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")

        # Update global config
        if not dry_run:
            global_config = GlobalConfig()
            global_config.load()
            global_config.current_branch = branch
            global_config.save()

        console.print()
        if dry_run:
            console.print(f"[dim]Dry run: {len(sections) - skipped} files would be deployed[/dim]")
        else:
            success(f"Deployed {deployed} files from '{branch}'")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Deployment failed: {e}")


# ============================================================================
# audit Command
# ============================================================================


@main.command()
@click.option("--strict", is_flag=True, help="Exit with error if secrets found (for CI/CD)")
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

        console.print("🔒 [bold]Security Audit[/bold]")
        console.print()
        console.print(f"Scanning [cyan]{REPO_DIR}[/cyan]...")
        console.print()

        matches = list(scanner.scan_directory(REPO_DIR))

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

            console.print(f"[{color}]{severity}[/{color}] ({len(items)} findings)")
            console.print("─" * 50)

            for match in items:
                rel_path = match.file.relative_to(REPO_DIR)
                console.print(f"  File: [cyan]{rel_path}[/cyan]")
                console.print(f"  Line {match.line_number}: {match.line_content[:60]}...")
                console.print(f"  Pattern: {match.pattern_name}")
                console.print()

        # Summary
        console.print("─" * 50)
        console.print(f"[bold]Total:[/bold] {len(matches)} secrets in {len(set(m.file for m in matches))} files")
        console.print()

        # Recommendations
        console.print("[bold]Recommendations:[/bold]")
        console.print("  1. Enable [cyan]secrets_filter = true[/cyan] for affected files")
        console.print("  2. Move credentials to environment variables")
        console.print("  3. Run [cyan]dot-man audit --fix[/cyan] to auto-redact")

        if fix:
            console.print()
            if not confirm("Auto-redact all detected secrets?"):
                console.print("Aborted.")
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
                    console.print(f"  [green]✓[/green] Redacted {count} secrets in {match.file.name}")

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


# ============================================================================
# branch Commands
# ============================================================================


@main.group()
def branch():
    """Manage configuration branches."""
    pass


@branch.command("list")
@require_init
def branch_list():
    """List all configuration branches."""
    try:
        git = GitManager()
        global_config = GlobalConfig()
        global_config.load()

        current = global_config.current_branch
        branches = git.list_branches()

        if not branches:
            console.print("[dim]No branches found[/dim]")
            return

        table = Table(title="Branches")
        table.add_column("Branch")
        table.add_column("Active")

        for b in branches:
            active = "[green]✓[/green]" if b == current else ""
            style = "bold" if b == current else ""
            table.add_row(f"[{style}]{b}[/{style}]" if style else b, active)

        console.print(table)

    except Exception as e:
        error(f"Failed to list branches: {e}")


@branch.command("delete")
@click.argument("name", shell_complete=complete_branches)
@click.option("--force", "-f", is_flag=True, help="Force delete without confirmation")
@require_init
def branch_delete(name: str, force: bool):
    """Delete a configuration branch."""
    try:
        git = GitManager()
        global_config = GlobalConfig()
        global_config.load()

        if name == global_config.current_branch:
            error("Cannot delete the active branch. Switch to another branch first.")

        if not git.branch_exists(name):
            error(f"Branch '{name}' not found")

        if not force:
            if not confirm(f"Delete branch '{name}'? This cannot be undone"):
                console.print("Aborted.")
                return

        git.delete_branch(name, force=force)
        success(f"Deleted branch '{name}'")

    except DotManError as e:
        # Import locally to avoid circular import issues if placed at top
        from .exceptions import BranchNotMergedError
        if isinstance(e, BranchNotMergedError):
            if confirm(f"Branch '{name}' is not fully merged. Force delete?"):
                 try:
                     git.delete_branch(name, force=True)
                     success(f"Deleted branch '{name}'")
                     return
                 except Exception as e2:
                     error(f"Failed to force delete: {e2}")
            else:
                 console.print("Aborted.")
                 return

        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to delete branch: {e}")


# ============================================================================
# remote Commands
# ============================================================================


@main.group()
def remote():
    """Manage remote repository connection."""
    pass


@remote.command("set")
@click.argument("url")
@require_init
def remote_set(url: str):
    """Set the remote repository URL.
    
    Example: dot-man remote set https://github.com/user/dotfiles.git
    """
    try:
        git = GitManager()
        git.set_remote(url)
        success(f"Remote set to: {url}")
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to set remote: {e}")


@remote.command("get")
@require_init
def remote_get():
    """Show the current remote repository URL."""
    try:
        git = GitManager()
        url = git.get_remote_url()
        if url:
            console.print(f"Remote URL: [cyan]{url}[/cyan]")
        else:
            console.print("[dim]No remote configured[/dim]")
            console.print("Use: [cyan]dot-man remote set <url>[/cyan]")
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to get remote: {e}")


# ============================================================================
# sync Command
# ============================================================================


@main.command()
@click.option("--push-only", is_flag=True, help="Only push, don't pull")
@click.option("--pull-only", is_flag=True, help="Only pull, don't push")
@require_init
def sync(push_only: bool, pull_only: bool):
    """Sync with remote repository.
    
    Pulls changes from remote (with rebase), then pushes local changes.
    Use this to keep dotfiles in sync across multiple machines.
    
    Example: dot-man sync
    """
    try:
        git = GitManager()
        
        if not git.has_remote():
            error("No remote configured. Use 'dot-man remote set <url>' first.")
        
        current = git.current_branch()
        console.print(f"Syncing branch [bold]{current}[/bold] with remote...")
        console.print()
        
        # Pull first (unless push-only)
        if not push_only:
            console.print("[bold]Fetching...[/bold]")
            git.fetch()
            
            console.print("[bold]Pulling...[/bold]")
            pull_result = git.pull(rebase=True)
            console.print(f"  {pull_result}")
            console.print()
        
        # Push (unless pull-only)
        if not pull_only:
            console.print("[bold]Pushing...[/bold]")
            push_result = git.push()
            console.print(f"  {push_result}")
            console.print()
        
        success("Sync complete!")
        
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Sync failed: {e}")


# ============================================================================
# tui Command
# ============================================================================


@main.command()
@require_init
def tui():
    """Interactive TUI for managing dotfiles.
    
    Navigate with arrow keys, press Enter to switch branches.
    
    Keys:
        Enter - Switch to selected branch
        s     - Sync with remote
        d     - Deploy selected branch
        r     - Refresh
        q     - Quit
    
    Requires: pip install dot-man[tui]
    """
    try:
        from .tui import run_tui
    except ImportError:
        console.print("[yellow]TUI requires the 'textual' package.[/yellow]")
        console.print()
        console.print("Install with:")
        console.print("  [cyan]pipx inject dot-man textual[/cyan]")
        console.print("  or")
        console.print("  [cyan]pip install dot-man[tui][/cyan]")
        return
    
    try:
        result = run_tui()
        
        if result:
            action, branch = result
            
            if action == "switch" and branch:
                ctx = click.Context(switch)
                ctx.invoke(switch, branch=branch, dry_run=False, force=True)
                
            elif action == "sync":
                ctx = click.Context(sync)
                ctx.invoke(sync, push_only=False, pull_only=False)
                
            elif action == "deploy" and branch:
                ctx = click.Context(deploy)
                ctx.invoke(deploy, branch=branch, force=True, dry_run=False)
                
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"TUI error: {e}")


# ============================================================================
# setup Command
# ============================================================================


@main.command()
@require_init
def setup():
    """Set up remote repository for syncing.
    
    Guides you through creating a GitHub repository and connecting it.
    Supports GitHub CLI (gh) for automatic creation.
    """
    import shutil
    
    git = GitManager()
    
    # Check if remote already configured
    if git.has_remote():
        url = git.get_remote_url()
        console.print(f"Remote already configured: [cyan]{url}[/cyan]")
        if not confirm("Replace with a new remote?"):
            return
    
    console.print()
    console.print("[bold]🔧 Remote Setup[/bold]")
    console.print()
    
    # Check for GitHub CLI
    gh_available = shutil.which("gh") is not None
    
    if gh_available:
        console.print("[green]✓[/green] GitHub CLI (gh) detected")
        console.print()
        
        if confirm("Create a new private GitHub repository?"):
            repo_name = click.prompt("Repository name", default="dotfiles")
            
            try:
                # Create repo with gh
                result = subprocess.run(
                    ["gh", "repo", "create", repo_name, "--private", "--source=.", "--remote=origin", "--push"],
                    cwd=REPO_DIR,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    success(f"Created and connected to GitHub repository: {repo_name}")
                    console.print()
                    console.print("You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!")
                    return
                else:
                    warn(f"gh command failed: {result.stderr}")
                    console.print("Falling back to manual setup...")
                    console.print()
            except Exception as e:
                warn(f"Error running gh: {e}")
                console.print("Falling back to manual setup...")
                console.print()
    else:
        console.print("[dim]GitHub CLI not found. Install with: https://cli.github.com[/dim]")
        console.print()
    
    # Manual setup instructions
    console.print("[bold]Manual Setup Steps:[/bold]")
    console.print()
    console.print("1. Create a new repository on GitHub:")
    console.print("   [cyan]https://github.com/new[/cyan]")
    console.print()
    console.print("2. Copy the repository URL (SSH or HTTPS)")
    console.print()
    
    url = click.prompt("Enter the repository URL (or 'skip' to exit)", default="skip")
    
    if url.lower() == "skip":
        console.print()
        console.print("You can set the remote later with:")
        console.print("  [cyan]dot-man remote set <url>[/cyan]")
        return
    
    try:
        git.set_remote(url)
        success(f"Remote set to: {url}")
        
        if confirm("Push current dotfiles to remote?"):
            console.print("Pushing...")
            git.push()
            success("Pushed to remote!")
            console.print()
            console.print("You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!")
    except Exception as e:
        error(f"Failed to set remote: {e}")


# ============================================================================
# repo Command
# ============================================================================


@main.command()
@require_init
def repo():
    """Show the repository path for direct git access.
    
    Use this to run git commands directly in the dot-man repository.
    
    Example:
        cd $(dot-man repo)
        git remote add origin <url>
    """
    console.print(str(REPO_DIR))


@main.command()
@require_init  
def shell():
    """Open a shell in the repository directory.
    
    Useful for running git commands directly.
    """
    import os
    
    console.print(f"Opening shell in [cyan]{REPO_DIR}[/cyan]")
    console.print("[dim]Type 'exit' to return[/dim]")
    console.print()
    
    # Get user's shell
    user_shell = os.environ.get("SHELL", "/bin/bash")
    
    # Change to repo dir and exec shell
    os.chdir(REPO_DIR)
    os.execlp(user_shell, user_shell)


# ============================================================================
# Entry Point
# ============================================================================


if __name__ == "__main__":
    main()
