#!/usr/bin/env bash
#
# dot-man uninstaller
# Removes dot-man CLI and shell completions
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_info() { echo -e "${CYAN}→${NC} $1"; }

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
COMPLETIONS_BASH="${COMPLETIONS_BASH:-$HOME/.local/share/bash-completion/completions}"
COMPLETIONS_ZSH="${COMPLETIONS_ZSH:-$HOME/.local/share/zsh/site-functions}"
COMPLETIONS_FISH="${COMPLETIONS_FISH:-$HOME/.config/fish/completions}"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      dot-man Uninstaller v0.1.0      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Uninstall package
print_info "Uninstalling dot-man package..."

# Try pipx first
if command -v pipx &> /dev/null; then
    if pipx uninstall dot-man 2>/dev/null; then
        print_status "Package uninstalled with pipx"
    fi
fi

# Also try pip (in case installed both ways)
pip3 uninstall -y dot-man 2>/dev/null || true
print_status "Package uninstalled"

# Remove completions
print_info "Removing shell completions..."

if [ -f "$COMPLETIONS_BASH/dot-man" ]; then
    rm -f "$COMPLETIONS_BASH/dot-man"
    print_status "Removed bash completion"
fi

if [ -f "$COMPLETIONS_ZSH/_dot-man" ]; then
    rm -f "$COMPLETIONS_ZSH/_dot-man"
    print_status "Removed zsh completion"
fi

if [ -f "$COMPLETIONS_FISH/dot-man.fish" ]; then
    rm -f "$COMPLETIONS_FISH/dot-man.fish"
    print_status "Removed fish completion"
fi

echo ""
print_status "dot-man has been uninstalled"
echo ""

# Ask about data
echo -e "${YELLOW}Note:${NC} Your configuration at ~/.config/dot-man/ was NOT removed."
echo "      To remove all data: rm -rf ~/.config/dot-man/"
echo ""
