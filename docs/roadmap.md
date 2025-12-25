# Development Roadmap

## MVP (v0.1.0) - Core Functionality

**Goal:** Basic dotfile management with git-backed branches.

### Phase 1: Foundation

- Project setup (pyproject.toml, package structure)
- Core modules: constants, exceptions, config parsing
- File operations and secret detection patterns

### Phase 2: Core Commands

- `dot-man init` - Initialize repository structure
- `dot-man status` - Display current state
- `dot-man switch <branch>` - Save/deploy configurations
- `dot-man edit` - Open config in editor
- `dot-man audit` - Scan for secrets
- `dot-man deploy <branch>` - One-way deploy for new machines

### Phase 3: Polish

- Test suite with pytest
- Error handling and user feedback
- Documentation and examples

---

## v1.0.0 - Full Feature Set

- `dot-man sync` - Push/pull with remote
- `dot-man remote get/set` - Remote configuration
- `dot-man doctor` - Diagnostics and health checks
- Shell completions (bash, zsh, fish)

---

## v1.1.0 - Advanced Features (Future)

- `dot-man backup create/list/restore` - Backup management
- `dot-man template` - Machine-specific variable substitution
- `dot-man conflicts list/resolve` - Merge conflict handling
- Web UI for configuration (v2.0 consideration)

---

## Success Metrics

| Metric        | Target                     |
| ------------- | -------------------------- |
| Test Coverage | 70%+                       |
| Core Commands | All 6 MVP commands working |
| Documentation | All commands documented    |
| Performance   | Handle 100+ files in <5s   |
