# Installation

## From PyPI (Recommended)

```bash
pip install dotman-git
```

## With pipx (Isolated)

```bash
pipx install dotman-git
```

## One-Line Install

```bash
pip install dotman-git && dot-man init
```

Or with pipx:

```bash
pipx install dotman-git && dot-man init
```

## From Source

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
pip install -e .
```

Or with pipx:

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
pipx install -e .
```

## Shell Completions

Shell completions are installed automatically on first run. To install manually:

```bash
dot-man completions install
```

Supports **bash**, **zsh**, and **fish**.

## Requirements

- Python 3.10+
- Git
