import hashlib
import json
from pathlib import Path

import pytest

from caelestia_doctor import restore
from caelestia_doctor.utils import Proc


def git_blob_sha(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def test_catalog_maps_only_default_files_under_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    payload = b"return {}\n"
    tree = {
        "truncated": False,
        "tree": [
            {"path": "hypr/hyprland.lua", "type": "blob", "mode": "100644", "sha": git_blob_sha(payload)},
            {"path": "hypr/modules/input.lua", "type": "blob", "mode": "100755", "sha": git_blob_sha(payload)},
            {"path": "../outside", "type": "blob", "mode": "100644", "sha": "bad"},
        ],
    }
    manifest = '''
[[components]]
name = "hypr"
default = true
[[components.entries]]
src = "hypr"
dest = "$XDG_CONFIG_HOME/hypr"
[[components]]
name = "optional"
default = false
[[components.entries]]
src = "hyprland.lua"
dest = "$HOME/.config/optional.lua"
'''
    responses = {
        f"{restore.API}/commits/main": json.dumps({"sha": "abc123"}).encode(),
        f"{restore.RAW}/abc123/manifest.toml": manifest.encode(),
        f"{restore.API}/git/trees/abc123?recursive=1": json.dumps(tree).encode(),
    }
    monkeypatch.setattr(restore, "_request", lambda url: responses[url])

    revision, files = restore.upstream_files()

    assert revision == "abc123"
    assert {f.target for f in files} == {
        tmp_path / ".config/hypr/hyprland.lua",
        tmp_path / ".config/hypr/modules/input.lua",
    }
    assert all(f.target.is_relative_to(tmp_path) for f in files)


def test_restore_prompts_and_downloads_with_hash_check(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    data = b"hello from official Caelestia\n"
    item = restore.UpstreamFile(
        component="hypr",
        source="hypr/hyprland.lua",
        target=tmp_path / ".config/hypr/hyprland.lua",
        sha=git_blob_sha(data),
        mode=0o644,
        revision="abc123",
    )
    monkeypatch.setattr(restore, "upstream_files", lambda _component: ("abc123", [item]))
    prompts = []
    output = []

    restored, errors = restore.restore_missing(
        "hypr",
        ask=lambda prompt: prompts.append(prompt) or "y",
        say=output.append,
        fetch=lambda _url: data,
    )

    assert (restored, errors) == (1, 0)
    assert prompts and "[y/N]" in prompts[0]
    assert item.target.read_bytes() == data
    assert "Downloaded to" in "\n".join(output)


def test_restore_skips_on_no_and_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    data = b"official file"
    target = tmp_path / ".config/hypr/hyprland.lua"
    target.parent.mkdir(parents=True)
    target.write_text("my custom config")
    item = restore.UpstreamFile("hypr", "hypr/hyprland.lua", target, git_blob_sha(data), 0o644, "abc123")
    monkeypatch.setattr(restore, "upstream_files", lambda _component: ("abc123", [item]))

    restored, errors = restore.restore_missing(
        "hypr", ask=lambda _prompt: "y", say=lambda _message: None, fetch=lambda _url: data
    )

    assert (restored, errors) == (0, 0)
    assert target.read_text() == "my custom config"


def test_bad_upstream_hash_does_not_create_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    item = restore.UpstreamFile("hypr", "hypr/hyprland.lua", tmp_path / ".config/hypr/hyprland.lua", "wrong", 0o644, "abc123")
    with pytest.raises(ValueError, match="integrity check failed"):
        restore._download(item, lambda _url: b"tampered")
    assert not item.target.exists()


def test_old_hyprland_version_skips_incompatible_lua_defaults(monkeypatch):
    data = b"config"
    item = restore.UpstreamFile(
        "hypr", "hypr/hyprland.lua", Path("/home/test/.config/hypr/hyprland.lua"),
        git_blob_sha(data), 0o644, "abc123"
    )
    monkeypatch.setattr(restore, "upstream_files", lambda _component: ("abc123", [item]))
    monkeypatch.setattr(restore, "_installed_hyprland_version", lambda: (0, 54))
    output = []

    restored, errors = restore.restore_missing(
        "hypr", ask=lambda _prompt: pytest.fail("must not prompt for incompatible Lua files"), say=output.append
    )

    assert (restored, errors) == (0, 0)
    assert "skipped" in "\n".join(output)


def test_empty_fish_hook_is_created_only_after_yes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    target = tmp_path / ".config/caelestia/user-config.fish"

    assert restore._offer_empty_user_config(lambda _prompt: "n", lambda _message: None) == 0
    assert not target.exists()
    assert restore._offer_empty_user_config(lambda _prompt: "y", lambda _message: None) == 1
    assert target.read_bytes() == b""


def test_default_scheme_initialization_runs_official_cli_only_after_yes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".local/state/caelestia/scheme.json"
    calls = []

    def fake_run(command, timeout):
        calls.append(command)
        target.parent.mkdir(parents=True)
        target.write_text('{"name":"caelestia"}')
        return Proc(0, "", "")

    monkeypatch.setattr(restore, "run", fake_run)
    assert restore._offer_scheme_initialization(lambda _prompt: "n", lambda _message: None) == (0, 0)
    assert not calls
    assert restore._offer_scheme_initialization(lambda _prompt: "y", lambda _message: None) == (1, 0)
    assert calls == [["caelestia", "scheme", "set", "-n", "caelestia"]]


def test_restore_dry_run_lists_paths_without_prompt_or_download(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    item = restore.UpstreamFile(
        "hypr", "hypr/hyprland.conf", tmp_path / ".config/hypr/hyprland.conf",
        "not-used-for-dry-run", 0o644, "abc123"
    )
    monkeypatch.setattr(restore, "upstream_files", lambda _component: ("abc123", [item]))
    output = []
    restored, errors = restore.restore_missing(
        "hypr", dry_run=True,
        ask=lambda _prompt: pytest.fail("dry run must not prompt"),
        say=output.append,
        fetch=lambda _url: pytest.fail("dry run must not download"),
    )
    assert (restored, errors) == (0, 0)
    assert "Would offer" in "\n".join(output)
    assert not item.target.exists()
