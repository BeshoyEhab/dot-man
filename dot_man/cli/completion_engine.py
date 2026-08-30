"""Decorator-driven shell completion engine for dot-man.

Single source of truth for shell completions: commands, subcommands,
options, accepted values (static or dynamic) and defaults are gathered
from the Click CLI definition itself, extended via the :func:`completes`
decorator registry. The fish completion script delegates every TAB press
to ``dot-man --complete fish`` so completions can never go stale.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import click

PROG_NAME = "dot-man"

CompletionEntry = tuple[str, str]
ProviderResult = Iterable[
    "str | tuple[str, str] | click.shell_completion.CompletionItem"
]
ProviderFn = Callable[["CompletionContext"], ProviderResult]


@dataclass
class CompletionContext:
    """State passed to value providers registered with :func:`completes`."""

    args: list[str] = field(default_factory=list)
    incomplete: str = ""
    command_path: str = ""


_PROVIDERS: dict[tuple[str, str], ProviderFn] = {}


def completes(command_path: str, param: str | None = None):
    """Register a value provider for a command path (and optional param).

    The decorated callable receives a :class:`CompletionContext` and may
    return plain strings, ``(value, description)`` tuples or Click
    ``CompletionItem`` objects. A ``(path, param)`` registration wins
    over the generic ``(path, None)`` one.

    Example::

        @completes("config set", param="value")
        def _config_values(ctx):
            return ["true", "false"]
    """

    def decorator(fn: ProviderFn) -> ProviderFn:
        _PROVIDERS[(command_path, param or "")] = fn
        return fn

    return decorator


def _normalize(result: ProviderResult) -> list[CompletionEntry]:
    """Normalize provider output to (value, description) pairs."""
    pairs: list[CompletionEntry] = []
    if result is None:
        return pairs
    for item in result:
        if isinstance(item, str):
            pairs.append((item, ""))
        elif isinstance(item, tuple):
            pairs.append((item[0], item[1]))
        else:
            pairs.append((item.value, item.help or ""))
    return pairs


class CompletionEngine:
    """Gathers completions by walking the Click command tree."""

    def __init__(self, cli_root: click.Command, prog_name: str = PROG_NAME):
        self.cli = cli_root
        self.prog_name = prog_name

    def complete(self, args: list[str], incomplete: str) -> list[CompletionEntry]:
        """Return (value, description) pairs for the given word list.

        ``args`` holds the words before the word being completed (the
        leading program name is optional and ignored), ``incomplete`` is
        the partial word itself.
        """
        try:
            args = self._strip_prog_name(args)
            chain, rest = self._walk(args)

            if incomplete.startswith("-") and "--" not in rest:
                if "=" in incomplete:
                    entries = self._split_option_value(chain, args, incomplete)
                else:
                    entries = self._option_names(chain, args, incomplete)
            elif chain:
                entries = self._word_values(chain, args, incomplete, rest)
            else:
                entries = []
            return self._filter(entries, incomplete)
        except Exception as e:
            logging.debug("Completion engine error: %s", e)
            return []

    def _strip_prog_name(self, args: list[str]) -> list[str]:
        if args and (
            args[0] == self.prog_name or args[0].endswith("/" + self.prog_name)
        ):
            return args[1:]
        return args

    def _walk(self, args: list[str]) -> tuple[list[click.Command], list[str]]:
        """Follow command words through nested groups.

        Returns the resolved command chain (root first) and the words
        left over after the deepest command was reached. Options
        interleaved with subcommand names are skipped, consuming one
        following token when they take a value.
        """
        cmd: click.Command = self.cli
        chain = [cmd]
        rest = list(args)
        ctx = click.Context(cmd, info_name=self.prog_name, resilient_parsing=True)

        while isinstance(cmd, click.Group) and rest:
            word = rest[0]
            if word == "--":
                break
            if word.startswith("-"):
                opt = self._find_option(cmd, ctx, word)
                rest.pop(0)
                if (
                    opt is not None
                    and not opt.is_flag
                    and rest
                    and not rest[0].startswith("-")
                ):
                    rest.pop(0)
                continue
            sub = click.Group.get_command(cmd, ctx, word)
            if sub is None:
                break
            rest.pop(0)
            chain.append(sub)
            cmd = sub
        return chain, rest

    def _find_option(
        self, cmd: click.Command, ctx: click.Context, word: str
    ) -> click.Option | None:
        name = word.split("=", 1)[0]
        for param in cmd.get_params(ctx):
            if isinstance(param, click.Option) and name in (
                *param.opts,
                *param.secondary_opts,
            ):
                return param
        return None

    def _describe_option(self, param: click.Option, ctx: click.Context) -> str:
        """Build the description shown next to an option name.

        Includes the help text plus the accepted choices and the
        declared default when applicable.
        """
        desc = param.help or ""
        choices = getattr(param.type, "choices", None)
        if choices:
            desc = f"{desc} [choices: {'|'.join(str(c) for c in choices)}]".strip()
        default = param.get_default(ctx, call=False)
        if default is not None and not param.is_flag:
            desc = f"{desc} [default: {default}]".strip()
        return desc

    def _option_names(
        self, chain: list[click.Command], args: list[str], incomplete: str
    ) -> list[CompletionEntry]:
        """Complete option names of the current command and the root."""
        cmd = chain[-1]
        ctx = click.Context(cmd, info_name=cmd.name, resilient_parsing=True)

        entries: list[CompletionEntry] = []
        seen: set[int] = set()
        for owner in {id(cmd): cmd, id(self.cli): self.cli}.values():
            for param in owner.get_params(ctx):
                if (
                    id(param) in seen
                    or not isinstance(param, click.Option)
                    or param.hidden
                ):
                    continue
                seen.add(id(param))
                if not param.multiple and any(o in args for o in param.opts):
                    continue
                desc = self._describe_option(param, ctx)
                for name in (*param.opts, *param.secondary_opts):
                    if name.startswith(incomplete):
                        entries.append((name, desc))
        return entries

    def _split_option_value(
        self, chain: list[click.Command], args: list[str], incomplete: str
    ) -> list[CompletionEntry]:
        """Complete ``--option=<TAB>`` style values, emitting full tokens."""
        name, _, _prefix = incomplete.partition("=")
        cmd = chain[-1]
        path = self._path_of(chain)
        ctx = click.Context(cmd, info_name=cmd.name, resilient_parsing=True)
        opt = self._find_option(cmd, ctx, name)
        if opt is None or opt.is_flag:
            return []
        values = self._values_for_param(cmd, path, opt, ctx, _prefix, args)
        return [(f"{name}={v}", d) for v, d in values]

    def _word_values(
        self,
        chain: list[click.Command],
        args: list[str],
        incomplete: str,
        rest: list[str],
    ) -> list[CompletionEntry]:
        """Complete option values, argument values or subcommands."""
        cmd = chain[-1]
        path = self._path_of(chain)
        ctx = click.Context(cmd, info_name=cmd.name, resilient_parsing=True)

        prev = args[-1] if args else ""
        if prev.startswith("-") and prev != "--":
            opt = self._find_option(cmd, ctx, prev)
            if opt is not None and not opt.is_flag:
                return self._values_for_param(cmd, path, opt, ctx, incomplete, args)

        if isinstance(cmd, click.Group):
            return self._subcommands(cmd, incomplete)

        arg = self._next_argument(cmd, ctx, rest)
        if arg is not None:
            return self._values_for_param(cmd, path, arg, ctx, incomplete, args)
        return []

    @staticmethod
    def _path_of(chain: list[click.Command]) -> str:
        return " ".join(c.name or "" for c in chain[1:]).strip()

    def _subcommands(
        self, group: click.Group, incomplete: str
    ) -> list[CompletionEntry]:
        """List subcommands; aliases are labeled and sorted last."""
        primaries: list[CompletionEntry] = []
        aliases: list[CompletionEntry] = []
        for name, sub in group.commands.items():
            if sub.hidden:
                continue
            short = sub.get_short_help_str(limit=60)
            if name == sub.name:
                primaries.append((name, short))
            elif short:
                aliases.append((name, f"(alias) {short}"))
        return primaries + aliases

    def _next_argument(
        self, cmd: click.Command, ctx: click.Context, rest: list[str]
    ) -> click.Argument | None:
        """Find the argument slot matching the number of given values."""
        positional = [w for w in rest if not w.startswith("-")]
        arguments = [p for p in cmd.get_params(ctx) if isinstance(p, click.Argument)]
        index = len(positional)
        if 0 <= index < len(arguments):
            return arguments[index]
        if arguments and arguments[-1].nargs == -1:
            return arguments[-1]
        return None

    def _values_for_param(
        self,
        cmd: click.Command,
        path: str,
        param: click.Parameter,
        ctx: click.Context,
        incomplete: str,
        args: list[str],
    ) -> list[CompletionEntry]:
        """Values for an option/argument slot.

        Priority: decorator-registered provider, static ``click.Choice``
        choices, then the parameter's own completion callback (the
        dynamic branches/tags/commits providers attached throughout the
        CLI).
        """
        specific = _PROVIDERS.get((path, param.name or ""))
        if specific is None:
            specific = _PROVIDERS.get((path, ""))
        if specific is not None:
            try:
                ctx_info = CompletionContext(
                    args=args, incomplete=incomplete, command_path=path
                )
                return _normalize(specific(ctx_info))
            except Exception as e:
                logging.debug("Provider %s failed: %s", path, e)
                return []

        choices = getattr(param.type, "choices", None)
        if choices is not None:
            return [(str(c), "") for c in choices]

        try:
            return _normalize(param.shell_complete(ctx, incomplete))
        except Exception as e:
            logging.debug(
                "Completion callback failed for %s %s: %s", path, param.name, e
            )
            return []

    @staticmethod
    def _filter(
        entries: list[CompletionEntry], incomplete: str
    ) -> list[CompletionEntry]:
        seen: set[str] = set()
        out: list[CompletionEntry] = []
        for value, desc in entries:
            if not value.startswith(incomplete) or value in seen:
                continue
            seen.add(value)
            out.append((value, desc))
        out.sort(key=lambda pair: pair[0].lower())
        return out


def format_fish(pairs: list[CompletionEntry]) -> str:
    """Format entries as fish lines: ``value<TAB>description``."""
    return "\n".join(f"{v}\t{d}" if d else v for v, d in pairs)


def parse_request(argv: list[str]) -> tuple[list[str], str] | None:
    """Extract (words, incomplete) from a ``--complete`` invocation.

    Expected shape::

        dot-man --complete <shell> [program words...] -- <incomplete>

    Returns None when argv is not a valid completion request.
    """
    try:
        idx = argv.index("--complete")
        rest = argv[idx + 2 :]
    except (ValueError, IndexError):
        return None
    if not argv[idx + 1 : idx + 2]:
        return None

    if "--" in rest:
        sep = len(rest) - 1 - rest[::-1].index("--")
        incomplete = rest[sep + 1] if sep + 1 < len(rest) else ""
        return rest[:sep], incomplete
    if not rest:
        return [], ""
    return rest[:-1], rest[-1]


def run_completion_request(argv: list[str]) -> int:
    """Run the engine for a ``--complete`` invocation and print results."""
    request = parse_request(argv)
    if request is None:
        return 1
    args, incomplete = request

    from .interface import cli

    engine = CompletionEngine(cli)
    pairs = engine.complete(args, incomplete)

    shell = argv[argv.index("--complete") + 1]
    if shell == "fish":
        output = format_fish(pairs)
    else:
        output = "\n".join(v for v, _ in pairs)
    if output:
        click.echo(output)
    return 0


def maybe_run_completion(argv: list[str] | None = None) -> None:
    """Run the completion engine and exit when ``--complete`` is requested.

    Called from the CLI entry point before anything else so completions
    never trigger onboarding, git access or other side effects.
    """
    argv = list(sys.argv if argv is None else argv)
    if "--complete" not in argv:
        return
    sys.exit(run_completion_request(argv))


@completes("config set", param="value")
def _complete_config_value(ctx: CompletionContext) -> ProviderResult:
    """Static choices for boolean config values."""
    return ["true", "false"]


@completes("add", param="path")
def _complete_add_path(ctx: CompletionContext) -> ProviderResult:
    """Complete local file/directory paths for the add command."""
    import os
    from pathlib import Path

    incomplete = ctx.incomplete or "."
    expanded = os.path.expanduser(incomplete)
    parent = Path(expanded).parent if expanded else Path(".")
    prefix = Path(expanded).name if expanded else ""

    if not parent.exists():
        return []

    results: list[str] = []
    try:
        for entry in sorted(parent.iterdir()):
            if entry.name.startswith(prefix) and not entry.name.startswith("."):
                if incomplete.startswith("~"):
                    display = str(entry).replace(str(Path.home()), "~", 1)
                else:
                    display = str(entry)
                results.append(display + "/" if entry.is_dir() else display)
    except PermissionError:
        pass
    return results


@completes("bootstrap", param="pm")
def _complete_bootstrap_pm(ctx: CompletionContext) -> ProviderResult:
    """Complete package manager names for the bootstrap command."""
    return [
        ("brew", "macOS package manager"),
        ("apt", "Debian/Ubuntu"),
        ("dnf", "Fedora/RHEL"),
        ("pacman", "Arch Linux"),
        ("zypper", "openSUSE"),
        ("nix-env", "NixOS"),
        ("xbps-install", "Void Linux"),
        ("pkg", "FreeBSD"),
    ]
