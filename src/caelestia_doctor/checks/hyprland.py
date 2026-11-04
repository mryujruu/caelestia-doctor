"""Hyprland config checks: Lua vs .conf, and keyboard layout codes."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from ..utils import FAIL, INFO, OK, WARN, Result, config_dir, have, read_text, run, short

XKB_LIST = Path("/usr/share/X11/xkb/rules/base.lst")
LAYOUT_RE = re.compile(r"""kb_layout\s*=\s*["']?([^"'\n},]+(?:,[^"'\n},]+)*)""")
VERSION_RE = re.compile(r"Hyprland\s+v?(\d+)\.(\d+)")


def layout_names(path: Path = XKB_LIST) -> dict[str, str] | None:
    """{code: description} of the layouts known to xkb, or None if the list is not available."""
    text = read_text(path)
    if text is None:
        return None
    names: dict[str, str] = {}
    in_section = False
    for line in text.splitlines():
        if line.startswith("!"):
            in_section = line.strip() == "! layout"
            continue
        if in_section and line.strip():
            parts = line.split(None, 1)
            names[parts[0]] = parts[1].strip() if len(parts) > 1 else ""
    return names or None


def valid_layouts(path: Path = XKB_LIST) -> set[str] | None:
    names = layout_names(path)
    return set(names) if names else None


def suggest_layouts(code: str, known: set[str]) -> list[str]:
    """Closest valid codes for a wrong one (for example ar -> ara)."""
    c = code.lower()
    out = sorted((k for k in known if k.startswith(c) and k != c), key=lambda k: (len(k), k))[:3]
    for k in difflib.get_close_matches(c, sorted(known), n=3, cutoff=0.6):
        if k not in out:
            out.append(k)
    return out[:3]


def split_codes(value: str) -> list[str]:
    return [c.strip() for c in value.split(",") if c.strip()]


def find_layouts_in_text(text: str) -> list[list[str]]:
    return [split_codes(m.group(1)) for m in LAYOUT_RE.finditer(text)]


def parse_version(text: str) -> tuple[int, int] | None:
    m = VERSION_RE.search(text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def lua_is_used(version: tuple[int, int] | None) -> bool | None:
    """Hyprland 0.55 and newer read hyprland.lua. None = unknown."""
    return None if version is None else version >= (0, 55)


def _config_files(hypr: Path, caelestia: Path):
    for root in (hypr, caelestia):
        if root.is_dir():
            for f in sorted(root.rglob("*")):
                if f.is_file() and f.suffix in (".lua", ".conf"):
                    yield f


def _layout_fix(bad: list[str], names: dict[str, str], where: str) -> list[str]:
    fix: list[str] = []
    for code in bad:
        opts = suggest_layouts(code, set(names))
        if opts:
            shown = ", ".join(f"{o} ({names.get(o, '')})" if names.get(o) else o for o in opts)
            fix.append(f"Instead of `{code}` you probably want: {shown}")
    fix.append(f"Edit the kb_layout line in {where}, then apply it:")
    fix.append("$ hyprctl reload")
    fix.append("To browse every valid code:")
    fix.append("$ localectl list-x11-keymap-layouts")
    return fix


def run_checks() -> list[Result]:
    results: list[Result] = []
    hypr = config_dir() / "hypr"
    lua, conf = hypr / "hyprland.lua", hypr / "hyprland.conf"

    hv = run(["hyprctl", "version"])
    version = parse_version(hv.out) if hv and hv.rc == 0 else None

    if lua.exists() and conf.exists():
        used = lua_is_used(version)
        if used is True:
            results.append(Result(
                "Hyprland config", WARN,
                f"both hyprland.lua and hyprland.conf exist, and your Hyprland "
                f"{version[0]}.{version[1]} uses the Lua one",
                "hyprland.conf is probably ignored, so edits to it will seem to do nothing.",
                steps=["If you are sure everything you need is in the Lua files, keep the old file as a backup:",
                     f"$ mv {short(conf)} {short(conf)}.bak"],
            ))
        else:
            results.append(Result(
                "Hyprland config", WARN, "both hyprland.lua and hyprland.conf exist",
                "Hyprland 0.55 and newer use the Lua config; older versions use .conf. "
                "Only one is used, so edits to the other one will seem to do nothing.",
                steps=["Check your version, then edit the matching file:", "$ hyprctl version"],
            ))
    elif lua.exists():
        results.append(Result("Hyprland config", OK, "using hyprland.lua"))
    elif conf.exists():
        results.append(Result("Hyprland config", OK, "using hyprland.conf"))
    else:
        results.append(Result(
            "Hyprland config", WARN, f"no hyprland.lua / hyprland.conf in {short(hypr)}",
            "Hyprland will start with its generated fallback config, so your keybinds and Caelestia startup may be missing.",
            steps=["Review the missing upstream defaults, then answer Y to download only the files you want:",
                   "$ caelestia-doctor restore --component hypr"],
        ))

    # Check the active parser's diagnostics when a Hyprland session is available.
    errors = run(["hyprctl", "configerrors"])
    if errors is not None and errors.rc == 0:
        diagnostic = errors.out.strip()
        lower = diagnostic.lower()
        if diagnostic and not any(token in lower for token in ("no errors", "no config errors", "no errors found")):
            results.append(Result(
                "Hyprland config errors", FAIL, "Hyprland reports configuration errors",
                "The compositor may have skipped settings or loaded a fallback configuration.",
                detail=diagnostic,
                steps=["Correct the reported file and line, then reload and inspect errors:",
                       "$ hyprctl reload", "$ hyprctl configerrors"],
            ))
        else:
            results.append(Result("Hyprland config errors", OK, "Hyprland reports no configuration errors"))
    elif errors is not None and errors.rc not in (0, 124):
        results.append(Result(
            "Hyprland config errors", INFO, "could not query the active Hyprland session",
            detail=errors.err or errors.out,
        ))

    # `hyprctl configerrors` checks the active session. luac is a useful offline
    # syntax check, but cannot validate Hyprland options or imported modules.
    if have("luac"):
        lua_files = [f for f in _config_files(hypr, config_dir() / "caelestia") if f.suffix == ".lua"]
        for lua_file in lua_files:
            parsed = run(["luac", "-p", str(lua_file)], timeout=10)
            if parsed is not None and parsed.rc != 0:
                results.append(Result(
                    f"Lua syntax: {lua_file.name}", FAIL, f"{short(lua_file)} has invalid Lua syntax",
                    "This checks Lua syntax only; use Hyprland's own diagnostics for option and runtime errors.",
                    detail=parsed.err or parsed.out,
                    steps=["Fix the syntax error, then reload and inspect Hyprland's diagnostics:",
                           "$ hyprctl reload", "$ hyprctl configerrors"],
                ))
            elif parsed is not None:
                results.append(Result(f"Lua syntax: {lua_file.name}", OK, f"{short(lua_file)} parses successfully"))

    names = layout_names()
    if names is None:
        results.append(Result("Keyboard layout", INFO,
                              f"cannot read {XKB_LIST}, skipping layout validation"))
        return results
    known = set(names)

    # 1) what Hyprland is really using right now
    live = run(["hyprctl", "getoption", "input:kb_layout"])
    if live is not None and live.rc == 0:
        m = re.search(r"str:\s*(.*)", live.out)
        value = m.group(1).strip() if m else ""
        bad = [c for c in split_codes(value) if c not in known]
        if bad:
            results.append(Result(
                "Keyboard layout", FAIL,
                f'active kb_layout "{value}" contains unknown code(s): {", ".join(bad)}',
                "Hyprland falls back to US silently when a code is not valid.",
                steps=_layout_fix(bad, names, "your Hyprland config"),
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
                    f"File: {short(f)}. Make sure this is the file Hyprland really loads.",
                    steps=_layout_fix(bad, names, short(f)),
                ))
    if (live is None or live.rc != 0) and not seen_bad:
        results.append(Result("Keyboard layout", OK, "config files contain only valid layout codes"))
    return results
