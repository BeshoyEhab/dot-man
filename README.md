# dot-man

## Overview

dot-man is a Python CLI tool for managing your dotfiles across multiple machines using git. It provides commands to initialize a repository, switch branches, edit configurations, deploy, audit for secrets, and more.

## Installation

```bash
pip install dot-man
```

Or clone the repository and install in editable mode:

```bash
git clone https://github.com/yourusername/dot-man.git
cd dot-man
pip install -e .
```

## Quick Start

```bash
dot-man init
# Initialize the dot-man repository structure

dot-man switch main
# Switch to the main branch and deploy configuration

dot-man edit
# Open the current configuration in your editor

dot-man deploy main
# Deploy the main branch to a new machine
```

## Documentation

Detailed command specifications, security guidelines, and the development roadmap are available in the `docs/` directory:

- [Command Specs](docs/specs/commands.md)
- [Security Spec](docs/specs/security.md)
- [Roadmap & Timeline](docs/roadmap.md)

## Contributing

See the developer guide in `DEVELOPMENT.md` for setup, testing, and contribution guidelines.

## License

MIT License
