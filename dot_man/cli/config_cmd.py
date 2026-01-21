"""Config command for dot-man CLI."""

import json

import click
from rich.table import Table

from .. import ui
from ..config import GlobalConfig
from ..exceptions import ConfigurationError
from .interface import cli as main
from .common import error, success, require_init


@main.group()
def config():
    """Manage global configuration."""
    pass


@config.command("list")
def config_list():
    """List all global configuration values."""
    try:
        cfg = GlobalConfig()
        cfg.load()

        def flatten(d, parent_key="", sep="."):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        flat_data = flatten(cfg._data)

        table = Table(title="Global Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for k, v in sorted(flat_data.items()):
            table.add_row(k, str(v))

        ui.console.print(table)

    except Exception as e:
        error(f"Failed to list config: {e}")


@config.command("get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value.

    Example: dot-man config get dot-man.editor
    """
    try:
        cfg = GlobalConfig()
        cfg.load()

        parts = key.split(".")
        current = cfg._data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                error(f"Key not found: {key}")

        if isinstance(current, dict):
            ui.console.print(f"[dim]Section '{key}' contains:[/dim]")
            ui.console.print(json.dumps(current, indent=2))
        else:
            ui.console.print(str(current))

    except Exception as e:
        error(f"Failed to get config: {e}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Example: dot-man config set dot-man.editor nvim
    """
    try:
        cfg = GlobalConfig()
        try:
            cfg.load()
        except (FileNotFoundError, ConfigurationError):
            cfg.create_default()

        # Handle boolean values
        if value.lower() == "true":
            val = True
        elif value.lower() == "false":
            val = False
        else:
            val = value

        parts = key.split(".")
        current = cfg._data

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
            if not isinstance(current, dict):
                error(f"Key path conflict: '{'.'.join(parts[: i + 1])}' is not a section")

        current[parts[-1]] = val
        cfg.save()

        success(f"Set '{key}' to '{val}'")

    except Exception as e:
        error(f"Failed to set config: {e}")


@config.command("create")
@click.option(
    "--examples",
    "with_examples",
    is_flag=True,
    default=True,
    help="Include commented examples in the config file (default: True)",
)
@click.option(
    "--minimal",
    is_flag=True,
    help="Create a minimal config file without examples or comments",
)
@click.option(
    "--force", is_flag=True, help="Overwrite existing config file without prompting"
)
@require_init
def config_create(with_examples: bool, minimal: bool, force: bool):
    """Create or regenerate the dot-man.toml configuration file.

    This command creates a new dot-man.toml file for the current branch.
    By default, it includes commented examples to help you get started.

    Examples:
        # Create config with examples (default)
        dot-man config create

        # Create minimal config without examples
        dot-man config create --minimal

        # Create config with examples, overwrite existing
        dot-man config create --examples --force

        # Create minimal config, overwrite existing
        dot-man config create --minimal --force
    """
    try:
        from ..constants import DOT_MAN_TOML, REPO_DIR
        from ..config import DotManConfig

        config_path = REPO_DIR / DOT_MAN_TOML

        # Check if file exists
        if config_path.exists() and not force:
            if not ui.confirm(f"Config file already exists at {config_path}. Overwrite?"):
                ui.console.print("Cancelled.")
                return

        # Create the config
        dotman_config = DotManConfig()

        if minimal:
            # Create minimal config without examples
            dotman_config._data = {}
            dotman_config.save()
            ui.console.print(f"Created minimal config at {config_path}")
        else:
            # Create config with examples (default behavior)
            dotman_config.create_default()
            ui.console.print(f"Created config with examples at {config_path}")

        ui.console.print("Tip: Use 'dot-man edit' to open the config in your editor")

    except Exception as e:
        error(f"Failed to create config: {e}")


@config.command("tutorial")
@click.option("--section", help="Show examples for a specific section type")
@click.option("--interactive", "-i", is_flag=True, help="Interactive tutorial mode")
def config_tutorial(section: str | None, interactive: bool):
    """Interactive configuration tutorial with examples.

    Learn how to configure dot-man with practical examples and explanations.
    Similar to vimtutor, this guides you through configuration options.

    Examples:
        # Show all examples
        dot-man config tutorial

        # Show examples for a specific type
        dot-man config tutorial --section basic
        dot-man config tutorial --section advanced
        dot-man config tutorial --section hooks

        # Interactive mode (step by step)
        dot-man config tutorial --interactive
    """
    from rich.panel import Panel
    from rich.prompt import Prompt

    if interactive:
        _run_interactive_tutorial()
        return

    if section:
        _show_section_examples(section)
        return

    # Show interactive overview with all sections
    ui.console.print()
    ui.console.print(
        Panel.fit(
            "[bold blue]dot-man Configuration Tutorial[/bold blue]\n\n"
            "This tutorial shows you how to configure dot-man to track your dotfiles.\n"
            "Choose from the options below or use --interactive for guided learning.",
            title="🎯 Tutorial Overview",
        )
    )

    ui.console.print("\n[bold]What would you like to learn about?[/bold]")
    ui.console.print()

    # Interactive menu options
    menu_options = [
        ("1", "Basic file tracking", "paths, sections, simple examples"),
        ("2", "Directory tracking", "include/exclude patterns, wildcards"),
        ("3", "Update strategies", "replace, rename_old, ignore strategies"),
        ("4", "Hooks & automation", "pre/post deploy commands, aliases"),
        ("5", "Templates & inheritance", "reusable configs, organization"),
        ("6", "Advanced features", "custom paths, overrides, limits"),
        ("7", "Security & secrets", "automatic filtering, best practices"),
        ("I", "Interactive tutorial", "step-by-step guided learning"),
        ("C", "Create config", "generate config file with examples"),
        ("Q", "Quit", "exit tutorial"),
    ]

    for key, title, desc in menu_options:
        if key in ["I", "C", "Q"]:
            ui.console.print(f"  [yellow]{key}[/yellow] - [bold]{title}[/bold] - {desc}")
        else:
            ui.console.print(f"  [cyan]{key}[/cyan] - [bold]{title}[/bold] - {desc}")

    ui.console.print()

    # Get user choice
    choice = Prompt.ask(
        "Enter your choice",
        choices=["1", "2", "3", "4", "5", "6", "7", "I", "C", "Q"],
        default="I",
    ).upper()

    # Handle choice
    if choice == "1":
        _show_section_examples("basic")
    elif choice == "2":
        _show_section_examples("directories")
    elif choice == "3":
        _show_section_examples("hooks")  # Update strategies are in hooks section
    elif choice == "4":
        _show_section_examples("hooks")
    elif choice == "5":
        _show_section_examples("templates")
    elif choice == "6":
        _show_section_examples("advanced")
    elif choice == "7":
        _show_section_examples("secrets")
    elif choice == "I":
        _run_interactive_tutorial()
    elif choice == "C":
        ui.console.print(
            "\n[dim]Tip: Run 'dot-man config create' to generate a config file with examples[/dim]"
        )
    elif choice == "Q":
        ui.console.print(
            "\n[dim]Goodbye! Run 'dot-man config tutorial' anytime to return.[/dim]"
        )

    return


def _show_section_examples(section: str):
    """Show examples for a specific section."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    examples = {
        "basic": {
            "title": "Basic File Tracking",
            "description": "Track individual files with smart defaults",
            "examples": [
                {
                    "title": "Simple file tracking",
                    "config": """[bashrc]
paths = ["~/.bashrc"]""",
                    "explanation": "Tracks your bash configuration. dot-man automatically:\n"
                    "• Generates repo_base as 'bashrc'\n"
                    "• Uses 'replace' update_strategy\n"
                    "• Enables secrets_filter",
                },
                {
                    "title": "Multiple files in one section",
                    "config": """[shell-files]
paths = ["~/.bashrc", "~/.zshrc", "~/.profile"]""",
                    "explanation": "Group related files together. All files share the same settings.",
                },
                {
                    "title": "Custom repository name",
                    "config": """[my-config]
paths = ["~/.myapp/config"]
repo_base = "my-app-config" """,
                    "explanation": "Override the auto-generated repo_base with a custom name.",
                },
            ],
        },
        "directories": {
            "title": "Directory Tracking",
            "description": "Track entire directories with include/exclude patterns",
            "examples": [
                {
                    "title": "Basic directory tracking",
                    "config": """[nvim]
paths = ["~/.config/nvim"]""",
                    "explanation": "Tracks your entire Neovim config directory.",
                },
                {
                    "title": "Directory with exclusions",
                    "config": """[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]""",
                    "explanation": "Exclude temporary files and compiled plugins from tracking.",
                },
                {
                    "title": "Include only specific files",
                    "config": """[dotfiles]
paths = ["~/dotfiles"]
include = ["*.conf", "*.sh", "README.md"]""",
                    "explanation": "Only track configuration files, scripts, and documentation.",
                },
            ],
        },
        "hooks": {
            "title": "Pre/Post Deploy Hooks",
            "description": "Run commands before or after file deployment",
            "examples": [
                {
                    "title": "Shell reload after config change",
                    "config": """[bashrc]
paths = ["~/.bashrc"]
post_deploy = "shell_reload" """,
                    "explanation": "Reloads your shell after deploying bash config.\n"
                    "'shell_reload' is an alias for: source ~/.bashrc || source ~/.zshrc",
                },
                {
                    "title": "Neovim plugin sync",
                    "config": """[nvim]
paths = ["~/.config/nvim"]
post_deploy = "nvim_sync" """,
                    "explanation": "Runs PackerSync after deploying Neovim config.\n"
                    "'nvim_sync' is an alias for: nvim --headless +PackerSync +qa",
                },
                {
                    "title": "Custom command",
                    "config": """[custom-app]
paths = ["~/.config/myapp"]
post_deploy = "systemctl --user restart myapp" """,
                    "explanation": "Restart a user service after config deployment.",
                },
                {
                    "title": "Pre-deploy backup",
                    "config": """[important-config]
paths = ["~/.important"]
pre_deploy = "cp ~/.important ~/.important.backup" """,
                    "explanation": "Create a backup before overwriting important files.",
                },
            ],
        },
        "templates": {
            "title": "Reusable Templates",
            "description": "Define shared settings that can be inherited",
            "examples": [
                {
                    "title": "Template definition",
                    "config": """[templates.linux-desktop]
post_deploy = "notify-send 'Config updated'"
update_strategy = "rename_old"

[templates.dev-tools]
secrets_filter = false
pre_deploy = "echo 'Deploying dev config'" """,
                    "explanation": "Define reusable templates with common settings.",
                },
                {
                    "title": "Template inheritance",
                    "config": """[hyprland]
paths = ["~/.config/hypr"]
inherits = ["linux-desktop"]

[git]
paths = ["~/.gitconfig"]
inherits = ["dev-tools"]""",
                    "explanation": "Inherit settings from templates. Child settings override parent settings.",
                },
            ],
        },
        "advanced": {
            "title": "Advanced Options",
            "description": "Fine-tune behavior with advanced configuration options",
            "examples": [
                {
                    "title": "Update strategies",
                    "config": """[careful-config]
paths = ["~/.important"]
update_strategy = "rename_old"

[aggressive-config]
paths = ["~/.cache/myapp"]
update_strategy = "replace"

[readonly-config]
paths = ["~/.readonly"]
update_strategy = "ignore" """,
                    "explanation": "• 'replace': Overwrite existing files (default)\n"
                    "• 'rename_old': Backup existing files\n"
                    "• 'ignore': Skip if file exists",
                },
                {
                    "title": "Explicit repository paths",
                    "config": """[special-file]
paths = ["~/.config/app/special.conf"]
repo_path = "configs/special-config.toml" """,
                    "explanation": "Override automatic repo path generation with explicit repo_path.",
                },
            ],
        },
        "secrets": {
            "title": "Secret Detection & Filtering",
            "description": "Automatically detect and handle sensitive information",
            "examples": [
                {
                    "title": "Automatic secret filtering",
                    "config": """[gitconfig]
paths = ["~/.gitconfig"]
# secrets_filter = true  (enabled by default)""",
                    "explanation": "Automatically redacts API keys, passwords, and tokens when saving.",
                },
                {
                    "title": "Disable filtering for trusted files",
                    "config": """[trusted-config]
paths = ["~/.config/trusted"]
secrets_filter = false""",
                    "explanation": "Disable secret filtering for files you know are safe.",
                },
                {
                    "title": "Check for secrets",
                    "command": "dot-man audit",
                    "explanation": "Scan your repository for secrets. Use --strict for CI/CD.",
                },
            ],
        },
    }

    if section not in examples:
        ui.error(f"Unknown section: {section}", exit_code=0)
        ui.console.print(f"Available sections: {', '.join(examples.keys())}")
        return

    data = examples[section]

    ui.console.print()
    ui.console.print(
        Panel.fit(
            f"[bold blue]{data['title']}[/bold blue]\n\n{data['description']}",
            title=f"📖 {data['title']}",
        )
    )

    for i, example in enumerate(data["examples"], 1):
        ui.console.print(f"\n[bold cyan]Example {i}: {example['title']}[/bold cyan]")

        if "config" in example:
            ui.console.print(
                Syntax(example["config"], "toml", theme="monokai", line_numbers=False)
            )
        elif "command" in example:
            ui.console.print(f"[green]$ {example['command']}[/green]")

        ui.console.print(f"\n[dim]{example['explanation']}[/dim]")

    ui.console.print(
        f"\n[dim]💡 Run 'dot-man config create' to add these examples to your config file[/dim]"
    )


