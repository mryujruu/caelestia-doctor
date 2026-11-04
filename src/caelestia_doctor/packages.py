"""Audit Caelestia manifest packages and offer explicit per-package installs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass

from .restore import API, RAW, _request
from .utils import run

PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._+-]*$")


@dataclass(frozen=True)
class PackageNeed:
    component: str
    name: str
    source: str  # "arch" means found in any enabled pacman repository; otherwise unlisted/AUR


def catalog_from_manifest(manifest: dict, component_filter: str | None = None) -> list[tuple[str, str]]:
    """Collect validated package names from the manifest's default components."""
    pairs: list[tuple[str, str]] = []
    for component in manifest.get("components", []):
        name = component.get("name", "unnamed")
        if not component.get("default", False) or (component_filter and name != component_filter):
            continue
        packages = component.get("packages", [])
        if not isinstance(packages, list):
            continue
        for package in packages:
            if not isinstance(package, str) or package.startswith("local:"):
                continue
            if PACKAGE_RE.fullmatch(package):
                pairs.append((name, package))
    return list(dict.fromkeys(pairs))


def upstream_package_catalog(
    component_filter: str | None = None,
    *,
    fetch: Callable[[str], bytes] = _request,
) -> tuple[str, list[tuple[str, str]]]:
    commit = json.loads(fetch(f"{API}/commits/main"))
    revision = commit["sha"]
    manifest = tomllib.loads(fetch(f"{RAW}/{revision}/manifest.toml").decode("utf-8"))
    if component_filter and component_filter not in {c.get("name") for c in manifest.get("components", [])}:
        raise ValueError(f"unknown Caelestia component: {component_filter}")
    return revision, catalog_from_manifest(manifest, component_filter)


def find_missing_packages(
    packages: list[tuple[str, str]],
    *,
    query: Callable[[list[str]], tuple[set[str], set[str]]],
) -> list[PackageNeed]:
    valid = [(component, package) for component, package in packages if PACKAGE_RE.fullmatch(package)]
    installed, official = query(sorted({p for _, p in valid}))
    return [
        PackageNeed(component, package, "arch" if package in official else "unlisted")
        for component, package in valid
        if package not in installed
    ]


def _pacman_package_sets(packages: list[str]) -> tuple[set[str], set[str]]:
    installed_proc = run(["pacman", "-Qq"], timeout=30)
    repo_proc = run(["pacman", "-Sl"], timeout=30)
    if installed_proc is None or installed_proc.rc != 0:
        raise RuntimeError("could not read installed packages with pacman -Qq")
    if repo_proc is None or repo_proc.rc != 0:
        raise RuntimeError("could not read configured repositories with pacman -Sl")
    names = set(packages)
    installed = {line.strip() for line in installed_proc.out.splitlines() if line.strip()} & names
    official = set()
    for line in repo_proc.out.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] in names:
            official.add(fields[1])
    return installed, official


def _is_installed(package: str) -> bool:
    result = run(["pacman", "-Q", package], timeout=10)
    return result is not None and result.rc == 0


def review_packages(
    component_filter: str | None = None,
    *,
    dry_run: bool = False,
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
    is_tty: bool | None = None,
    fetch: Callable[[str], bytes] = _request,
    package_query: Callable[[list[str]], tuple[set[str], set[str]]] = _pacman_package_sets,
    verify_installed: Callable[[str], bool] = _is_installed,
    execute: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> tuple[int, int]:
    """Report the official manifest and request consent separately for each package install."""
    try:
        revision, catalog = upstream_package_catalog(component_filter, fetch=fetch)
        missing = find_missing_packages(catalog, query=package_query)
    except (OSError, RuntimeError, KeyError, ValueError, urllib.error.URLError, tomllib.TOMLDecodeError) as exc:
        say(f"Could not audit Caelestia packages: {exc}")
        return 0, 1
    say(f"Caelestia package catalog at {revision}: {len(catalog)} package entry/entries checked.")
    if not missing:
        say("All package entries in the selected default component(s) are installed.")
        return 0, 0
    say(f"Missing {len(missing)} package(s):")
    for item in missing:
        source_label = "configured pacman repository" if item.source == "arch" else "AUR / not found in current sync databases"
        say(f"  {item.component}: {item.name} ({source_label})")
    say("This checks packages only; it does not run Caelestia manifest post-install scripts.")
    say("A package missing from current sync databases may be from AUR or may need a reviewed repository-database refresh.")
    if dry_run:
        say("Dry run only; no packages were installed.")
        return 0, 0

    tty = sys.stdin.isatty() and sys.stdout.isatty() if is_tty is None else is_tty
    installed = errors = 0
    for item in missing:
        helper = None
        if item.source != "arch":
            helper = shutil.which("paru") or shutil.which("yay")
        if item.source != "arch" and not helper:
            say(f"Cannot safely classify/install {item.name}: install an AUR helper or review your sync databases first.")
            errors += 1
            continue
        if not tty:
            say("A terminal is required for package installation; nothing was installed.")
            return installed, errors + 1
        command = ([helper, "-S", "--needed", item.name] if helper else
                   ["sudo", "pacman", "-S", "--needed", item.name])
        say(f"\nPackage: {item.name} ({'configured pacman repository' if item.source == 'arch' else 'AUR/unlisted'})")
        if item.source != "arch":
            say("AUR packages run user-provided build/install instructions; review the PKGBUILD when prompted.")
        say("Command: " + " ".join(command))
        try:
            answer = ask("Install this package? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            say("\nCancelled; no further packages were installed.")
            break
        if answer not in ("y", "yes"):
            say("Skipped.")
            continue
        try:
            result = execute(command, check=False)
        except OSError as exc:
            errors += 1
            say(f"Could not start package manager: {exc}")
            continue
        if result.returncode != 0:
            errors += 1
            say(f"Package manager failed (exit {result.returncode}).")
        elif not verify_installed(item.name):
            errors += 1
            say(f"Package manager returned success, but pacman cannot verify {item.name} is installed.")
        else:
            installed += 1
            say(f"Installed: {item.name}")
    say(f"\nInstalled {installed} package(s); {errors} error(s).")
    return installed, errors
