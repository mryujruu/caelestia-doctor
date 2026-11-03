import os
import stat

from caelestia_doctor.repairs import apply_repair
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


def test_atomic_write_replaces_content_and_keeps_permissions(tmp_path):
    path = tmp_path / "f.json"
    path.write_text("old")
    os.chmod(path, 0o640)
    write_text_atomic(path, "new")
    assert path.read_text() == "new"
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert [p.name for p in tmp_path.iterdir()] == ["f.json"]  # no temp file left behind
