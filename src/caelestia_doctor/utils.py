"""Small helpers shared by every check. Nothing in here may raise on missing files/commands."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

OK, INFO, WARN, FAIL = "OK", "INFO", "WARN", "FAIL"


@dataclass
class Repair:
    """A safe, deterministic repair for one diagnostic. `apply` edits `path` in place."""

    path: Path
    description: str
    apply: Callable[[], None]


@dataclass
class Result:
    """One line of the report."""

    name: str
    status: str  # OK / INFO / WARN / FAIL
    message: str
    hint: str = ""
    detail: str = ""  # raw command output etc., only shown in `report`
    steps: list[str] = field(default_factory=list)  # "$ command" lines are commands, others are notes
    repair: Repair | None = None  # set only when the tool can fix it safely by itself


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


def short(path) -> str:
    """Show a path with ~ instead of the home directory."""
    h = str(home())
    t = str(path)
    return "~" + t[len(h):] if h != "/" and t.startswith(h) else t


def write_text_atomic(path: Path, text: str) -> None:
    """Write a file so that it is either fully replaced or left untouched."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            shutil.copymode(path, tmp)
        except OSError:
            pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
