"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys
import tarfile

from . import __version__
from .backup import list_backup, restore_backup
from .diagnostics import collect_runtime_logs
from .checks import ALL, arch
from .installer import install_optional_tools
from .packages import review_packages
from .repairs import apply_repair, undo_repair_backup
from .report import render_json, render_markdown, render_text
from .restore import restore_missing
from .shellcheck import check_command, check_command_file
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


def _repair(results: list[Result], color: bool, automatic: bool = False, dry_run: bool = False) -> int:
    if dry_run:
        print(render_text(results, color=color))
        candidates = [r for r in results if r.status in (FAIL, WARN) and r.repair is not None]
        if not candidates:
            print("Dry run: no safe file repairs are available.")
        else:
            print("Dry run only; no files were changed. Potential repairs:")
            for r in candidates:
                print(f"  - {r.name}: {r.repair.description}")
        return _exit_code(results)
    if automatic:
        current = results
        applied = 0
        while applied < 100:
            candidate = next((r for r in current if r.repair is not None), None)
            if candidate is None:
                break
            try:
                backup = apply_repair(candidate.repair)
            except (OSError, ValueError) as e:
                print(f"Could not auto-fix {candidate.name}: {e}")
                break
            print(f"Auto-fixed {candidate.name}. Backup: {short(backup)}")
            applied += 1
            current = run_all()
        if applied == 100:
            print("Stopped after 100 repairs; run the command again to continue.")
        if applied == 0:
            print("No deterministic safe repairs are available.")
        print("\nResults after auto-fix:")
        print(render_text(current, color=color))
        return _exit_code(current)

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
        description="Diagnose and repair common Arch/CachyOS, Hyprland and Caelestia problems. "
                    "`check`, `deep-check`, `logs`, `command-check`, `report` and every --dry-run only read. "
                    "`fix`, `restore`, `backup restore`, `packages`, `install` and `undo` change things only "
                    "after you confirm, and file edits are backed up first.",
    )
    ap.add_argument("--version", action="version", version=f"caelestia-doctor {__version__}")
    ap.add_argument("--no-color", action="store_true", help="plain output (also set by NO_COLOR)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check", help="run all checks and print the result (default)")
    dc = sub.add_parser("deep-check", help="run the slower pacman checksum/metadata integrity check")
    dc.add_argument("--full", action="store_true", help="also list every altered file, grouped by category")
    fp = sub.add_parser("fix", help="show safe repairs and apply the ones you select")
    fp.add_argument("--all", action="store_true", help="apply every deterministic safe repair without prompting")
    fp.add_argument("--dry-run", action="store_true", help="preview available repairs without changing files")
    restore = sub.add_parser("restore", help="review missing default Caelestia files from the official repository")
    restore.add_argument("--component", help="limit downloads to one default component (for example: hypr)")
    restore.add_argument("--dry-run", action="store_true", help="list missing files without asking or downloading")
    sub.add_parser("install", help="review and install the optional less pager from configured pacman repositories")
    packages = sub.add_parser("packages", help="audit Caelestia manifest packages and offer per-package installation")
    packages.add_argument("--component", help="limit the audit to one default component (for example: hypr)")
    packages.add_argument("--dry-run", action="store_true", help="list missing packages without offering installation")
    backup = sub.add_parser("backup", help="inspect or selectively restore a Caelestia backup archive")
    backup_actions = backup.add_subparsers(dest="backup_action", required=True)
    backup_list = backup_actions.add_parser("list", help="list supported files without extracting them")
    backup_list.add_argument("archive", help="path to a .tar, .tar.gz, or .tgz backup")
    backup_restore = backup_actions.add_parser("restore", help="restore selected files after per-file confirmation")
    backup_restore.add_argument("archive", help="path to a .tar, .tar.gz, or .tgz backup")
    backup_restore.add_argument("--dry-run", action="store_true", help="preview missing destinations without restoring")
    undo = sub.add_parser("undo", help="restore one caelestia-doctor file backup after confirmation")
    undo.add_argument("backup", help="backup file created by `caelestia-doctor fix`")
    logs = sub.add_parser("logs", help="collect recent Hyprland and Quickshell logs for diagnosis")
    logs.add_argument("-o", "--output", help="write a redacted Markdown log report to this path")
    command_check = sub.add_parser("command-check", help="parse pasted command text without executing it")
    command_source = command_check.add_mutually_exclusive_group(required=True)
    command_source.add_argument("--command", help="command text to parse; quote it for your current shell")
    command_source.add_argument("--file", help="path to a text file containing commands to parse")
    command_check.add_argument("--shell", choices=("fish", "bash"), default="fish")
    rp = sub.add_parser("report", help="print a Markdown report to paste into a GitHub issue")
    rp.add_argument("-o", "--output", help="write the report to this file instead of printing it")
    rp.add_argument("--format", choices=("markdown", "json"), default="markdown", help="report format")
    args = ap.parse_args(argv)

    color = sys.stdout.isatty() and not args.no_color and not os.environ.get("NO_COLOR")
    if args.cmd == "restore":
        restored, errors = restore_missing(args.component, dry_run=args.dry_run)
        if restored:
            updated = run_all()
            print("\nChecks after restore:")
            print(render_text(updated, color=color))
            if _exit_code(updated):
                return _exit_code(updated)
        return 1 if errors else 0

    if args.cmd == "install":
        code = install_optional_tools()
        if code == 0:
            updated = run_all()
            print("\nChecks after installation:")
            print(render_text(updated, color=color))
        return code

    if args.cmd == "deep-check":
        results = arch.run_deep_checks()
        print(render_text(results, color=color))
        if args.full:
            for r in results:
                if r.detail:
                    print(f"\n{r.name}: every file by category\n")
                    print(r.detail)
        return _exit_code(results)

    if args.cmd == "packages":
        installed, errors = review_packages(args.component, dry_run=args.dry_run)
        if installed:
            updated = run_all()
            print("\nChecks after package installation:")
            print(render_text(updated, color=color))
        return 1 if errors else 0

    if args.cmd == "backup":
        if args.backup_action == "list":
            try:
                entries = list_backup(args.archive)
            except (OSError, ValueError, tarfile.TarError) as exc:
                print(f"Could not safely inspect backup: {exc}", file=sys.stderr)
                return 1
            if not entries:
                print("No supported Hyprland/Caelestia files were found.")
            else:
                print(f"Found {len(entries)} supported file(s):")
                for item in entries:
                    print(f"{item.destination}\t{item.size} bytes\t(from {item.name})")
            return 0
        restored, errors = restore_backup(args.archive, dry_run=args.dry_run)
        if restored:
            updated = run_all()
            print("\nChecks after backup restore:")
            print(render_text(updated, color=color))
        return 1 if errors else 0

    if args.cmd == "undo":
        restored, _current_backup = undo_repair_backup(args.backup)
        if restored:
            updated = run_all()
            print("\nChecks after undo:")
            print(render_text(updated, color=color))
        return 0 if restored else 1

    if args.cmd == "logs":
        results = collect_runtime_logs()
        text = render_markdown(results)
        if args.output:
            print("This report contains recent compositor/shell log lines. Review it before sharing.")
            if not _interactive():
                print("A terminal is required to confirm saving log output; nothing was written.")
                return 2
            confirm = _ask(f"Write the redacted report to {args.output}? [y/N] ")
            if confirm not in ("y", "yes"):
                print("Cancelled; no report was written.")
                return 0
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            print(f"Report written to {args.output}")
        else:
            print(render_text(results, color=color))
            for result in results:
                if result.detail:
                    print(f"\n--- {result.name} ---\n{result.detail}")
            print("Review log details before sharing; logs may still contain private application data.")
        return _exit_code(results)

    if args.cmd == "command-check":
        results = check_command(args.command, args.shell) if args.command is not None else check_command_file(args.file, args.shell)
        print(render_text(results, color=color))
        return _exit_code(results)

    results = run_all()

    if args.cmd == "fix":
        if args.all and args.dry_run:
            print("Choose either --all or --dry-run, not both.", file=sys.stderr)
            return 2
        return _repair(results, color, automatic=args.all, dry_run=args.dry_run)
    if args.cmd == "report":
        text = render_json(results) if args.format == "json" else render_markdown(results)
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
