# config

View and edit the dot-man configuration file.

## Usage

```bash
dot-man config
dot-man config get <key>
dot-man config set <key> <value>
```

## Subcommands

### `config` (no args)

Opens the config file in your default editor ($EDITOR).

### `config get <key>`

Get a config value:

```bash
dot-man config get settings.default_branch
dot-man config get main.paths
```

### `config set <key> <value>`

Set a config value:

```bash
dot-man config set settings.default_branch main
dot-man config set main.deploy_method symlink
```

### `config tutorial`

Interactive tutorial for setting up your first configuration. Walks through creating sections, adding paths, and configuring hooks step by step.

```bash
dot-man config tutorial
```
