"""Safely inspect and selectively restore Caelestia configuration tar backups."""

from __future__ import annotations

import os
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from .utils import config_dir, home, state_dir

MAX_FILES = 20_000
MAX_FILE_SIZE = 128 * 1024 * 1024
MAX_TOTAL_SIZE = 1024 * 1024 * 1024


@dataclass(frozen=True)
class BackupEntry:
    name: str
    destination: Path
    size: int
    mode: int


def _safe_destination(name: str) -> Path | None:
    """Map only known Caelestia config/state paths into this user's home."""
    path = PurePosixPath(name)
    if any(part == ".." for part in path.parts):
        return None
    parts = list(path.parts)
    # Tar usually strips the leading slash. Handle both forms without trusting
    # any archived home-directory name: map to the current user's XDG dirs.
    for i in range(len(parts) - 1):
        if parts[i:i + 2] == [".config", "hypr"]:
            rel = parts[i + 2:]
            return config_dir() / "hypr" / Path(*rel) if rel else config_dir() / "hypr"
        if parts[i:i + 2] == [".config", "caelestia"]:
            rel = parts[i + 2:]
            return config_dir() / "caelestia" / Path(*rel) if rel else config_dir() / "caelestia"
        if parts[i:i + 3] == [".local", "state", "caelestia"]:
            rel = parts[i + 3:]
            return state_dir() / "caelestia" / Path(*rel) if rel else state_dir() / "caelestia"
    # Also accept archives created with paths relative to the config roots.
    if parts and parts[0] in ("hypr", "caelestia"):
        root = config_dir() / parts[0]
        return root.joinpath(*parts[1:])
    return None


def list_backup(archive: str | Path) -> list[BackupEntry]:
    """Return supported regular files; reject unsafe, oversized, or ambiguous archives."""
    archive = Path(archive).expanduser()
    entries: list[BackupEntry] = []
    seen: set[Path] = set()
    total = 0
    with tarfile.open(archive, mode="r:*") as tar:
        for index, member in enumerate(tar):
            if index >= MAX_FILES:
                raise ValueError(f"archive contains more than {MAX_FILES} entries")
            if not member.isfile():
                continue
            destination = _safe_destination(member.name)
            if destination is None:
                continue
            if member.size < 0 or member.size > MAX_FILE_SIZE:
                raise ValueError(f"archive file is too large: {member.name}")
            total += member.size
            if total > MAX_TOTAL_SIZE:
                raise ValueError("supported files exceed the 1 GiB safety limit")
            resolved_home = home().resolve()
            try:
                destination.resolve(strict=False).relative_to(resolved_home)
            except (OSError, ValueError) as exc:
                raise ValueError(f"unsafe destination in archive: {member.name}") from exc
            if destination in seen:
                raise ValueError(f"multiple archive entries map to the same path: {destination}")
            seen.add(destination)
            entries.append(BackupEntry(member.name, destination, member.size, member.mode & 0o777))
    return entries


def _write_exclusive(archive: str | Path, entry: BackupEntry) -> None:
    archive_path = Path(archive).expanduser()
    with tarfile.open(archive_path, mode="r:*") as tar:
        member = tar.getmember(entry.name)
        source = tar.extractfile(member)
        if source is None:
            raise ValueError(f"could not read archived file: {entry.name}")
        target = entry.destination
        try:
            target.parent.resolve(strict=False).relative_to(home().resolve())
        except (OSError, ValueError) as exc:
            raise ValueError("restore destination escaped the home directory") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.parent.resolve().relative_to(home().resolve())
        except (OSError, ValueError) as exc:
            raise ValueError("restore destination escaped the home directory") from exc
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, entry.mode or 0o644)
        try:
            with os.fdopen(fd, "wb") as out, source:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            os.chmod(target, entry.mode or 0o644)
        except BaseException:
            try:
                target.unlink()
            except OSError:
                pass
            raise


def restore_backup(
    archive: str | Path,
    *,
    dry_run: bool = False,
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
) -> tuple[int, int]:
    """Preview and confirm each selected archive file, never overwriting a path."""
    try:
        entries = list_backup(archive)
    except (OSError, tarfile.TarError, ValueError) as exc:
        say(f"Could not safely inspect backup: {exc}")
        return 0, 1
    if not entries:
        say("No supported Hyprland/Caelestia files were found in this backup.")
        return 0, 0
    if dry_run:
        for entry in entries:
            state = "already exists; would be left untouched" if entry.destination.exists() or entry.destination.is_symlink() else "would offer restore"
            say(f"{state}: {entry.name} -> {entry.destination}")
        say("Dry run only; no files were restored.")
        return 0, 0
    say(f"Found {len(entries)} supported file(s) in {Path(archive).expanduser()}")
    restored = errors = 0
    for entry in entries:
        if entry.destination.exists() or entry.destination.is_symlink():
            say(f"Already exists; leaving untouched: {entry.destination}")
            continue
        say(f"\nArchive: {entry.name}")
        say(f"Restore to: {entry.destination} ({entry.size} bytes)")
        try:
            answer = ask("Restore this file? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            say("\nCancelled; no further files were restored.")
            break
        if answer not in ("y", "yes"):
            say("Skipped.")
            continue
        try:
            _write_exclusive(archive, entry)
        except FileExistsError:
            say(f"Appeared during confirmation; left untouched: {entry.destination}")
        except (OSError, tarfile.TarError, ValueError) as exc:
            errors += 1
            say(f"Restore failed: {exc}")
        else:
            restored += 1
            say(f"Restored: {entry.destination}")
    say(f"\nRestored {restored} file(s); {errors} error(s).")
    return restored, errors
