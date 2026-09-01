#!/usr/bin/env bash
#
# dot-man installer
# Installs dot-man CLI and shell completions
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source utilities and helper scripts
source "$SCRIPT_DIR/scripts/utils.sh"
source "$SCRIPT_DIR/scripts/path-setup.sh"

# Get version from pyproject.toml
VERSION=$(grep -m1 '^version = ' "$SCRIPT_DIR/pyproject.toml" | cut -d '"' -f 2)

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       dot-man Installer v${VERSION}       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check prerequisites
if ! check_prerequisites; then
    exit 1
fi

echo ""

# Install package
if ! install_package "$SCRIPT_DIR"; then
    exit 1
fi

echo ""

# Install completions via the CLI (uses the packaged scripts)
if command -v dot-man > /dev/null 2>&1; then
    if dot-man completions --shell all; then
        print_status "Shell completions installed"
    else
        print_info "Completions install skipped. Run 'dot-man completions' later."
    fi
else
    print_info "dot-man not on PATH yet — run 'dot-man completions' after installing."
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       Installation Complete!         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Setup PATH if needed
setup_path

print_info "To enable completions, restart your shell or run:"
echo ""
echo "  # Bash:"
echo "  source $COMPLETIONS_BASH/dot-man"
echo ""
echo "  # Zsh:"
echo "  autoload -Uz compinit && compinit"
echo ""
echo "  # Fish (automatic)"
echo ""
print_status "Run 'dot-man --help' to get started!"
echo ""
