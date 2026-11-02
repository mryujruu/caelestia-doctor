# caelestia-doctor

A small, **read-only** diagnostic tool for [Caelestia](https://github.com/caelestia-dots) (Hyprland + Quickshell).
It checks the things that most often go wrong and prints a report you can paste into a GitHub issue.

> Unofficial community tool. Not affiliated with the Caelestia project.

## What it checks

- **Versions**: `caelestia -v`, Quickshell, Hyprland and the related Arch packages
- **`shell.json`**: JSON syntax (with line and column), duplicate keys, and `paths.*` that point to files that do not exist
- **Hyprland**: Lua vs `.conf` config, and keyboard layout codes (for example `ar` is not valid, `ara` is)
- **State files**: `~/.local/state/caelestia/scheme.json` and `wallpaper/path.txt` (see issue #1177)

Details: [docs/checks.md](docs/checks.md)

## Install (Arch)

```sh
sudo pacman -S --needed python-pipx
pipx install git+https://github.com/mryujruu/caelestia-doctor
```

or from a clone: `pipx install .`

## Use

```sh
caelestia-doctor            # run all checks
caelestia-doctor report     # Markdown report to paste into an issue
caelestia-doctor report -o report.md
```

Example output:

```
[FAIL]  Keyboard layout: active kb_layout "us,ar" contains unknown code(s): ar
        → Hyprland falls back to US silently. Arabic is `ara`, not `ar`.
[WARN]  Hyprland config: both hyprland.lua and hyprland.conf exist
[INFO]  shell.json: not found (that is normal)

1 problem(s), 1 warning(s), 0 ok.
```

Reports replace your home path and username with `~` and `<user>`. Read the report before you post it anyway.

Exit code is `1` if any check FAILs, otherwise `0`.

## Develop

```sh
pip install pytest
PYTHONPATH=src python -m pytest
```

Ideas and new checks are welcome: see "Adding a check" in [docs/checks.md](docs/checks.md).

## العربية

أداة تشخيص **للقراءة فقط** لمستخدمي Caelestia. بتفحص الإصدارات، وملف `shell.json`، وإعدادات Hyprland (ومنها أكواد لغة الكيبورد)، وملفات الحالة، وبتطلّعلك تقرير جاهز تلصقه في GitHub. الأداة مش بتعدّل أي ملف عندك.

```sh
caelestia-doctor
caelestia-doctor report
```

## License

MIT
