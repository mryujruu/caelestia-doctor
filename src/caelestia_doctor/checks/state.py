"""Files the Caelestia shell expects to find in ~/.local/state/caelestia.

Source: caelestia-dots/shell issue #1177, where users saw colour schemes "apply" with no
error and nothing changing while these two files were missing.
"""

from __future__ import annotations

from ..utils import WARN, OK, Result, expand, read_text, short, state_dir

WHY = "Colour scheme changes may silently do nothing when the shell state files are missing."
STEPS = [
    "Start the shell once so it can create its files, then run this check again:",
    "$ caelestia shell -d",
    "If that does not help, one user in issue #1177 fixed it by rebuilding the colour library "
    "(a single report, not confirmed by the maintainers):",
    "$ yay -Syu python-materialyoucolor-git --rebuild",
]


def run_checks() -> list[Result]:
    base = state_dir() / "caelestia"
    results: list[Result] = []

    if not base.is_dir():
        return [Result("State directory", WARN, f"{short(base)} does not exist", WHY, steps=STEPS)]

    scheme = base / "scheme.json"
    wall = base / "wallpaper" / "path.txt"

    if scheme.exists():
        results.append(Result("scheme.json", OK, "present"))
    else:
        results.append(Result("scheme.json", WARN, "missing", WHY, steps=STEPS))

    if wall.exists():
        target = (read_text(wall) or "").strip()
        if not target:
            results.append(Result("wallpaper/path.txt", WARN, "present but empty",
                                  "No wallpaper is recorded, so wallpaper-based colours cannot be used.",
                                  steps=["Pick a wallpaper again from the Caelestia launcher or settings."]))
        elif not expand(target).exists():
            results.append(Result("wallpaper/path.txt", WARN,
                                  f"points to a file that does not exist: {target}",
                                  "The wallpaper was moved or deleted.",
                                  steps=["Pick the wallpaper again from the Caelestia launcher or settings."]))
        else:
            results.append(Result("wallpaper/path.txt", OK, "points to an existing file"))
    else:
        results.append(Result("wallpaper/path.txt", WARN, "missing",
                              "No wallpaper is recorded, so wallpaper-based colours cannot be used.",
                              steps=["Pick a wallpaper from the Caelestia launcher or settings."] + STEPS[:2]))
    return results
