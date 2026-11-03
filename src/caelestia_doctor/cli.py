"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .checks import ALL
from .repairs import apply_repair
from .report import render_markdown, render_text
from .utils import FAIL, WARN, Result, short


def run_all() -> list[Result]:
    results: list[Result] = []
    for name, fn in ALL:
        try:
            results.extend(fn())
        except Exception as e:  # a broken check must never hide the others
            results.append(Result(f"check:{name}", FAIL, f"this check crashed: {e!r}",
                                  "Please report this as a bug of caelestia-doctor."))
    return results


def _exit_code(results: list[Result]) -> int:
    return 1 if any(r.status == FAIL for r in results) else 0


def _interactive() -> bool:
    return sys.stdin.isatty()


def _ask(prompt: str) -> str | None:
    """Read an answer. Returns None if there is no input (Ctrl+D, Ctrl+C or a closed stdin)."""
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _parse_selection(answer: str, count: int) -> list[int] | None:
    """'a' / 'all' -> every repair, '1,3' -> those repairs. None if it makes no sense."""
    if answer in ("a", "all"):
        return list(range(count))
    try:
        numbers = [int(x) for x in answer.replace(" ", "").split(",") if x]
    except ValueError:
        return None
    if not numbers or any(n < 1 or n > count for n in numbers):
        return None
    return [n - 1 for n in dict.fromkeys(numbers)]


def _repair(results: list[Result], color: bool) -> int:
    print(render_text(results, color=color))
    code = _exit_code(results)
    candidates = [r for r in results if r.status in (FAIL, WARN) and r.repair is not None]
    if not candidates:
        print("No safe automatic repairs are available. Follow the suggestions above.")
        return code
    if not _interactive():
        print("`fix` asks questions, so it needs a terminal. Nothing was changed.")
        return 2

    print("Safe repairs available:")
    for i, r in enumerate(candidates, 1):
        print(f"  {i}. {r.name}: {r.repair.description}")
    answer = _ask("\nApply which? [a]ll, numbers like 1,3, or [n]one: ")
    if answer in (None, "", "n", "none"):
        print("No changes made.")
        return code
    picked = _parse_selection(answer, len(candidates))
    if picked is None:
        print("Invalid selection. No changes made.")
        return code
    chosen = [candidates[i] for i in picked]
    confirm = _ask(f"Apply {len(chosen)} repair(s)? Each file is backed up first. [y/N] ")
    if confirm not in ("y", "yes"):
        print("No changes made.")
        return code

    for r in chosen:
        try:
            backup = apply_repair(r.repair)
        except (OSError, ValueError) as e:
            print(f"Could not repair {r.name}: {e}")
        else:
            print(f"Repaired {r.name}. Backup: {short(backup)}")

    updated = run_all()
    print("\nResults after repair:")
    print(render_text(updated, color=color))
    return _exit_code(updated)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="caelestia-doctor",
        description="Diagnose common Caelestia problems. Checks never change anything; "
                    "`fix` applies only the safe repairs you select, with a backup of each file.",
    )
    ap.add_argument("--version", action="version", version=f"caelestia-doctor {__version__}")
    ap.add_argument("--no-color", action="store_true", help="plain output (also set by NO_COLOR)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check", help="run all checks and print the result (default)")
    sub.add_parser("fix", help="show safe repairs and apply the ones you select")
    rp = sub.add_parser("report", help="print a Markdown report to paste into a GitHub issue")
    rp.add_argument("-o", "--output", help="write the report to this file instead of printing it")
    args = ap.parse_args(argv)

    color = sys.stdout.isatty() and not args.no_color and not os.environ.get("NO_COLOR")
    results = run_all()

    if args.cmd == "fix":
        return _repair(results, color)
    if args.cmd == "report":
        text = render_markdown(results)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            print(f"Report written to {args.output}")
        else:
            print(text)
    else:
        print(render_text(results, color=color))
    return _exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
