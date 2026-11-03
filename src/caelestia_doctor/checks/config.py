"""Validate ~/.config/caelestia/shell.json (and the optional per-monitor files)."""

from __future__ import annotations

import json
from pathlib import Path

from ..utils import (FAIL, INFO, OK, WARN, Repair, Result, config_dir, expand, read_text,
                     short, write_text_atomic)


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


def suggest_path(value: str) -> str | None:
    """If a path only fails because of upper/lower case, return the correct spelling."""
    p = expand(value)
    if not p.is_absolute():
        return None
    fixed = Path(p.anchor)
    for part in p.parts[1:]:
        cand = fixed / part
        if cand.exists():
            fixed = cand
            continue
        try:
            names = [e.name for e in fixed.iterdir()]
        except OSError:
            return None
        match = [n for n in names if n.casefold() == part.casefold()]
        if len(match) != 1:
            return None
        fixed = fixed / match[0]
    return str(fixed)


def make_path_repair(path: Path, text: str, key: str, val: str, better: str) -> Repair | None:
    """Rewrite one wrong-case path value in place, keeping the rest of the file exactly as it is."""
    new_val = short(better) if val.startswith("~") else better
    old, new = json.dumps(val, ensure_ascii=False), json.dumps(new_val, ensure_ascii=False)
    if old not in text:
        return None

    def apply() -> None:
        cur = path.read_text(encoding="utf-8")
        if old not in cur:
            if new in cur:
                return  # already fixed by an earlier repair
            raise OSError("the file changed since the check, run caelestia-doctor again")
        new_text = cur.replace(old, new)
        json.loads(new_text)  # never write something that is not valid JSON
        write_text_atomic(path, new_text)

    return Repair(path, f"In paths.{key}, change {val} to {new_val}", apply)


def _check_file(path: Path, label: str) -> list[Result]:
    text = read_text(path)
    if text is None:
        return [Result(label, FAIL, f"cannot read {short(path)}", "Check the file permissions.",
                       steps=[f"$ ls -l {short(path)}"])]
    if not text.strip():
        return [Result(label, WARN, "file is empty",
                       "An empty file is not valid JSON, and the shell may ignore your settings.",
                       steps=["Put {} in the file, or let `caelestia-doctor fix` do it for you."],
                       repair=Repair(path, "Replace the empty file with an empty JSON object ({})",
                                     lambda: write_text_atomic(path, "{}\n")))]

    data, dups, err = parse_json(text)
    if err:
        return [Result(label, FAIL, f"invalid JSON at {err}",
                       "JSON does not allow trailing commas, comments or single quotes.",
                       steps=["Look at the line above and fix it. This command shows the exact error:",
                            f"$ python -m json.tool {short(path)}"])]

    results = [Result(label, OK, "valid JSON")]
    if dups:
        names = ", ".join(sorted(set(dups)))
        results.append(Result(
            label, WARN, f"duplicate keys: {names}",
            "Only the last one is used, which is probably not what you wanted.",
            steps=[f"Merge the duplicate {names} blocks into one."],
        ))
    if not isinstance(data, dict):
        results.append(Result(label, FAIL, "top level must be an object { ... }",
                              steps=["The file must start with { and end with }."]))
        return results

    paths = data.get("paths")
    if isinstance(paths, dict):
        for key, val in paths.items():
            if not isinstance(val, str) or val.startswith(("root:", "http://", "https://")):
                continue  # built-in asset, URL, or not a path: nothing to check on disk
            if expand(val).exists():
                continue
            steps: list[str] = []
            repair = None
            better = suggest_path(val)
            if better:
                steps.append(f"Only the capital letters are wrong. The correct path is: {short(better)}")
                repair = make_path_repair(path, text, key, val, better)
            else:
                parent = expand(val).parent
                if parent.is_dir():
                    steps.append("The folder exists but the file does not. See what is in it:")
                    steps.append(f"$ ls -la {short(parent)}")
                else:
                    steps.append("The folder does not exist yet. Create it, or point to a different one.")
            results.append(Result(
                f"{label} → paths.{key}", WARN, f"path does not exist: {val}",
                "Linux paths are case-sensitive: Pictures and pictures are different folders.",
                steps=steps, repair=repair,
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
            "shell.json", INFO, f"not found at {short(main)}",
            "That is normal: Caelestia does not create it. Create it only if you want to change options.",
        ))

    mon = base / "monitors"
    if mon.is_dir():
        for f in sorted(mon.glob("*/shell.json")):
            results += _check_file(f, f"monitors/{f.parent.name}/shell.json")
    return results
