"""Syntax-check a user-supplied command without executing it."""

from __future__ import annotations

import re
from pathlib import Path

from .utils import FAIL, INFO, OK, WARN, Result, have, read_text, run

ASSIGNMENT = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def fish_assignment_suggestion(command: str) -> str | None:
    """Translate only plain leading `name=value` command lines into Fish `set` syntax."""
    lines = command.splitlines()
    changed = False
    for index, line in enumerate(lines):
        match = ASSIGNMENT.match(line)
        if not match:
            continue
        indent, name, value = match.groups()
        lines[index] = f"{indent}set {name} {value}" if value else f"{indent}set {name} ''"
        changed = True
    return "\n".join(lines) if changed else None


def check_command(command: str, shell: str = "fish") -> list[Result]:
    if not command.strip():
        return [Result("Command syntax", INFO, "no command text was supplied")]
    if shell == "fish":
        if not have("fish"):
            return [Result("Command syntax", INFO, "Fish is not installed; cannot parse this command")]
        proc = run(["fish", "--no-config", "--no-execute", "--command", command], timeout=10)
    elif shell == "bash":
        if not have("bash"):
            return [Result("Command syntax", INFO, "Bash is not installed; cannot parse this command")]
        proc = run(["bash", "-n", "-c", command], timeout=10)
    else:
        return [Result("Command syntax", INFO, f"unsupported shell: {shell}")]

    if proc is None:
        return [Result("Command syntax", INFO, f"{shell} disappeared before the syntax check")]
    if proc.rc == 124:
        return [Result("Command syntax", INFO, f"{shell} parser timed out")]
    if proc.rc != 0:
        suggestion = fish_assignment_suggestion(command) if shell == "fish" else None
        hint = "The command was parsed only; it was not executed."
        steps = ["Recheck with:", f"$ {shell} -n"]
        if suggestion:
            hint += " A leading `name=value` is Bash syntax; Fish uses `set name value`."
            steps += ["Suggested Fish form (review it before use):", suggestion]
        return [Result("Command syntax", FAIL, f"{shell} reported a syntax error", hint,
                       detail=proc.err or proc.out, steps=steps)]

    results = [Result("Command syntax", OK, f"{shell} accepts the command syntax; the command was not executed")]
    if shell == "fish" and re.search(r"\|\s*less(?:\s|$)", command) and not have("less"):
        results.append(Result(
            "Command dependency: less",
            WARN,
            "this pipeline invokes `less`, but it is not installed",
            "Use `head`/`cat`, or run `caelestia-doctor install` to review an optional installation from your configured pacman repositories.",
            steps=["$ caelestia-doctor install"],
        ))
    return results


def check_command_file(path: str | Path, shell: str = "fish") -> list[Result]:
    file_path = Path(path).expanduser()
    text = read_text(file_path)
    if text is None:
        return [Result("Command syntax", FAIL, f"could not read {file_path}")]
    return check_command(text, shell)
