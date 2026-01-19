# dot-man fish completion

function __fish_dot_man_complete
    set -l response (env _DOT_MAN_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) dot-man 2>/dev/null)
    for completion in $response
        # Click outputs "type,value" - we only want the value
        set -l parts (string split "," -- $completion)
        if test (count $parts) -ge 2
            # First part is type (plain, file, dir), second is value
            echo $parts[2]
        else if test (count $parts) -eq 1
            # Just the value
            echo $parts[1]
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
complete -c dot-man -n "__fish_use_subcommand" -a "sync" -d "Sync with remote"
complete -c dot-man -n "__fish_use_subcommand" -a "remote" -d "Manage remote"
complete -c dot-man -n "__fish_use_subcommand" -a "add" -d "Add file to tracking"
complete -c dot-man -n "__fish_use_subcommand" -a "tui" -d "Open TUI"

# Branch subcommands
complete -c dot-man -n "__fish_seen_subcommand_from branch" -a "list" -d "List branches"
complete -c dot-man -n "__fish_seen_subcommand_from branch" -a "delete" -d "Delete branch"

# Remote subcommands
complete -c dot-man -n "__fish_seen_subcommand_from remote" -a "get" -d "Get remote URL"
complete -c dot-man -n "__fish_seen_subcommand_from remote" -a "set" -d "Set remote URL"

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
