"""Check Fish configuration syntax and the optional `less` terminal pager."""

from __future__ import annotations

from ..utils import FAIL, INFO, OK, WARN, Result, config_dir, have, run, short


def run_checks() -> list[Result]:
    results: list[Result] = []
    fish_files = [
        config_dir() / "fish" / "config.fish",
        config_dir() / "caelestia" / "user-config.fish",
    ]
    existing = [path for path in fish_files if path.is_file()]
    if not existing:
        results.append(Result("Fish configuration", INFO, "no checked Fish config files are present"))
    elif not have("fish"):
        results.append(Result(
            "Fish configuration",
            INFO,
            "Fish is unavailable; could not run a syntax check",
            "The tool never executes these files. Install Fish or run the check on a host where it is available.",
        ))
    else:
        for path in existing:
            proc = run(["fish", "-n", str(path)], timeout=10)
            if proc is None:
                results.append(Result("Fish configuration", INFO, "Fish disappeared before the syntax check"))
            elif proc.rc == 124:
                results.append(Result(f"Fish syntax: {path.name}", INFO, "syntax check timed out"))
            elif proc.rc != 0:
                results.append(Result(
                    f"Fish syntax: {path.name}",
                    FAIL,
                    f"{short(path)} has a Fish syntax error",
                    "Review the reported line and correct it manually; arbitrary shell code is not rewritten automatically.",
                    detail=proc.err or proc.out,
                    steps=["Check syntax without running the file:", f"$ fish -n {short(path)}"],
                ))
            else:
                results.append(Result(f"Fish syntax: {path.name}", OK, f"{short(path)} parses successfully"))

    if have("less"):
        results.append(Result("Terminal pager: less", OK, "less is installed"))
    else:
        results.append(Result(
            "Terminal pager: less",
            WARN,
            "less is not installed; commands piped to `less` will fail",
            "It is optional. Run `caelestia-doctor install` to review and install it from your configured pacman repositories after confirmation, or use `head`/`cat`.",
            steps=["Install the optional pager after reviewing the package:", "$ caelestia-doctor install"],
        ))
    return results