def _run_interactive_tutorial():
    """Run interactive step-by-step tutorial with detailed explanations."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    ui.console.print()
    ui.console.print(
        Panel.fit(
            "[bold green]🎓 Interactive dot-man Configuration Tutorial[/bold green]\n\n"
            "This interactive tutorial will guide you through configuring dot-man.\n"
            "You'll learn what each configuration option does as we build examples.",
            title="Welcome!",
        )
    )

    # Track user configurations for final summary
    user_configs = []

    # Step 1: Basic files
    ui.console.print("\n[bold cyan]📁 Step 1: Basic File Tracking[/bold cyan]")
    ui.console.print(
        "Every configuration section starts with [section-name] and defines what files to track."
    )

    ui.console.print("\n[bold green]✅ Example: Shell Configuration[/bold green]")
    ui.console.print()

    # Show the config with explanations
    config_text = """[shell-config]
paths = ["~/.bashrc", "~/.zshrc"]
post_deploy = "shell_reload" """

    ui.console.print(Syntax(config_text, "toml", theme="monokai"))
    ui.console.print()

    # Explain each part
    ui.console.print(
        "[bold cyan]🔍 [shell-config][/bold cyan] - A unique name for this group of files"
    )
    ui.console.print(
        "[bold cyan]📂 paths[/bold cyan] - List of files/directories to track (supports ~ expansion)"
    )
    ui.console.print(
        "[bold cyan]🚀 post_deploy[/bold cyan] - Command to run AFTER files are deployed"
    )
    ui.console.print(
        "[bold cyan]🔄 shell_reload[/bold cyan] - Built-in alias that reloads bash/zsh"
    )
    ui.console.print("    [dim](runs: source ~/.bashrc || source ~/.zshrc)[/dim]")

    ui.console.print(
        "\n[dim]💡 Smart defaults apply automatically - you only specify what's different![/dim]"
    )

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    ui.console.print(
        "\n[bold green]✅ Git Config with Automatic Secret Protection:[/bold green]"
    )
    ui.console.print()

    config_text = """[gitconfig]
