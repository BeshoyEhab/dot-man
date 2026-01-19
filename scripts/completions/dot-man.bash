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
