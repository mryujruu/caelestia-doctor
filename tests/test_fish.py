from caelestia_doctor.checks import fish as check
from caelestia_doctor.utils import FAIL, INFO, OK, WARN, Proc


def test_fish_config_syntax_error_is_reported(tmp_path, monkeypatch):
    fish_dir = tmp_path / "fish"
    fish_dir.mkdir()
    config = fish_dir / "config.fish"
    config.write_text('backup="archive.tar.gz"\n')
    monkeypatch.setattr(check, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(check, "have", lambda cmd: cmd == "fish")
    monkeypatch.setattr(check, "run", lambda *args, **kwargs: Proc(127, "", "Unsupported use of '='."))

    result = next(r for r in check.run_checks() if r.name == "Fish syntax: config.fish")
    assert result.status == FAIL
    assert "Unsupported use" in result.detail
    assert "$ fish -n" in result.steps[1]


def test_missing_less_is_warned_and_healthy_less_is_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(check, "have", lambda cmd: False)
    missing = next(r for r in check.run_checks() if r.name == "Terminal pager: less")
    assert missing.status == WARN
    monkeypatch.setattr(check, "have", lambda cmd: cmd == "less")
    present = next(r for r in check.run_checks() if r.name == "Terminal pager: less")
    assert present.status == OK


def test_existing_fish_config_without_fish_is_not_misdiagnosed(tmp_path, monkeypatch):
    fish_dir = tmp_path / "fish"
    fish_dir.mkdir()
    (fish_dir / "config.fish").write_text("set x y\n")
    monkeypatch.setattr(check, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(check, "have", lambda _cmd: False)
    result = next(r for r in check.run_checks() if r.name == "Fish configuration")
    assert result.status == INFO