paths = ["~/.gitconfig"]"""

    ui.console.print(Syntax(config_text, "toml", theme="monokai"))
    ui.console.print()

    ui.console.print(
        "[bold cyan]🔒 Automatic security[/bold cyan] - Git configs get special protection:"
    )
    ui.console.print(
        "  • [yellow]secrets_filter = true[/yellow] - Detects and redacts sensitive data"
    )
    ui.console.print(
        "  • [yellow]API keys, passwords, tokens[/yellow] - Automatically removed when saving"
    )
    ui.console.print(
        '  • [yellow]update_strategy = "replace"[/yellow] - Safe for most config files'
    )

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 2: Directories with patterns
    ui.console.print(
        "\n[bold cyan]📂 Step 2: Directory Tracking with Patterns[/bold cyan]"
    )
    ui.console.print("When tracking directories, you can include/exclude specific files.")

    ui.console.print("\n[bold green]✅ Neovim Config with Smart Exclusions:[/bold green]")
    ui.console.print()

    config_text = """[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]
post_deploy = "nvim_sync" """

    ui.console.print(Syntax(config_text, "toml", theme="monokai"))
    ui.console.print()

    ui.console.print(
        "[bold cyan]🎯 exclude[/bold cyan] - Patterns of files/directories to SKIP tracking"
    )
    ui.console.print("  • [yellow]*.log[/yellow] - Any .log files")
    ui.console.print(
        "  • [yellow]plugin/packer_compiled.lua[/yellow] - Compiled plugin cache"
    )
    ui.console.print(
        "[bold cyan]📝 Pattern syntax[/bold cyan] - Wildcards (*, **, ?) and gitignore-style"
    )
    ui.console.print(
        "[bold cyan]🔄 nvim_sync[/bold cyan] - Alias: nvim --headless +PackerSync +qa"
    )

    ui.console.print(
        '\n[dim]💡 Use ** for recursive: "**/*.tmp" matches all .tmp files in subdirs[/dim]'
    )

    user_configs.append(
        (
            "nvim",
            """[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]
