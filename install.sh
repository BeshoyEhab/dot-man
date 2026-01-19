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
source "$SCRIPT_DIR/scripts/completions/install.sh"
source "$SCRIPT_DIR/scripts/path-setup.sh"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       dot-man Installer v0.4.0       ║"
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

# Install completions
install_completions

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
