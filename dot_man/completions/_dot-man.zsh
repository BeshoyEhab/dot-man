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