post_deploy = "nvim_sync" """,
        )
    )

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 3: Update strategies
    ui.console.print(
        "\n[bold cyan]🔄 Step 3: Update Strategies - How Files Are Deployed[/bold cyan]"
    )
    ui.console.print("Choose how dot-man handles existing files when deploying.")

    # Show update strategy information

    ui.console.print("\n[bold green]📋 Update Strategy Options:[/bold green]")

    strategy_examples = {
        "Safe (rename_old)": {
            "config": 'update_strategy = "rename_old"',
            "explanation": "• Backs up existing file as filename.bak\n• Then overwrites with new version\n• Your original file is safe if something goes wrong",
        },
        "Direct (replace)": {
            "config": 'update_strategy = "replace"  # Default',
            "explanation": "• Directly overwrites existing files\n• No backup created\n• Fastest option",
        },
        "Conservative (ignore)": {
            "config": 'update_strategy = "ignore"',
            "explanation": "• Skips files that already exist\n• Never overwrites your changes\n• Good for one-time setup files",
        },
    }

    for name, details in strategy_examples.items():
        ui.console.print(f"\n[yellow]{name}:[/yellow]")
        ui.console.print(Syntax(details["config"], "toml", theme="monokai"))
        ui.console.print(details["explanation"])

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 4: Pre-deploy hooks
    ui.console.print(
        "\n[bold cyan]⚡ Step 4: Pre-Deploy Hooks - Actions Before Deployment[/bold cyan]"
    )
    ui.console.print("Sometimes you need to prepare before deploying files.")

    ui.console.print("\n[bold green]🔧 Pre-deploy Hook Examples:[/bold green]")
    ui.console.print()

    examples = [
        {
            "title": "Backup important files",
            "config": """[important-config]
