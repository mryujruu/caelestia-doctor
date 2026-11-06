# Checks and repairs

The `check` command is read-only. Separate package-install commands require per-package confirmation. The tool never removes packages, updates the whole OS, or deletes user files.

| Check | What it looks at | What happens on a problem |
|---|---|---|
| Arch-based system (including CachyOS) | OS identity, free space, pacman lock and database, package-owned file presence (`pacman -Qkq`), failed system and user units | Shows status, command output, and safe inspection commands; it never deletes a pacman lock, reinstalls a package, or restarts a service. CachyOS packages are checked through the configured pacman repositories. |
| Versions | Caelestia, Quickshell, Hyprland and relevant installed pacman packages | Reports missing commands and versions; package installation remains a user decision. |
| Fish and pager | Syntax of `~/.config/fish/config.fish` and Caelestia `user-config.fish` via `fish -n`; presence of optional `less` | Reports syntax without executing config files. `caelestia-doctor install` asks before running `sudo pacman -S --needed less`. |
| Caelestia config | `shell.json`, per-monitor shell settings, duplicate keys and `paths.*` | Empty JSON and uniquely case-mismatched asset paths have reversible local repairs. Missing optional `shell.json` is INFO. |
| Hyprland | `hyprland.lua` / `hyprland.conf`, active `hyprctl configerrors`, Lua syntax when `luac` is installed, XKB layouts | Missing configs or invalid layouts are reported with precise file/line or restoration guidance. It does not invent custom settings. |
| Caelestia state | `scheme.json` and `wallpaper/path.txt` under XDG state | Suggests the shell command or wallpaper picker; state values are not guessed. |

Hyprland's `configerrors` command only reflects the current session and may not preserve every transient issue. `luac -p` checks Lua syntax but not Hyprland option names, imported module behavior, or plugins.

## Local safe repairs

`caelestia-doctor fix` shows repair candidates and asks which ones to apply, then asks for confirmation. `caelestia-doctor fix --all` applies every deterministic local repair without prompting.

Currently repairable:

- Empty `shell.json` → `{}`
- A path value whose only issue is a unique letter-case mismatch → the matching existing path

Fish syntax errors are diagnosed with Fish's parser but not rewritten automatically. A command entered interactively is not stored in these config files, so the doctor cannot inspect that past command. For the optional `less` pager, use the separate Y/N `install` command.

`command-check --shell fish --command TEXT` parses user-pasted command text with Fish's no-execute mode. It can suggest `set NAME VALUE` for simple Bash-style assignments and detects a missing `less` after a pipe. It never executes pasted text.

Every edited file is backed up, written atomically, and checked for changes since diagnosis. Invalid JSON, missing Hyprland configuration, missing packages, state files, services, plugins, and wallpaper choices require a user decision.

`caelestia-doctor undo BACKUP` restores one backup created by `fix`, asks before changing the target, and saves the current target to another backup first.

## Download missing Caelestia defaults

`caelestia-doctor restore` fetches the official Caelestia dotfiles manifest and file tree, lists missing default files, and prompts `Y/N` separately for each file. `restore --component hypr` limits the list to Hyprland defaults. It only downloads files from the official `caelestia-dots/caelestia` repository at a pinned commit, verifies each Git blob hash, checks the destination stays under the user's home directory, and refuses to overwrite files or symlinks. For the official generated defaults, it separately asks before creating the empty `user-config.fish` hook or running the upstream `caelestia scheme set -n caelestia` initialization command. It does not guess a wallpaper path.

`caelestia-doctor backup list ARCHIVE` previews supported files in a user's tar backup. `backup restore ARCHIVE` asks before restoring each file into the current user's config/state directories. It excludes links and unsupported paths, rejects ambiguous destinations, and never overwrites existing paths.

`backup restore ARCHIVE --dry-run`, `restore --dry-run`, `packages --dry-run`, and `fix --dry-run` only preview. `packages` reads the current official default-component manifest and distinguishes configured pacman repositories from AUR packages; every install is separately confirmed. AUR build recipes remain subject to the user's review. `report --format json` exports redacted machine-readable results.

`caelestia-doctor deep-check` runs the slower `pacman -Qkk` scan and sorts each altered file by what changed:

| Category | Reasons pacman gives | Counts as a problem? |
|---|---|---|
| content changed outside `/etc` | size, MD5/SHA256 checksum, type or symlink mismatch | **Yes (warning)**, named with its package |
| missing from disk | no such file or directory | **Yes (warning)**, except docs and translations |
| changed under `/etc` | any | No: usually your own edits |
| removed docs or translations | missing files under `/usr/share/{doc,man,info,locale,help,gtk-doc}` | No |
| only time, owner or permissions | modification time, UID, GID or permissions mismatch | No |
| unreadable without root | permission denied | No, but it could not be checked: run `sudo pacman -Qkk` |

Each file is counted once even when pacman gives several reasons. `deep-check --full` prints every file by category. It only reports; reinstalling a package is your decision.

`caelestia-doctor logs` optionally reads the recent Hyprland rolling log and Caelestia Quickshell log. It does not upload them. Saving a Markdown report requires confirmation, and logs should be reviewed for private details before sharing.

The repository source is current upstream `main`; its default components can change over time. Review the reported revision and your installed package versions. For a full install, upstream recommends `caelestia install`.

## GitHub rate limit

`restore` and `packages` call the GitHub API without logging in, which GitHub limits per IP address. If you see "GitHub refused the request (HTTP 403)", wait a while, or give the tool a token for read-only access:

```sh
GITHUB_TOKEN=$(gh auth token) caelestia-doctor restore
```

The token is sent only to `api.github.com`, and is never printed or stored.

## Exit codes

`0` when no FAIL result remains, `1` when at least one check fails. Warnings do not change the exit code. Interactive `fix` returns `2` when stdin is not a terminal.

See [upstream-issues.md](upstream-issues.md) for the upstream reports that informed the checks and the limits of those findings.
