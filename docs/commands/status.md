# status

Show current state: active branch, modified files, and summary.

## Usage

```bash
dot-man status
```

## Options

| Flag | Description |
|------|-------------|
| `--json` | Output structured JSON for CI/scripting |
| `--verbose` | Show all files, not just changed ones |

## Text Output

```
Branch: work
Remote: https://github.com/user/dotfiles.git
Repository: ~/.config/dot-man/repo

Sections:
  main (3 files)
    M ~/.bashrc
    M ~/.gitconfig
    M ~/.config/nvim/init.vim

  work (1 file)
    M ~/.config/slack/settings.json

Summary:
  Tracked: 12
  Modified: 4
  Untracked: 2
  Secrets detected: 1
```

## JSON Output

```bash
dot-man status --json
```

```json
{
  "branch": "work",
  "remote": "https://github.com/user/dotfiles.git",
  "repository": "~/.config/dot-man/repo",
  "sections": [
    {
      "name": "main",
      "files": [
        {"path": "~/.bashrc", "status": "modified"},
        {"path": "~/.gitconfig", "status": "modified"}
      ]
    }
  ],
  "summary": {
    "tracked": 12,
    "modified": 4,
    "untracked": 2
  }
}
```