paths = ["~/.important/app.conf"]
pre_deploy = "cp ~/.important/app.conf ~/.important/app.conf.backup" """,
            "explanation": "Creates a backup before dot-man touches the file",
        },
        {
            "title": "Stop services before config change",
            "config": """[service-config]
paths = ["~/.config/my-service"]
pre_deploy = "systemctl --user stop my-service" """,
            "explanation": "Stops the service before updating its config files",
        },
    ]

    for example in examples:
        ui.console.print(f"[cyan]{example['title']}:[/cyan]")
        ui.console.print(Syntax(example["config"], "toml", theme="monokai"))
        ui.console.print(f"  {example['explanation']}")
        ui.console.print()

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 5: Templates
    ui.console.print(
        "\n[bold cyan]📋 Step 5: Templates - Reusable Configuration[/bold cyan]"
    )
    ui.console.print("Define shared settings that multiple sections can inherit.")

    ui.console.print("\n[bold green]🎨 Template Example:[/bold green]")
    ui.console.print()

    config_text = """# Define a template
[templates.desktop-apps]
post_deploy = "notify-send 'Config updated'"
update_strategy = "rename_old"

# Use the template
[hyprland]
paths = ["~/.config/hypr"]
inherits = ["desktop-apps"]

[waybar]
paths = ["~/.config/waybar"]
inherits = ["desktop-apps"]
# Override settings if needed
update_strategy = "replace" """

    ui.console.print(Syntax(config_text, "toml", theme="monokai"))
    ui.console.print()

    ui.console.print(
        "[bold cyan]📋 Template definition[/bold cyan] - [templates.name] sections are reusable"
    )
    ui.console.print(
        "[bold cyan]🔗 inherits[/bold cyan] - List of templates to inherit settings from"
    )
    ui.console.print(
        "[bold cyan]⚡ Override behavior[/bold cyan] - Section settings override templates"
    )
    ui.console.print(
        "[bold cyan]🎯 Use case[/bold cyan] - Share notifications, strategies, etc."
    )

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 6: Terminal
    ui.console.print("\n[bold cyan]💻 Step 6: Terminal Configuration[/bold cyan]")

    ui.console.print("\n[bold green]✅ Kitty Terminal Configuration:[/bold green]")
    ui.console.print()

    config_text = """[kitty]
