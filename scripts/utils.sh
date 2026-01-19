#!/usr/bin/env bash
#
# dot-man installer utilities
# Common functions and variables used by install scripts
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${CYAN}→${NC} $1"; }

# Default install locations
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/bin}"
COMPLETIONS_BASH="${COMPLETIONS_BASH:-$HOME/.local/share/bash-completion/completions}"
COMPLETIONS_ZSH="${COMPLETIONS_ZSH:-$HOME/.local/share/zsh/site-functions}"
COMPLETIONS_FISH="${COMPLETIONS_FISH:-$HOME/.config/fish/completions}"

# Check prerequisites
check_prerequisites() {
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        return 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Found Python $PYTHON_VERSION"

    # Check for pip
    if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
        print_error "pip is required but not installed."
        return 1
    fi

    # Check for git
    if ! command -v git &> /dev/null; then
        print_error "Git is required but not installed."
        return 1
    fi

    print_status "Prerequisites check passed"
    return 0
}

# Install package using pipx or pip
install_package() {
    local script_dir="$1"
    
    print_info "Installing dot-man package..."
    
    cd "$script_dir"
    
    # Check if pipx is available (recommended for Arch/modern distros)
    if command -v pipx &> /dev/null; then
        echo -e "  Using ${CYAN}pipx${NC} for installation..."
        
        # Uninstall first if exists (to handle reinstalls)
        pipx uninstall dot-man 2>/dev/null || true
        
        # Install with pipx
        if pipx install . --force > /dev/null 2>&1; then
            print_status "Package installed successfully with pipx"
            return 0
        else
            print_error "Failed to install package with pipx"
            return 1
        fi
    else
        # Fallback: try pip with --user
        echo -e "  ${YELLOW}pipx not found, trying pip...${NC}"
        
        if pip3 install --user . --quiet 2>/dev/null; then
            print_status "Package installed successfully with pip"
            return 0
        elif pip3 install --user . --break-system-packages --quiet 2>/dev/null; then
            print_warning "Package installed with pip (--break-system-packages)"
            echo -e "  ${YELLOW}Tip: Install pipx with 'sudo pacman -S python-pipx' for better isolation${NC}"
            return 0
        else
            print_error "Failed to install package"
            echo -e "  ${YELLOW}Tip: Install pipx with 'sudo pacman -S python-pipx' and try again${NC}"
            return 1
        fi
    fi
}
