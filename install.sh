#!/usr/bin/env bash
#
# dot-man installer
# Installs dot-man CLI and shell completions
#

set -e

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
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
COMPLETIONS_BASH="${COMPLETIONS_BASH:-$HOME/.local/share/bash-completion/completions}"
COMPLETIONS_ZSH="${COMPLETIONS_ZSH:-$HOME/.local/share/zsh/site-functions}"
COMPLETIONS_FISH="${COMPLETIONS_FISH:-$HOME/.config/fish/completions}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       dot-man Installer v0.1.0       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_status "Found Python $PYTHON_VERSION"

# Check for pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    print_error "pip is required but not installed."
    exit 1
fi

# Check for git
if ! command -v git &> /dev/null; then
    print_error "Git is required but not installed."
    exit 1
fi

print_status "Prerequisites check passed"
echo ""

# Install with pipx (preferred) or pip fallback
print_info "Installing dot-man package..."

cd "$SCRIPT_DIR"

# Check if pipx is available (recommended for Arch/modern distros)
if command -v pipx &> /dev/null; then
    echo -e "  Using ${CYAN}pipx${NC} for installation..."
    
    # Uninstall first if exists (to handle reinstalls)
    pipx uninstall dot-man 2>/dev/null || true
    
    # Install with pipx
    if pipx install . --force > /dev/null 2>&1; then
        print_status "Package installed successfully with pipx"
    else
        print_error "Failed to install package with pipx"
        exit 1
    fi
else
    # Fallback: try pip with --user
    echo -e "  ${YELLOW}pipx not found, trying pip...${NC}"
    
    if pip3 install --user . --quiet 2>/dev/null; then
        print_status "Package installed successfully with pip"
    elif pip3 install --user . --break-system-packages --quiet 2>/dev/null; then
        print_warning "Package installed with pip (--break-system-packages)"
        echo -e "  ${YELLOW}Tip: Install pipx with 'sudo pacman -S python-pipx' for better isolation${NC}"
    else
        print_error "Failed to install package"
        echo -e "  ${YELLOW}Tip: Install pipx with 'sudo pacman -S python-pipx' and try again${NC}"
        exit 1
    fi
fi

echo ""
print_info "Setting up shell completions..."

# ============================================================================
# Generate completions using Click's built-in support
# ============================================================================

# Bash completion
mkdir -p "$COMPLETIONS_BASH"
cat > "$COMPLETIONS_BASH/dot-man" << 'EOF'
# dot-man bash completion
_dot_man_completion() {
    local IFS=$'\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _DOT_MAN_COMPLETE=bash_complete dot-man 2>/dev/null)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"
        COMPREPLY+=("$value")
    done
    return 0
}

complete -o default -F _dot_man_completion dot-man
EOF
print_status "Bash completion installed: $COMPLETIONS_BASH/dot-man"

# Zsh completion
mkdir -p "$COMPLETIONS_ZSH"
cat > "$COMPLETIONS_ZSH/_dot-man" << 'EOF'
#compdef dot-man

_dot_man_completion() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[dot-man] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) _DOT_MAN_COMPLETE=zsh_complete dot-man 2>/dev/null)}")

    for key descr in ${(kv)response}; do
        if [[ "$descr" == "_" ]]; then
            completions+=("$key")
        else
            completions_with_descriptions+=("$key":"$descr")
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

compdef _dot_man_completion dot-man
EOF
print_status "Zsh completion installed: $COMPLETIONS_ZSH/_dot-man"

# Fish completion
mkdir -p "$COMPLETIONS_FISH"
cat > "$COMPLETIONS_FISH/dot-man.fish" << 'EOF'
# dot-man fish completion

function __fish_dot_man_complete
    set -l response (env _DOT_MAN_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) dot-man 2>/dev/null)
    for completion in $response
        set -l metadata (string split "," -- $completion)
        if test (count $metadata) -eq 1
            echo $metadata[1]
        else
            echo -e "$metadata[1]\t$metadata[2]"
        end
    end
end

complete -c dot-man -f -a "(__fish_dot_man_complete)"

# Subcommand completions
complete -c dot-man -n "__fish_use_subcommand" -a "init" -d "Initialize repository"
complete -c dot-man -n "__fish_use_subcommand" -a "status" -d "Show status"
complete -c dot-man -n "__fish_use_subcommand" -a "switch" -d "Switch branch"
complete -c dot-man -n "__fish_use_subcommand" -a "edit" -d "Edit config"
complete -c dot-man -n "__fish_use_subcommand" -a "deploy" -d "Deploy branch"
complete -c dot-man -n "__fish_use_subcommand" -a "audit" -d "Audit secrets"
complete -c dot-man -n "__fish_use_subcommand" -a "branch" -d "Manage branches"

# Branch subcommands
complete -c dot-man -n "__fish_seen_subcommand_from branch" -a "list" -d "List branches"
complete -c dot-man -n "__fish_seen_subcommand_from branch" -a "delete" -d "Delete branch"

# Options
complete -c dot-man -l help -d "Show help"
complete -c dot-man -l version -d "Show version"
complete -c dot-man -n "__fish_seen_subcommand_from init" -l force -d "Force reinitialize"
complete -c dot-man -n "__fish_seen_subcommand_from switch" -l dry-run -d "Preview changes"
complete -c dot-man -n "__fish_seen_subcommand_from switch" -l force -d "Skip prompts"
complete -c dot-man -n "__fish_seen_subcommand_from deploy" -l dry-run -d "Preview changes"
complete -c dot-man -n "__fish_seen_subcommand_from deploy" -l force -d "Skip prompts"
complete -c dot-man -n "__fish_seen_subcommand_from audit" -l strict -d "Strict mode"
complete -c dot-man -n "__fish_seen_subcommand_from audit" -l fix -d "Auto-fix secrets"
complete -c dot-man -n "__fish_seen_subcommand_from status" -s v -l verbose -d "Verbose output"
complete -c dot-man -n "__fish_seen_subcommand_from status" -l secrets -d "Show secrets"
EOF
print_status "Fish completion installed: $COMPLETIONS_FISH/dot-man.fish"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       Installation Complete!         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check if install dir is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]] && [[ ":$PATH:" != *":$PIP_BIN:"* ]]; then
    print_warning "Add this to your shell config to use dot-man:"
    echo ""
    echo "  # For bash/zsh:"
    echo "  export PATH=\"\$PATH:$PIP_BIN\""
    echo ""
    echo "  # For fish:"
    echo "  fish_add_path $PIP_BIN"
    echo ""
fi

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
