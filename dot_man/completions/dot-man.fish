# dot-man fish completion
# Fully dynamic: delegates every TAB press to `dot-man --complete fish`,
# which gathers commands, subcommands, options, static choices, defaults
# and dynamic values (branches, tags, commits...) from the CLI itself,
# so completions never go stale.
complete -c dot-man -e

function __fish_dot_man_complete
    set -l tokens (commandline -opc) "--" (commandline -ct)
    command dot-man --complete fish $tokens 2>/dev/null
end

complete -c dot-man -f -a '(__fish_dot_man_complete)'
