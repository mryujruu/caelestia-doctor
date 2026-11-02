# What each check does

All checks are read-only. caelestia-doctor never edits or deletes your files.

| Check | Status levels | What it looks at | Why |
|---|---|---|---|
| `versions` | FAIL / WARN / OK / INFO | `caelestia -v`, `quickshell --version`, `hyprctl version`, installed pacman packages | Many bug reports are version mismatches; the maintainers' issue template asks for this output. |
| `config` | FAIL / WARN / OK / INFO | `~/.config/caelestia/shell.json` and `monitors/*/shell.json`: JSON syntax (with line and column), duplicate keys, `paths.*` that point to files that do not exist | `shell.json` is not created by default and is edited by hand, so typos are common. |
| `hyprland` | FAIL / WARN / OK / INFO | Lua vs `.conf` config, and every `kb_layout` code (live and in config files) against the xkb layout list | A wrong code (for example `ar` instead of `ara`) makes Hyprland silently fall back to US. |
| `state` | WARN / OK | `~/.local/state/caelestia/scheme.json` and `wallpaper/path.txt` | When these are missing, scheme changes can appear to apply while nothing changes (caelestia-dots/shell issue #1177). |

## Exit code

`0` if there is no FAIL, `1` otherwise. Warnings do not change the exit code.

## Adding a check

1. Create `src/caelestia_doctor/checks/yourcheck.py` with a `run_checks() -> list[Result]` function.
2. Register it in `checks/__init__.py`.
3. Add a test in `tests/`.
