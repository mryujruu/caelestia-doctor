import io
import tarfile

from caelestia_doctor import backup


def make_tar(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))


def test_backup_lists_known_config_files_and_maps_to_current_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    archive = tmp_path / "backup.tar.gz"
    make_tar(archive, [("home/olduser/.config/hypr/hyprland.lua", b"return {}\n"),
                       ("home/olduser/Documents/private.txt", b"ignore")])
    entries = backup.list_backup(archive)
    assert len(entries) == 1
    assert entries[0].destination == tmp_path / ".config" / "hypr" / "hyprland.lua"


def test_backup_restore_prompts_and_writes_only_after_yes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    archive = tmp_path / "backup.tar.gz"
    make_tar(archive, [("home/olduser/.config/caelestia/shell.json", b"{}\n")])
    prompts = []
    count, errors = backup.restore_backup(archive, ask=lambda prompt: prompts.append(prompt) or "y", say=lambda _: None)
    target = tmp_path / ".config" / "caelestia" / "shell.json"
    assert (count, errors) == (1, 0)
    assert target.read_bytes() == b"{}\n"
    assert len(prompts) == 1


def test_backup_restore_never_overwrites_existing_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".config" / "hypr" / "hyprland.lua"
    target.parent.mkdir(parents=True)
    target.write_text("custom")
    archive = tmp_path / "backup.tar.gz"
    make_tar(archive, [("home/olduser/.config/hypr/hyprland.lua", b"backup")])
    count, errors = backup.restore_backup(archive, ask=lambda _: "y", say=lambda _: None)
    assert (count, errors) == (0, 0)
    assert target.read_text() == "custom"


def test_backup_rejects_duplicate_destinations(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    archive = tmp_path / "backup.tar.gz"
    make_tar(archive, [("home/a/.config/hypr/x.lua", b"one"), ("home/b/.config/hypr/x.lua", b"two")])
    try:
        backup.list_backup(archive)
    except ValueError as exc:
        assert "same path" in str(exc)
    else:
        raise AssertionError("duplicate destinations must be rejected")


def test_backup_dry_run_never_asks_or_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    archive = tmp_path / "backup.tar.gz"
    make_tar(archive, [("home/a/.config/hypr/config.lua", b"return {}")])
    calls = []
    count, errors = backup.restore_backup(archive, dry_run=True,
                                          ask=lambda _p: calls.append("asked"), say=lambda _s: None)
    assert (count, errors) == (0, 0)
    assert calls == []
    assert not (tmp_path / ".config" / "hypr" / "config.lua").exists()
