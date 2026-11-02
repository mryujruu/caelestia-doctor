"""Validate ~/.config/caelestia/shell.json (and the optional per-monitor files)."""

from __future__ import annotations

import json
from pathlib import Path

from ..utils import FAIL, INFO, OK, WARN, Result, config_dir, expand, read_text


def parse_json(text: str) -> tuple[object | None, list[str], str | None]:
    """Return (data, duplicate_keys, error_message)."""
    dups: list[str] = []

    def hook(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                dups.append(k)
            d[k] = v
        return d

    try:
        return json.loads(text, object_pairs_hook=hook), dups, None
    except json.JSONDecodeError as e:
        return None, dups, f"line {e.lineno}, column {e.colno}: {e.msg}"


def _check_file(path: Path, label: str) -> list[Result]:
    text = read_text(path)
    if text is None:
        return [Result(label, FAIL, f"cannot read {path}", "Check the file permissions.")]
    if not text.strip():
        return [Result(label, WARN, "file is empty",
                       'Put {} in it, or delete it. An empty file is not valid JSON.')]

    data, dups, err = parse_json(text)
    if err:
        hint = "JSON does not allow trailing commas, comments or single quotes."
        return [Result(label, FAIL, f"invalid JSON at {err}", hint)]

    results = [Result(label, OK, "valid JSON")]
    if dups:
        results.append(Result(
            label, WARN, "duplicate keys: " + ", ".join(sorted(set(dups))),
            "Only the last one is used, which is probably not what you wanted.",
        ))
    if not isinstance(data, dict):
        results.append(Result(label, FAIL, "top level must be an object { ... }"))
        return results

    paths = data.get("paths")
    if isinstance(paths, dict):
        for key, val in paths.items():
            if not isinstance(val, str):
                continue
            if val.startswith(("root:", "http://", "https://")):
                continue  # built-in asset or URL, nothing to check on disk
            if not expand(val).exists():
                results.append(Result(
                    f"{label} → paths.{key}", WARN, f"path does not exist: {val}",
                    "Check the spelling and capital letters. Linux paths are case-sensitive.",
                ))
    return results


def run_checks() -> list[Result]:
    base = config_dir() / "caelestia"
    main = base / "shell.json"
    results: list[Result] = []

    if main.exists():
        results += _check_file(main, "shell.json")
    else:
        results.append(Result(
            "shell.json", INFO, f"not found at {main}",
            "That is normal: Caelestia does not create it. Create it only if you want to change options.",
        ))

    mon = base / "monitors"
    if mon.is_dir():
        for f in sorted(mon.glob("*/shell.json")):
            results += _check_file(f, f"monitors/{f.parent.name}/shell.json")
    return results
