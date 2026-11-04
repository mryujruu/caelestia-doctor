import subprocess

from caelestia_doctor import packages


def test_catalog_filters_non_default_and_unsafe_package_names():
    manifest = {"components": [
        {"name": "hypr", "default": True, "packages": ["hyprland", "local:packages/foo", "--bad"]},
        {"name": "optional", "default": False, "packages": ["firefox"]},
    ]}
    assert packages.catalog_from_manifest(manifest) == [("hypr", "hyprland")]


def test_find_missing_packages_classifies_arch_and_aur():
    catalog = [("hypr", "hyprland"), ("shell", "caelestia-shell"), ("shell", "fish")]
    missing = packages.find_missing_packages(
        catalog,
        query=lambda _names: ({"fish"}, {"hyprland", "fish"}),
    )
    assert [(x.name, x.source) for x in missing] == [
        ("hyprland", "arch"), ("caelestia-shell", "unlisted")
    ]


def test_review_packages_only_installs_after_per_package_yes(monkeypatch):
    monkeypatch.setattr(packages, "upstream_package_catalog", lambda *_a, **_k: ("abc123", [("hypr", "hyprland")]))
    query = lambda _names: (set(), {"hyprland"})
    calls = []
    rc = packages.review_packages(
        ask=lambda _p: "n", say=lambda _s: None, is_tty=True,
        package_query=query, execute=lambda *a, **k: calls.append(a),
    )
    assert rc == (0, 0)
    assert calls == []


def test_review_packages_installs_and_verifies_after_yes(monkeypatch):
    monkeypatch.setattr(packages, "upstream_package_catalog", lambda *_a, **_k: ("abc123", [("hypr", "hyprland")]))
    calls = []

    def execute(cmd, check=False):
        calls.append((cmd, check))
        return subprocess.CompletedProcess(cmd, 0)

    rc = packages.review_packages(
        ask=lambda _p: "y", say=lambda _s: None, is_tty=True,
        package_query=lambda _names: (set(), {"hyprland"}),
        verify_installed=lambda _name: True, execute=execute,
    )
    assert rc == (1, 0)
    assert calls == [(["sudo", "pacman", "-S", "--needed", "hyprland"], False)]


def test_package_dry_run_never_prompts_or_installs(monkeypatch):
    monkeypatch.setattr(packages, "upstream_package_catalog", lambda *_a, **_k: ("abc123", [("hypr", "hyprland")]))
    calls = []
    result = packages.review_packages(
        dry_run=True, ask=lambda _p: calls.append("asked"), say=lambda _s: None,
        package_query=lambda _names: (set(), {"hyprland"}),
        execute=lambda *a, **k: calls.append("executed"),
    )
    assert result == (0, 0)
    assert calls == []
