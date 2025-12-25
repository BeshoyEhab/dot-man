# TODO

## v0.1.0 (Current) ✅

- [x] Core CLI with Click
- [x] Git operations with GitPython
- [x] Secret detection (10 patterns)
- [x] Commands: init, status, switch, edit, deploy, audit
- [x] Branch management (list, delete)
- [x] Install script with shell completions
- [x] Unit tests

## v0.2.0 (Current) ✅

- [x] Hooks: `pre_deploy` and `post_deploy`
- [x] Smart deployment (skip identical files)
- [x] Directory recursion fix
- [x] Interactive branch deletion
- [x] Shell completions for branches

## v0.3.0 - Remote Sync

- [ ] `dot-man sync` - Push/pull with remote
- [ ] `dot-man remote get/set` - Configure remote URL
- [ ] Conflict detection and reporting
- [ ] `--dry-run` for sync operations

## v0.4.0 - Backup System

- [ ] `dot-man backup create` - Manual backups
- [ ] `dot-man backup list` - Show available backups
- [ ] `dot-man backup restore` - Restore from backup
- [ ] Auto-backup before destructive operations
- [ ] Backup rotation (max 5)

## v0.5.0 - Template Variables

- [ ] `dot-man template --set KEY=VALUE`
- [ ] `dot-man template --list`
- [ ] Template substitution (`{{HOSTNAME}}`, `{{EMAIL}}`)
- [ ] System variable auto-population
- [ ] Default value syntax (`{{VAR:default}}`)

## v1.0.0 - Production Ready

- [ ] `dot-man doctor` - Diagnostics and health checks
- [ ] Shell completions via Click native support
- [ ] 80%+ test coverage
- [ ] Full documentation site
- [ ] PyPI publication

## Future Ideas

- [ ] Integration with pro-mgr for project dotfiles
- [ ] Web UI for configuration management
- [ ] Encrypted repository support
- [ ] Dotfile marketplace/sharing
- [ ] Migration tools from chezmoi, yadm, GNU Stow
