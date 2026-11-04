from caelestia_doctor.checks import hyprland as h
from caelestia_doctor.utils import WARN


def test_arabic_suggestion_for_ar():
    assert h.suggest_layouts("ar", {"us", "ara", "arm", "de"}) == ["ara", "arm"]


def test_typo_suggestion():
    assert "de" in h.suggest_layouts("dee", {"us", "de", "fr"})


def test_version_parsing_and_lua_rule():
    assert h.parse_version("Hyprland 0.56.2 built from branch v0.56.2") == (0, 56)
    assert h.lua_is_used((0, 56)) is True
    assert h.lua_is_used((0, 54)) is False
    assert h.lua_is_used(None) is None
    assert h.parse_version("nothing here") is None


def test_layout_names_have_descriptions(tmp_path):
    f = tmp_path / "base.lst"
    f.write_text("! layout\n  us   English (US)\n  ara  Arabic\n\n! variant\n  x  y\n")
    assert h.layout_names(f) == {"us": "English (US)", "ara": "Arabic"}


def test_missing_hyprland_config_is_a_warning_with_restore_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(h, "run", lambda _command: None)
    monkeypatch.setattr(h, "layout_names", lambda: None)
    monkeypatch.setattr(h, "have", lambda _command: False)

    results = h.run_checks()

    config = next(r for r in results if r.name == "Hyprland config")
    assert config.status == WARN
    assert any("restore --component hypr" in step for step in config.steps)
