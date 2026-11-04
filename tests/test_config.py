import json
import os

import pytest

from caelestia_doctor.checks import config, hyprland, state
from caelestia_doctor.utils import FAIL, OK, WARN


def setup_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / ".local" / "state"))
    (tmp_path / ".config" / "caelestia").mkdir(parents=True)
    return tmp_path / ".config" / "caelestia"


def statuses(results):
    return [r.status for r in results]


def test_missing_shell_json_is_not_an_error(tmp_path, monkeypatch):
    setup_home(tmp_path, monkeypatch)
    assert FAIL not in statuses(config.run_checks())


def test_invalid_json_is_reported_with_position(tmp_path, monkeypatch):
    base = setup_home(tmp_path, monkeypatch)
    (base / "shell.json").write_text('{"a": 1,}')
    res = config.run_checks()
    assert res[0].status == FAIL and "line 1" in res[0].message


def test_duplicate_keys_warn(tmp_path, monkeypatch):
    base = setup_home(tmp_path, monkeypatch)
    (base / "shell.json").write_text('{"paths": {}, "paths": {}}')
    assert WARN in statuses(config.run_checks())


def test_missing_path_warns_but_builtin_assets_are_fine(tmp_path, monkeypatch):
    base = setup_home(tmp_path, monkeypatch)
    cfg = {"paths": {"mediaGif": "~/nope.gif", "sessionGif": "root:/assets/x.gif"}}
    (base / "shell.json").write_text(json.dumps(cfg))
    res = config.run_checks()
    warns = [r for r in res if r.status == WARN]
    assert len(warns) == 1 and "mediaGif" in warns[0].name


def test_arabic_layout_code_is_ara_not_ar():
    codes = {"us", "ara", "de"}
    found = hyprland.find_layouts_in_text('hl.config({ input = { kb_layout = "us,ar", kb_options = "x" } })')
    assert found == [["us", "ar"]]
    assert [c for c in found[0] if c not in codes] == ["ar"]


def test_legacy_conf_syntax_is_parsed():
    assert hyprland.find_layouts_in_text("    kb_layout = us,eg\n    kb_options = grp:x") == [["us", "eg"]]


def test_xkb_list_parser(tmp_path):
    f = tmp_path / "base.lst"
    f.write_text("! model\n  pc105  PC\n\n! layout\n  us   English (US)\n  ara  Arabic\n\n! variant\n  x  y\n")
    assert hyprland.valid_layouts(f) == {"us", "ara"}


def test_state_dir_missing_warns(tmp_path, monkeypatch):
    setup_home(tmp_path, monkeypatch)
    assert state.run_checks()[0].status == WARN


def test_state_files_present_ok(tmp_path, monkeypatch):
    setup_home(tmp_path, monkeypatch)
    d = tmp_path / ".local" / "state" / "caelestia"
    (d / "wallpaper").mkdir(parents=True)
    (d / "scheme.json").write_text("{}")
    img = tmp_path / "w.png"
    img.write_text("x")
    (d / "wallpaper" / "path.txt").write_text(str(img))
    assert all(r.status == OK for r in state.run_checks())


def test_empty_json_offers_deterministic_repair(tmp_path, monkeypatch):
    base = setup_home(tmp_path, monkeypatch)
    path = base / "shell.json"
    path.write_text("")

    result = config.run_checks()[0]

    assert result.repair is not None
    assert result.repair.path == path
    assert result.repair.description


@pytest.mark.skipif(os.name == "nt", reason="Windows filesystems are usually case-insensitive")
def test_wrong_case_path_is_detected_and_repaired(tmp_path, monkeypatch):
    base = setup_home(tmp_path, monkeypatch)
    (tmp_path / "Pictures" / "Wallpapers").mkdir(parents=True)
    (tmp_path / "Pictures" / "Wallpapers" / "x.gif").write_text("gif")
    cfg = base / "shell.json"
    cfg.write_text('{\n  "paths": {\n    "mediaGif": "~/Pictures/wallpapers/x.gif"\n  },\n  "keep": 1\n}\n')

    warn = [r for r in config.run_checks() if r.status == WARN][0]
    assert "Wallpapers" in " ".join(warn.steps) and warn.repair is not None

    from caelestia_doctor.repairs import apply_repair
    backup = apply_repair(warn.repair)

    data = json.loads(cfg.read_text())
    assert data["paths"]["mediaGif"] == "~/Pictures/Wallpapers/x.gif" and data["keep"] == 1
    assert "wallpapers" in backup.read_text()  # the backup is the original
    assert not [r for r in config.run_checks() if r.status == WARN]  # and now it is clean


def test_no_repair_when_nothing_matches(tmp_path, monkeypatch):
    base = setup_home(tmp_path, monkeypatch)
    (base / "shell.json").write_text('{"paths": {"mediaGif": "~/nowhere/x.gif"}}')
    warn = [r for r in config.run_checks() if r.status == WARN][0]
    assert warn.repair is None


def test_repair_keeps_json_valid_even_for_odd_values(tmp_path):
    cfg = tmp_path / "shell.json"
    text = '{"paths": {"a": "/tmp/xx"}}'
    cfg.write_text(text)
    repair = config.make_path_repair(cfg, text, "a", "/tmp/xx", 'bad"quote\\')
    repair.apply()  # json.dumps escapes the value, so the result is still valid JSON
    assert json.loads(cfg.read_text())["paths"]["a"] == 'bad"quote\\'
