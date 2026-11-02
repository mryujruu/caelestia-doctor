"""Small helpers shared by every check. Nothing in here may raise on missing files/commands."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

OK, INFO, WARN, FAIL = "OK", "INFO", "WARN", "FAIL"


@dataclass
class Result:
    """One line of the report."""

    name: str
    status: str  # OK / INFO / WARN / FAIL
    message: str
    hint: str = ""
    detail: str = ""  # raw command output etc., only shown in `report`


@dataclass
class Proc:
    rc: int
    out: str
    err: str


def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or home() / ".config")


def state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or home() / ".local" / "state")


def run(cmd: list[str], timeout: float = 5.0) -> Proc | None:
    """Run a command. Returns None if the program does not exist."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return Proc(124, "", "timed out")
    except OSError as e:
        return Proc(126, "", str(e))
    return Proc(p.returncode, p.stdout.strip(), p.stderr.strip())


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))
