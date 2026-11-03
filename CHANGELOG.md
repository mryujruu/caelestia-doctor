# Changelog

## 0.2.0
- New: every problem now comes with a "What to do" list, with copyable commands, in a clearer layout (`--no-color` / `NO_COLOR` supported).
- New: `caelestia-doctor fix` applies safe repairs you select, after confirmation, with a backup of each file (empty `shell.json`, wrong capital letters in a `paths.*` value). Contributed in part by a community member.
- New: keyboard layout check suggests the closest valid code (`ar` → `ara`).
- New: path check suggests the correctly capitalised path.
- Improved: the Lua-vs-.conf warning now uses your Hyprland version.
- Fixed: `fix` no longer crashes when there is no input (closed stdin, Ctrl+D).
- Fixed: the `caelestia CLI` line no longer shows only the "Packages:" heading.
- Repo: LF line endings enforced with `.gitattributes`.

## 0.1.0
- First release: versions, `shell.json`, Hyprland layout and state checks, plus `report`.
