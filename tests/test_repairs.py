import os
import stat

import pytest

from caelestia_doctor.repairs import apply_repair, undo_repair_backup
from caelestia_doctor.utils import Repair, write_text_atomic


def test_apply_repair_backs_up_original_before_editing(tmp_path):
    path = tmp_path / "shell.json"
    path.write_text("")
    repair = Repair(path, "write empty object", lambda: path.write_text("{}\n"))

    backup = apply_repair(repair)

    assert path.read_text() == "{}\n"
    assert backup.read_text() == ""
    assert backup.parent == path.parent


def test_backup_path_does_not_overwrite_existing_backup(tmp_path):
    path = tmp_path / "shell.json"
    path.write_text("")
    repair = Repair(path, "write empty object", lambda: path.write_text("{}\n"))
    first_backup = apply_repair(repair)
    path.write_text("")

    second_backup = apply_repair(repair)

    assert first_backup != second_backup
    assert first_backup.read_text() == ""
    assert second_backup.read_text() == ""


def test_undo_restores_backup_and_backs_up_current_contents(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".config" / "caelestia" / "shell.json"
    target.parent.mkdir(parents=True)
    backup = target.with_name("shell.json.backup-20261103-123456")
    backup.write_text("original")
    target.write_text("current")
    restored, current_backup = undo_repair_backup(backup, ask=lambda _p: "y", is_tty=True, say=lambda _s: None)
    assert restored
    assert target.read_text() == "original"
    assert current_backup is not None and current_backup.read_text() == "current"


def test_undo_declined_leaves_both_files_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "settings.json"
    backup = tmp_path / "settings.json.backup-20261103-123456"
    target.write_text("current")
    backup.write_text("old")
    restored, new_backup = undo_repair_backup(backup, ask=lambda _p: "n", is_tty=True, say=lambda _s: None)
    assert not restored and new_backup is None
    assert target.read_text() == "current"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are not preserved on Windows")
def test_atomic_write_replaces_content_and_keeps_permissions(tmp_path):
    path = tmp_path / "f.json"
    path.write_text("old")
    os.chmod(path, 0o640)
    write_text_atomic(path, "new")
    assert path.read_text() == "new"
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert [p.name for p in tmp_path.iterdir()] == ["f.json"]  # no temp file left behind
