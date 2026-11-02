"""Command line entry point."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .checks import ALL
from .report import render_markdown, render_text
from .utils import FAIL, Result


def run_all() -> list[Result]:
    results: list[Result] = []
    for name, fn in ALL:
        try:
            results.extend(fn())
        except Exception as e:  # a broken check must never hide the others
            results.append(Result(f"check:{name}", FAIL, f"this check crashed: {e!r}",
                                  "Please report this as a bug of caelestia-doctor."))
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="caelestia-doctor",
        description="Diagnose common Caelestia problems. Read-only: it never changes your files.",
    )
    ap.add_argument("--version", action="version", version=f"caelestia-doctor {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check", help="run all checks and print the result (default)")
    rp = sub.add_parser("report", help="print a Markdown report to paste into a GitHub issue")
    rp.add_argument("-o", "--output", help="write the report to this file instead of printing it")
    args = ap.parse_args(argv)

    results = run_all()

    if args.cmd == "report":
        text = render_markdown(results)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            print(f"Report written to {args.output}")
        else:
            print(text)
    else:
        print(render_text(results, color=sys.stdout.isatty()))

    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
