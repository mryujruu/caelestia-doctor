"""User-approved installation of an optional tool from pacman repositories."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable


def install_optional_tools(
    *,
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
    is_tty: bool | None = None,
    execute: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """Offer to install only `less`, using pacman and an explicit user confirmation."""
    if shutil.which("less"):
        say("less is already installed; nothing to do.")
        return 0
    if not shutil.which("pacman"):
        say("pacman was not found. This installer supports Arch-based systems such as Arch Linux and CachyOS.")
        return 1
    tty = sys.stdin.isatty() and sys.stdout.isatty() if is_tty is None else is_tty
    if not tty:
        say("Installing a package requires an interactive terminal; nothing was changed.")
        say("Run `caelestia-doctor install` from your terminal.")
        return 2

    say("Missing optional tool: less (package: less; source: configured pacman repositories).")
    say("This will run: sudo pacman -S --needed less")
    try:
        answer = ask("Install less now? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        say("\nCancelled. Nothing was installed.")
        return 0
    if answer not in ("y", "yes"):
        say("Skipped. Nothing was installed.")
        return 0

    try:
        result = execute(["sudo", "pacman", "-S", "--needed", "less"], check=False)
    except OSError as exc:
        say(f"Could not start pacman: {exc}")
        return 1
    if result.returncode != 0:
        say(f"pacman did not install less (exit {result.returncode}). No files were changed by this tool directly.")
        return 1
    if not shutil.which("less"):
        say("pacman finished, but `less` is still not on PATH. Check the package output and PATH.")
        return 1
    say("Installed and verified: less is now available on PATH.")
    return 0
