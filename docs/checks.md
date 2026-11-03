# What each check does

The checks are read-only. They never edit or delete your files. Every problem comes with a
"What to do" list: plain notes, and commands you can copy (lines starting with `$`).

| Check | Status levels | What it looks at | Why |
|---|---|---|---|
| `versions` | FAIL / WARN / OK / INFO | `caelestia -v`, `quickshell --version`, `hyprctl version`, installed pacman packages | Many bug reports are version mismatches; the maintainers' issue template asks for this output. |
| `config` | FAIL / WARN / OK / INFO | `~/.config/caelestia/shell.json` and `monitors/*/shell.json`: JSON syntax (with line and column), duplicate keys, `paths.*` that point to files that do not exist | `shell.json` is not created by default and is edited by hand, so typos are common. |
| `hyprland` | FAIL / WARN / OK / INFO | Lua vs `.conf` config (using your Hyprland version), and every `kb_layout` code (live and in config files) against the xkb layout list, with a suggestion for the closest valid code | A wrong code (for example `ar` instead of `ara`) makes Hyprland silently fall back to US. |
| `state` | WARN / OK | `~/.local/state/caelestia/scheme.json` and `wallpaper/path.txt` | When these are missing, scheme changes can appear to apply while nothing changes (caelestia-dots/shell issue #1177). |

## Exit code

`0` if there is no FAIL, `1` otherwise. Warnings do not change the exit code.
`fix` exits with `2` when it cannot ask questions (no terminal).

## Safe repairs (`caelestia-doctor fix`)

| Problem | Repair |
|---|---|
| `shell.json` is empty | Write `{}` into it |
| A `paths.*` value fails only because of capital letters | Replace that one value with the correct spelling, leaving the rest of the file untouched |

How it stays safe:

1. You see every repair first and choose which ones to apply, then confirm.
2. The original file is copied to `<name>.backup-<date>` before any change.
3. The file is replaced atomically, and the result must still be valid JSON.
4. Everything else (invalid JSON, duplicate keys, a keyboard layout code, packages, state files) is only explained with steps, because the right answer depends on you.

## Adding a check

1. Create `src/caelestia_doctor/checks/yourcheck.py` with a `run_checks() -> list[Result]` function.
2. Register it in `checks/__init__.py`.
3. Give each WARN/FAIL a short `hint` (why) and `steps` (what to do). Add a `repair` only when there is exactly one obviously correct fix.
4. Add a test in `tests/`.
