#!/usr/bin/env bash
#
# dot-man PATH setup
# Detects and configures PATH for dot-man executable
#

setup_path() {
    # Detect the bin directory
    if command -v pipx &> /dev/null; then
        # pipx installs to ~/.local/bin by default
        BIN_DIR="$HOME/.local/bin"
    else
        # pip --user installs to ~/.local/bin on most systems
        BIN_DIR="$HOME/.local/bin"
    fi

    # Check if bin dir is in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        print_warning "dot-man is not in your PATH!"
        echo ""
        echo "  The installation directory is: $BIN_DIR"
        echo ""
        
        # Detect shell and offer to add to config
        SHELL_NAME=$(basename "$SHELL")
        
        add_to_path() {
            local config_file="$1"
            local export_line="$2"
            
            if [ -f "$config_file" ]; then
                if ! grep -q "dot-man PATH" "$config_file" 2>/dev/null; then
                    echo "" >> "$config_file"
                    echo "# dot-man PATH" >> "$config_file"
                    echo "$export_line" >> "$config_file"
                    print_status "Added to $config_file"
                    return 0
                else
                    echo "  Already configured in $config_file"
                    return 0
                fi
            fi
            return 1
        }
        
        read -p "Do you want to automatically add it to your shell config? [y/N] " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            ADDED=false
            
            # Bash
            if [ -f "$HOME/.bashrc" ]; then
                add_to_path "$HOME/.bashrc" "export PATH=\"\$PATH:$BIN_DIR\"" && ADDED=true
            fi
            
            # Zsh
            if [ -f "$HOME/.zshrc" ]; then
                add_to_path "$HOME/.zshrc" "export PATH=\"\$PATH:$BIN_DIR\"" && ADDED=true
            fi
            
            # Fish
            if [ -d "$HOME/.config/fish" ]; then
                FISH_CONFIG="$HOME/.config/fish/config.fish"
                if [ -f "$FISH_CONFIG" ]; then
                    if ! grep -q "dot-man PATH" "$FISH_CONFIG" 2>/dev/null; then
                        echo "" >> "$FISH_CONFIG"
                        echo "# dot-man PATH" >> "$FISH_CONFIG"
                        echo "fish_add_path $BIN_DIR" >> "$FISH_CONFIG"
                        print_status "Added to $FISH_CONFIG"
                        ADDED=true
                    else
                        echo "  Already configured in $FISH_CONFIG"
                        ADDED=true
                    fi
                else
                    echo "# dot-man PATH" > "$FISH_CONFIG"
                    echo "fish_add_path $BIN_DIR" >> "$FISH_CONFIG"
                    print_status "Created $FISH_CONFIG with PATH"
                    ADDED=true
                fi
            fi
            
            if [ "$ADDED" = true ]; then
                echo ""
                print_info "Restart your shell or run 'source ~/.bashrc' (or equivalent) to apply changes."
            else
                print_warning "Could not find shell config files. Add manually:"
                echo ""
                echo "  # For bash/zsh:"
                echo "  export PATH=\"\$PATH:$BIN_DIR\""
                echo ""
                echo "  # For fish:"
                echo "  fish_add_path $BIN_DIR"
                echo ""
            fi
        else
            echo ""
            print_info "Add this to your shell config to use dot-man:"
            echo ""
            echo "  # For bash/zsh:"
            echo "  export PATH=\"\$PATH:$BIN_DIR\""
            echo ""
            echo "  # For fish:"
            echo "  fish_add_path $BIN_DIR"
            echo ""
        fi
    fi
}
