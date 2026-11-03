# caelestia-doctor

A diagnostic tool for [Caelestia](https://github.com/caelestia-dots) (Hyprland + Quickshell).
It checks the things that most often go wrong, tells you **what to do about each one**, and
prints a report you can paste into a GitHub issue.

Checks are **read-only**. An optional command, `caelestia-doctor fix`, can apply a few safe
repairs, but only the ones you select, and it backs up each file first.

> Unofficial community tool. Not affiliated with the Caelestia project.

## What it checks

- **Versions**: `caelestia -v`, Quickshell, Hyprland and the related Arch packages
- **`shell.json`**: JSON syntax (with line and column), duplicate keys, and `paths.*` that point to files that do not exist (it spots wrong capital letters, like `wallpapers` vs `Wallpapers`)
- **Hyprland**: Lua vs `.conf` config, and keyboard layout codes (for example `ar` is not valid, `ara` is)
- **State files**: `~/.local/state/caelestia/scheme.json` and `wallpaper/path.txt` (see issue #1177)

Details: [docs/checks.md](docs/checks.md)

## Install (Arch)

```sh
sudo pacman -S --needed python-pipx
pipx install git+https://github.com/mryujruu/caelestia-doctor
```

or from a clone: `pipx install .`. Update with `pipx upgrade caelestia-doctor`.

## Use

```sh
caelestia-doctor            # run all checks, with suggestions
caelestia-doctor fix        # apply the safe repairs you select
caelestia-doctor report     # Markdown report to paste into an issue
caelestia-doctor report -o report.md
caelestia-doctor --no-color # plain output (NO_COLOR works too)
```

Example output:

```
 ⚠ Warnings (2)

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

 ┌─ Keyboard layout in hyprland.lua
 │ unknown code(s) in kb_layout: ar
 │
 │ What to do
 │   Instead of `ar` you probably want: ara (Arabic)
 │   Edit the kb_layout line in ~/.config/hypr/hyprland.lua, then apply it:
 │   $ hyprctl reload
 └─

 ────────────────────────────────────────
 0 problems  ·  2 warnings  ·  6 ok
```

## How `fix` stays safe

- It never runs by itself: `check` and `report` change nothing.
- It lists each repair, you choose which ones, and it asks once more before touching anything.
- Every file is copied to `<name>.backup-<date>` first, and the new file is written atomically.
- It only does repairs with one obvious right answer (an empty `shell.json`, wrong capital letters in a path). It never guesses at your Hyprland config, installs packages, or deletes anything.
- It refuses to run when it has no terminal (for example inside a script).

Reports replace your home path and username with `~` and `<user>`. Read the report before you post it anyway.

Exit code is `1` if any check FAILs, otherwise `0`.

## Develop

```sh
pip install pytest
PYTHONPATH=src python -m pytest
```

Ideas and new checks are welcome: see "Adding a check" in [docs/checks.md](docs/checks.md).

## العربية

أداة تشخيص لمستخدمي Caelestia. بتفحص الإصدارات، وملف `shell.json`، وإعدادات Hyprland (ومنها أكواد لغة الكيبورد)، وملفات الحالة، وبتقولك **تعمل إيه** لكل مشكلة، وبتطلّعلك تقرير جاهز تلصقه في GitHub.

الفحص العادي ما بيعدّلش أي ملف. أمر `fix` بيصلّح حاجتين بس (ملف `shell.json` الفاضي، وحروف كبيرة/صغيرة غلط في المسار)، وبعد ما تختار وتأكّد، وبعد ما يعمل نسخة احتياطية من الملف.

```sh
caelestia-doctor
caelestia-doctor fix
caelestia-doctor report
```

## License

MIT
