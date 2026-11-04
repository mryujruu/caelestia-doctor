## 0.6.0

- Fixed: `installer.py` had an indentation error, so 0.5.0 could not start at all. A new test now imports every module, so this cannot ship again.
- Fixed: importing `caelestia_doctor.__main__` ran the tool; it now runs only with `python -m caelestia_doctor`.
- Added: `restore` and `packages` accept an optional `GITHUB_TOKEN` or `GH_TOKEN` to raise GitHub's anonymous rate limit. The token is only sent to `api.github.com` and is never stored.
- Improved: when GitHub answers 403 or 429 (rate limit), the tool says so and shows how to use a token instead of a bare "HTTP Error 403".
- Improved: the heading of every command no longer says "read-only", because commands such as `fix` and `restore` change things after you confirm. The `--help` text now describes all eleven commands.
- Docs: English `README.md` that explains every command and the safety model, a full Arabic `README.ar.md`, and the maintainer steps moved to `docs/maintainer-guide.ar.md`.
- Project: GitHub Actions CI (Python 3.11 to 3.13, tests and lint), bug report and pull request templates, `CONTRIBUTING.md`, `SECURITY.md`, project links in `pyproject.toml`, and lint clean-ups.
- Tests: 83 tests (new: module imports, CLI help, GitHub request handling).

## 0.5.0

- Added explicit CachyOS detection, including systems whose `/etc/os-release` omits `ID_LIKE`.
- Clarified that package checks and installs use the configured pacman repositories, including CachyOS repositories.
- Expanded the Arabic README with first-time ZIP installation, pipx PATH setup, safe smoke-check commands, GitHub authentication, first upload, updating an existing repository, and reinstalling the update locally.
- Updated the support notes for Arch Linux and CachyOS.

## 0.4.0

- Added safe, selective inspection and restoration from the user's own tar backup.
- Added a manifest-driven Caelestia package audit and per-package confirmed installation; AUR/unlisted packages are handled separately.
- Added Fish config validation and `command-check` for pasted Fish/Bash commands without execution; offers a Fish `set` suggestion for simple Bash-style assignments.
- Added `less` detection and a confirmed optional package installer.
- Added recent Hyprland/Quickshell log collection, deeper `pacman -Qkk` integrity check, and redacted JSON reports.
- Added dry-run previews and `undo` for file repairs, preserving the previous current file as another backup.

## 0.3.0

- Added Arch Linux checks for disk space, pacman lock/database health, and failed system/user services.
- Added active Hyprland `configerrors` diagnostics, optional `luac` syntax validation, and a warning for missing Hyprland config.
- Added `restore`, which compares the user's config with default component files in the official Caelestia dots manifest and asks before each download.
- Pins the upstream commit for a restore run, verifies each downloaded file against its Git blob hash, refuses path escapes, and never overwrites existing files.
- Added `fix --all` for deterministic local repairs, with backups and a check rerun after each repair.
- Added upstream issue notes and restore/auto-fix regression tests.
