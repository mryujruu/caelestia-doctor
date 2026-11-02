"""Files the Caelestia shell expects to find in ~/.local/state/caelestia.

Source: caelestia-dots/shell issue #1177, where users saw colour schemes "apply" with no
error and nothing changing while these two files were missing.
"""

from __future__ import annotations

from ..utils import INFO, OK, WARN, Result, expand, read_text, state_dir

HINT = (
    "Reported fix in that issue: reinstall the git version of the colour library "
    "(yay -Syu python-materialyoucolor-git --rebuild). This was one user's report, "
    "not confirmed by the maintainers."
)


def run_checks() -> list[Result]:
    base = state_dir() / "caelestia"
    results: list[Result] = []

    if not base.is_dir():
        return [Result("State directory", WARN, f"{base} does not exist",
                       "Start the shell once (`caelestia shell -d`) and run this again. " + HINT)]

    scheme = base / "scheme.json"
    wall = base / "wallpaper" / "path.txt"

    if scheme.exists():
        results.append(Result("scheme.json", OK, "present"))
    else:
        results.append(Result("scheme.json", WARN, "missing",
                              "Colour scheme changes may silently do nothing. " + HINT))

    if wall.exists():
        target = (read_text(wall) or "").strip()
        if not target:
            results.append(Result("wallpaper/path.txt", WARN, "present but empty"))
        elif not expand(target).exists():
            results.append(Result("wallpaper/path.txt", WARN,
                                  f"points to a file that does not exist: {target}",
                                  "Set the wallpaper again with `caelestia wallpaper`."))
        else:
            results.append(Result("wallpaper/path.txt", OK, "points to an existing file"))
    else:
        results.append(Result("wallpaper/path.txt", WARN, "missing",
                              "Set a wallpaper with `caelestia wallpaper`. " + HINT))
    return results
