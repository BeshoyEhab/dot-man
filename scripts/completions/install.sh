#!/usr/bin/env bash
#
# dot-man completions installer
# Copies shell completion files to their target locations
#

COMPLETIONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install_completions() {
    print_info "Setting up shell completions..."

    # Bash completion
    mkdir -p "$COMPLETIONS_BASH"
    cp "$COMPLETIONS_DIR/dot-man.bash" "$COMPLETIONS_BASH/dot-man"
    print_status "Bash completion installed: $COMPLETIONS_BASH/dot-man"

    # Zsh completion
    mkdir -p "$COMPLETIONS_ZSH"
    cp "$COMPLETIONS_DIR/_dot-man.zsh" "$COMPLETIONS_ZSH/_dot-man"
    print_status "Zsh completion installed: $COMPLETIONS_ZSH/_dot-man"

    # Fish completion
    mkdir -p "$COMPLETIONS_FISH"
    cp "$COMPLETIONS_DIR/dot-man.fish" "$COMPLETIONS_FISH/dot-man.fish"
    print_status "Fish completion installed: $COMPLETIONS_FISH/dot-man.fish"
}