paths = ["~/.config/kitty"]
post_deploy = "kitty_reload" """

    ui.console.print(Syntax(config_text, "toml", theme="monokai"))
    ui.console.print()

    ui.console.print(
        "[bold cyan]🖥️ Kitty[/bold cyan] - Fast, GPU-accelerated terminal emulator"
    )
    ui.console.print("[bold cyan]📂 paths[/bold cyan] - Kitty configuration directory")
    ui.console.print("[bold cyan]🚀 post_deploy[/bold cyan] - Reload command for Kitty")
    ui.console.print(
        "[bold cyan]🔄 kitty_reload[/bold cyan] - Sends SIGUSR1 to reload running instances"
    )

    user_configs.append(
        (
            "kitty",
            """[kitty]
paths = ["~/.config/kitty"]
post_deploy = "kitty_reload" """,
        )
    )

    ui.console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Final summary
    ui.console.print("\n[bold green]🎉 Tutorial Complete![/bold green]")
    ui.console.print("\n[dim]You've learned about:[/dim]")
    ui.console.print("  • 📁 Basic file and directory tracking")
    ui.console.print("  • 🎯 Include/exclude patterns for selective tracking")
    ui.console.print("  • 🔄 Update strategies (replace, rename_old, ignore)")
    ui.console.print("  • ⚡ Pre/post deploy hooks for automation")
    ui.console.print("  • 📋 Templates for reusable configuration")
    ui.console.print("  • 🔒 Automatic secret detection and filtering")

    ui.console.print("\n[dim]Next steps:[/dim]")
    ui.console.print(
        "[green]$ dot-man config create[/green] [dim]- Generate config file with examples[/dim]"
    )
    ui.console.print(
        "[green]$ dot-man edit[/green] [dim]- Customize your configuration[/dim]"
    )
    ui.console.print(
        "[green]$ dot-man config tutorial --section advanced[/green] [dim]- Learn advanced features[/dim]"
    )
