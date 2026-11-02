"""Hyprland config checks: Lua vs .conf, and keyboard layout codes."""

from __future__ import annotations

import re
from pathlib import Path

from ..utils import FAIL, INFO, OK, WARN, Result, config_dir, read_text, run

XKB_LIST = Path("/usr/share/X11/xkb/rules/base.lst")
LAYOUT_RE = re.compile(r"""kb_layout\s*=\s*["']?([^"'\n},]+(?:,[^"'\n},]+)*)""")


def valid_layouts(path: Path = XKB_LIST) -> set[str] | None:
    """Layout codes known to xkb, or None if the list is not available."""
    text = read_text(path)
    if text is None:
        return None
    codes: set[str] = set()
    in_section = False
    for line in text.splitlines():
        if line.startswith("!"):
            in_section = line.strip() == "! layout"
            continue
        if in_section and line.strip():
            codes.add(line.split()[0])
    return codes or None


def split_codes(value: str) -> list[str]:
    return [c.strip() for c in value.split(",") if c.strip()]


def find_layouts_in_text(text: str) -> list[list[str]]:
    return [split_codes(m.group(1)) for m in LAYOUT_RE.finditer(text)]


def _config_files(hypr: Path, caelestia: Path):
    for root in (hypr, caelestia):
        if root.is_dir():
            for f in sorted(root.rglob("*")):
                if f.is_file() and f.suffix in (".lua", ".conf"):
                    yield f


def run_checks() -> list[Result]:
    results: list[Result] = []
    hypr = config_dir() / "hypr"
    lua, conf = hypr / "hyprland.lua", hypr / "hyprland.conf"

    if lua.exists() and conf.exists():
        results.append(Result(
            "Hyprland config", WARN, "both hyprland.lua and hyprland.conf exist",
            "Hyprland 0.55 and newer use the Lua config; older versions use .conf. "
            "Only one is used, so edits to the other one will seem to do nothing.",
        ))
    elif lua.exists():
        results.append(Result("Hyprland config", OK, "using hyprland.lua"))
    elif conf.exists():
        results.append(Result("Hyprland config", OK, "using hyprland.conf"))
    else:
        results.append(Result("Hyprland config", INFO, f"no hyprland.lua / hyprland.conf in {hypr}"))

    known = valid_layouts()
    if known is None:
        results.append(Result("Keyboard layout", INFO,
                              f"cannot read {XKB_LIST}, skipping layout validation"))
        return results

    # 1) what Hyprland is really using right now
    live = run(["hyprctl", "getoption", "input:kb_layout"])
    if live is not None and live.rc == 0:
        m = re.search(r"str:\s*(.*)", live.out)
        value = m.group(1).strip() if m else ""
        codes = split_codes(value)
        bad = [c for c in codes if c not in known]
        if bad:
            results.append(Result(
                "Keyboard layout", FAIL,
                f"active kb_layout \"{value}\" contains unknown code(s): {', '.join(bad)}",
                "Hyprland falls back to US silently. Arabic is `ara`, not `ar`. "
                "Valid codes are listed by: localectl list-x11-keymap-layouts",
            ))
        else:
            results.append(Result("Keyboard layout", OK, f"active layout: {value or '(default)'}"))

    # 2) what is written in the config files
    seen_bad = False
    for f in _config_files(hypr, config_dir() / "caelestia"):
        text = read_text(f)
        if not text:
            continue
        for codes in find_layouts_in_text(text):
            bad = [c for c in codes if c not in known]
            if bad:
                seen_bad = True
                results.append(Result(
                    f"Keyboard layout in {f.name}", WARN,
                    f"unknown code(s) in kb_layout: {', '.join(bad)}",
                    f"File: {f}. Check that this file is actually the one Hyprland loads.",
                ))
    if live is None or live.rc != 0:
        if not seen_bad:
            results.append(Result("Keyboard layout", OK, "config files contain only valid layout codes"))
    return results
