"""Which Caelestia / Quickshell / Hyprland versions are installed."""

from __future__ import annotations

from ..utils import FAIL, INFO, OK, WARN, Result, have, run

# Packages worth listing in a bug report (only the installed ones are shown).
PACKAGES = [
    "caelestia-shell", "caelestia-shell-git",
    "caelestia-cli", "caelestia-cli-git",
    "caelestia-meta",
    "quickshell", "quickshell-git",
    "python-materialyoucolor", "python-materialyoucolor-git",
    "hyprland", "hyprland-git",
]


def run_checks() -> list[Result]:
    results: list[Result] = []

    p = run(["caelestia", "-v"], timeout=10)
    if p is None:
        results.append(Result(
            "caelestia CLI", FAIL, "`caelestia` command not found",
            "Without the CLI most Caelestia commands will not work.",
            steps=["Install caelestia-cli by following the Caelestia install guide:",
                 "https://github.com/caelestia-dots/caelestia",
                 "If it is installed, check that its folder is on your PATH:",
                 "$ which caelestia"],
        ))
    elif p.rc != 0:
        results.append(Result(
            "caelestia CLI", WARN, f"`caelestia -v` exited with code {p.rc}",
            "Run it by hand and look at the error.", detail=p.err or p.out,
        ))
    else:
        n = len(p.out.splitlines()) if p.out else 0
        # The first line of `caelestia -v` is only a heading, so do not show it as the result.
        results.append(Result("caelestia CLI", OK, f"`caelestia -v` ran fine ({n} lines of version info, "
                              "included in `caelestia-doctor report`)", detail=p.out))

    qs = run(["quickshell", "--version"]) or run(["qs", "--version"])
    if qs is None:
        results.append(Result("Quickshell", FAIL, "`quickshell` not found",
                              "The Caelestia shell runs on Quickshell.",
                              steps=["Install Quickshell with your package manager or AUR helper."]))
    else:
        results.append(Result("Quickshell", OK, qs.out.splitlines()[0] if qs.out else "installed",
                              detail=qs.out))

    hv = run(["hyprctl", "version"])
    if hv is None:
        results.append(Result("Hyprland", INFO, "`hyprctl` not found (not on a Hyprland system?)"))
    elif hv.rc != 0:
        results.append(Result(
            "Hyprland", INFO, "hyprctl could not reach Hyprland",
            "Run caelestia-doctor from inside a Hyprland session for full checks.",
        ))
    else:
        results.append(Result("Hyprland", OK, hv.out.splitlines()[0] if hv.out else "running",
                              detail=hv.out))

    if have("pacman"):
        found = []
        for pkg in PACKAGES:
            q = run(["pacman", "-Q", pkg])
            if q is not None and q.rc == 0:
                found.append(q.out)
        if found:
            results.append(Result("Packages", INFO, f"{len(found)} relevant package(s) installed",
                                  detail="\n".join(found)))
        else:
            results.append(Result("Packages", INFO, "no Caelestia packages found via pacman",
                                  "Fine if you installed from source."))
    return results
