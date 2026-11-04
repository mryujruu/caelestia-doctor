"""Apply explicitly selected, safe repairs with a backup of each changed file."""

from __future__ import annotations

import shutil
import os
import re
import tempfile
import sys
from datetime import datetime
from pathlib import Path

from .utils import Repair, home


def backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.backup-{stamp}")
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.backup-{stamp}-{suffix}")
        suffix += 1
    return candidate


def apply_repair(repair: Repair) -> Path:
    """Back up the original file, apply the repair, and return the backup path."""
    if repair.expected is not None:
        current = repair.path.read_text(encoding="utf-8")
        if current != repair.expected:
            raise OSError("the file changed since the check; run caelestia-doctor again")
    backup = backup_path(repair.path)
    shutil.copy2(repair.path, backup)
    repair.apply()
    return backup


def undo_repair_backup(
    backup: str | Path,
    *,
    ask=input,
    say=print,
    is_tty: bool | None = None,
) -> tuple[bool, Path | None]:
    """Restore one doctor-created backup after confirmation, backing up current contents first."""
    backup_path_arg = Path(backup).expanduser()
    match = re.search(r"\.backup-\d{8}-\d{6}(?:-\d+)?$", backup_path_arg.name)
    if not match or not backup_path_arg.is_file() or backup_path_arg.is_symlink():
        say("This is not a recognized regular-file backup created by caelestia-doctor.")
        return False, None
    target = backup_path_arg.with_name(backup_path_arg.name[:match.start()])
    try:
        backup_path_arg.resolve().relative_to(home().resolve())
        target.resolve(strict=False).relative_to(home().resolve())
    except (OSError, ValueError):
        say("Refusing to restore a backup outside your home directory.")
        return False, None
    if target.is_symlink():
        say(f"Refusing to replace a symlink: {target}")
        return False, None
    tty = sys.stdin.isatty() if is_tty is None else is_tty
    if not tty:
        say("Undo requires an interactive terminal; no files were changed.")
        return False, None
    say(f"Backup: {backup_path_arg}")
    say(f"Restore to: {target}")
    try:
        answer = ask("Restore this backup? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        say("\nCancelled; no files were changed.")
        return False, None
    if answer not in ("y", "yes"):
        say("Cancelled; no files were changed.")
        return False, None

    current_backup: Path | None = None
    if target.exists():
        if not target.is_file():
            say("Target is not a regular file; refusing to replace it.")
            return False, None
        current_backup = backup_path(target)
        try:
            shutil.copy2(target, current_backup)
        except OSError as exc:
            say(f"Could not back up current contents: {exc}")
            return False, None
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.parent.resolve().relative_to(home().resolve())
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".undo", dir=target.parent)
        os.close(fd)
        try:
            shutil.copy2(backup_path_arg, temporary)
            os.replace(temporary, target)
        finally:
            try:
                os.unlink(temporary)
            except OSError:
                pass
    except (OSError, ValueError) as exc:
        say(f"Could not restore backup: {exc}")
        if current_backup:
            say(f"Current contents remain backed up at {current_backup}")
        return False, current_backup
    if current_backup:
        say(f"Previous current contents backed up to: {current_backup}")
    say(f"Restored: {target}")
    return True, current_backup
