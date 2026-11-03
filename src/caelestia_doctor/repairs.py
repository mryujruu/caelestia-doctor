"""Apply explicitly selected, safe repairs with a backup of each changed file."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .utils import Repair


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
    backup = backup_path(repair.path)
    shutil.copy2(repair.path, backup)
    repair.apply()
    return backup
