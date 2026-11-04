"""Optional, read-only collection of recent compositor and shell logs."""

from __future__ import annotations

import re

from .report import redact
from .utils import INFO, WARN, Result, run


def _log_result(name: str, command: list[str], timeout: int = 10) -> Result:
    proc = run(command, timeout=timeout)
    if proc is None:
        return Result(name, INFO, f"could not collect log; command not found: {command[0]}")
    if proc.rc != 0:
        return Result(name, INFO, f"could not collect log (exit {proc.rc})", detail=redact(proc.err or proc.out))
    lines = (proc.out or "").splitlines()
    tail = "\n".join(lines[-160:])
    severe = [line for line in lines[-160:] if re.search(r"\b(error|critical|fatal)\b", line, re.IGNORECASE)]
    status = WARN if severe else INFO
    message = f"collected {min(len(lines), 160)} recent line(s)"
    if severe:
        message += f"; {len(severe)} line(s) contain error-like terms (review context; may be historical)"
    return Result(name, status, message, detail=redact(tail))


def collect_runtime_logs() -> list[Result]:
    """Read recent logs only on request; do not upload or alter anything."""
    return [
        _log_result("Hyprland recent log", ["hyprctl", "rollinglog"]),
        _log_result("Quickshell Caelestia log", ["qs", "log", "-c", "caelestia", "--tail", "200", "--no-color"]),
    ]
