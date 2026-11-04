# caelestia-doctor

Diagnose and repair common problems on **Arch-based Linux (Arch, CachyOS)**, **Hyprland** and the **[Caelestia](https://github.com/caelestia-dots) shell**. For every problem it tells you what to do next, and for a few safe cases it can fix the file for you.

> Unofficial community tool. Not affiliated with the Caelestia project.
> Arabic version: [README.ar.md](README.ar.md)

## The safety model, in short

| Kind of command | What it does |
|---|---|
| `check`, `deep-check`, `logs`, `command-check`, `report`, and every `--dry-run` | **Only read.** They never change anything. |
| `fix`, `undo`, `restore`, `backup restore`, `packages`, `install` | Change things **only after you confirm**. File edits are backed up first. |
| `fix --all` | Applies every safe local repair **without asking**. Use it only when you have read `fix --dry-run`. |

It never removes your files or packages, never updates your whole system, and never runs commands you paste into `command-check`.

## Install

```sh
sudo pacman -S --needed python-pipx
pipx install git+https://github.com/mryujruu/caelestia-doctor
pipx ensurepath          # then open a new terminal
caelestia-doctor --version
```

Update with `pipx upgrade caelestia-doctor`. It needs Python 3.11 or newer.

## Quick start

```sh
caelestia-doctor                # run every check, with suggestions
caelestia-doctor fix --dry-run  # see what could be repaired, change nothing
caelestia-doctor fix            # choose repairs, then confirm
caelestia-doctor report         # a report to paste into a GitHub issue
```

Example (shortened):

```
 ⚠ Warnings (1)

 ┌─ shell.json → paths.mediaGif
 │ path does not exist: ~/Pictures/wallpapers/cat.gif
 │ Linux paths are case-sensitive: Pictures and pictures are different folders.
 │
 │ What to do
 │   Only the capital letters are wrong. The correct path is:
 │   ~/Pictures/Wallpapers/cat.gif
 │
 │ Can be fixed automatically
 │   In paths.mediaGif, change ~/Pictures/wallpapers/cat.gif to ~/Pictures/Wallpapers/cat.gif
 │   $ caelestia-doctor fix
 └─
```

## Commands

| Command | What it does |
|---|---|
| `check` (default) | Runs every check below and shows a **What to do** list under each problem. |
| `deep-check` | Slower: runs `pacman -Qkk` to find package-owned files that were changed. Changes in `/etc` can be intentional, so it only reports. |
| `fix [--all] [--dry-run]` | Lists safe repairs, asks which to apply, then asks again. `--dry-run` only previews. |
| `undo BACKUP` | Restores one backup that `fix` made. It asks first and keeps your current file as another backup. |
| `restore [--component hypr] [--dry-run]` | Compares your config with Caelestia's official default files, lists the missing ones, and asks **per file** before downloading. |
| `packages [--component hypr] [--dry-run]` | Audits the packages in Caelestia's manifest and offers to install each missing one. AUR and unlisted packages are shown separately, with a warning to read the PKGBUILD. |
| `backup list ARCHIVE` | Shows which supported files are inside your own tar backup, without extracting. |
| `backup restore ARCHIVE [--dry-run]` | Restores selected files from that backup, asking per file. Links and unsupported paths are skipped. |
| `logs [-o FILE]` | Reads the recent Hyprland and Quickshell logs. Nothing is uploaded. Saving a report asks first. |
| `command-check --shell fish\|bash --command TEXT` (or `--file FILE`) | Checks the **syntax** of a pasted command with Fish's no-execute mode. It never runs it. Suggests Fish's `set` for simple `name=value` Bash lines, and notices a missing `less` after a pipe. |
| `install` | Offers to install the optional `less` pager (used by `command-check` hints) with `pacman`, after you confirm. |
| `report [--format markdown\|json] [-o FILE]` | Prints a report with your home path and username replaced by `~` and `<user>`. |

Global option: `--no-color` (or set `NO_COLOR`).

## What `check` looks at

- **System:** Arch-based detection (including CachyOS), free disk space, a stuck pacman lock, the pacman database, package-owned files that are missing, and failed system or user services.
- **Versions:** `caelestia -v`, Quickshell, Hyprland and the related pacman packages.
- **`shell.json`:** valid JSON (with line and column), duplicate keys, and `paths.*` that point to files that do not exist. It spots wrong capital letters, like `wallpapers` instead of `Wallpapers`.
- **Hyprland:** Lua or `.conf` config (it uses your Hyprland version to say which one is used), live errors from `hyprctl configerrors`, Lua syntax if `luac` is installed, and keyboard layout codes (`ar` is not valid, `ara` is) with the closest valid suggestion.
- **Fish:** syntax of `~/.config/fish/config.fish` and Caelestia's `user-config.fish`, using `fish -n`, which does not run the file.
- **State files:** `scheme.json` and `wallpaper/path.txt` ([upstream issue #1177](docs/upstream-issues.md)).

Details and limits: [docs/checks.md](docs/checks.md).

## Safe repairs (`fix`)

Only repairs with one obviously correct answer exist:

- an **empty `shell.json`** becomes `{}`;
- a **`paths.*` value** that fails only because of letter case is replaced with the existing path.

Each edit is backed up to `<name>.backup-<date>`, written atomically, and refused if the file changed since the check. Everything else (invalid JSON, keyboard layout codes, missing packages, state files) is explained, not edited, because the right answer depends on you.

## Downloads and the GitHub rate limit

`restore` and `packages` read the current `main` of `caelestia-dots/caelestia`. For a restore run it pins one commit, checks every file against its Git blob hash, refuses paths that leave your home, and never overwrites an existing file.

GitHub limits anonymous API calls. If you see `HTTP 403`, wait a while, or use a read-only token:

```sh
GITHUB_TOKEN=$(gh auth token) caelestia-doctor restore
```

The token goes only to `api.github.com` and is never stored.

## Exit codes

`0` when no check fails, `1` when at least one fails (warnings do not count), `2` when `fix` needs to ask a question but there is no terminal.

## Good to know

- It targets Arch-based systems. On other systems it warns and skips what it cannot check.
- `luac` checks Lua syntax only, not Hyprland option names or plugins.
- Reports and logs may still hold private details. Read them before sharing.
- It was developed and tested on a few Arch setups. Please report what it gets wrong.

## Development

```sh
pip install -e ".[dev]" pyflakes
python -m pytest -q
python -m pyflakes src tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [CHANGELOG.md](CHANGELOG.md).

## License

MIT
