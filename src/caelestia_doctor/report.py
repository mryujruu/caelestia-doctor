"""Turn a list of Results into pretty terminal text or a GitHub-ready Markdown report."""

from __future__ import annotations

import getpass
import json
import os
import platform
import shutil
import textwrap
from pathlib import Path

from .utils import FAIL, INFO, OK, WARN, Result, home, read_text

ORDER = {FAIL: 0, WARN: 1, INFO: 2, OK: 3}
GROUPS = {
    FAIL: ("✖", "Problems", "31"),
    WARN: ("⚠", "Warnings", "33"),
}


def redact(text: str) -> str:
    """Keep personal paths/usernames out of reports people paste online."""
    h = str(home())
    if h and h != "/":
        text = text.replace(h, "~")
    try:
        user = getpass.getuser()
    except Exception:
        user = ""
    if user and len(user) > 2:
        text = text.replace(user, "<user>")
    return text


def summary(results: list[Result]) -> dict[str, int]:
    out = {OK: 0, INFO: 0, WARN: 0, FAIL: 0}
    for r in results:
        out[r.status] += 1
    return out


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def render_text(results: list[Result], color: bool = False, width: int | None = None) -> str:
    from . import __version__

    width = width or min(shutil.get_terminal_size((80, 20)).columns, 100)

    def c(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    out: list[str] = ["", c("1", f" caelestia-doctor {__version__}"),
                      c("2", " nothing is changed unless you confirm it"), ""]

    for status in (FAIL, WARN):
        group = [r for r in results if r.status == status]
        if not group:
            continue
        icon, title, code = GROUPS[status]
        out.append(c(f"{code};1", f" {icon} {title} ({len(group)})"))
        out.append("")
        for r in group:
            bar = c(code, " │ ")
            out.append(c(code, " ┌─ ") + c("1", r.name))
            for line in textwrap.wrap(r.message, width - 5) or [""]:
                out.append(bar + line)
            if r.hint:
                for line in textwrap.wrap(r.hint, width - 5):
                    out.append(bar + c("2", line))
            if r.steps:
                out.append(bar)
                out.append(bar + c("1;36", "What to do"))
                for step in r.steps:
                    if step.startswith("$ "):
                        out.append(bar + "  " + c("36", step))
                    else:
                        for line in textwrap.wrap(step, width - 7):
                            out.append(bar + "  " + line)
            if r.repair:
                out.append(bar)
                out.append(bar + c("1;32", "Can be fixed automatically"))
                for line in textwrap.wrap(r.repair.description, width - 7):
                    out.append(bar + "  " + line)
                out.append(bar + "  " + c("36", "$ caelestia-doctor fix"))
            out.append(c(code, " └─"))
            out.append("")

    passed = [r for r in results if r.status in (OK, INFO)]
    if passed:
        out.append(c("32;1", f" ✔ Passed ({len(passed)})"))
        for r in sorted(passed, key=lambda r: ORDER[r.status]):
            mark = c("32", "✔") if r.status == OK else c("36", "ℹ")
            line = f"{r.name}: {r.message}"
            if len(line) > width - 6:
                line = line[: width - 9] + "..."
            out.append(f"   {mark} {line}")
        out.append("")

    s = summary(results)
    parts = [
        c("31;1", _plural(s[FAIL], "problem")),
        c("33;1", _plural(s[WARN], "warning")),
        c("32;1", f"{s[OK] + s[INFO]} ok"),
    ]
    out.append(" " + c("2", "─" * min(width - 2, 40)))
    out.append(" " + "  ·  ".join(parts))
    if s[FAIL] or s[WARN]:
        out.append(c("2", " Tip: `caelestia-doctor report` makes a version you can paste into a GitHub issue."))
    n_repairs = sum(1 for r in results if r.repair and r.status in (FAIL, WARN))
    if n_repairs:
        out.append(c("2", f" {_plural(n_repairs, 'repair')} can be applied safely: run `caelestia-doctor fix`."))
    out.append("")
    return "\n".join(out)


def _os_name() -> str:
    text = read_text(Path("/etc/os-release")) or ""
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return platform.system()


def render_markdown(results: list[Result]) -> str:
    s = summary(results)
    md = ["### caelestia-doctor report", ""]
    md.append(f"- OS: {_os_name()}")
    md.append(f"- Kernel: {platform.release()}")
    md.append(f"- Session: {os.environ.get('XDG_SESSION_TYPE', '?')} / "
              f"{os.environ.get('XDG_CURRENT_DESKTOP', '?')}")
    md.append(f"- Result: {s[FAIL]} problem(s), {s[WARN]} warning(s), {s[OK]} ok")
    md += ["", "| Status | Check | Result |", "|---|---|---|"]
    for r in sorted(results, key=lambda r: ORDER[r.status]):
        msg = r.message.replace("|", "\\|")
        md.append(f"| {r.status} | {r.name} | {msg} |")

    notes = [r for r in results if (r.hint or r.steps or r.repair) and r.status in (WARN, FAIL)]
    if notes:
        md += ["", "#### Suggested fixes"]
        for r in notes:
            md += ["", f"**{r.name}**"]
            if r.hint:
                md.append(r.hint)
            if r.repair:
                md.append(f"- Automatic repair available (`caelestia-doctor fix`): {r.repair.description}")
            cmds = [x[2:] for x in r.steps if x.startswith("$ ")]
            for x in r.steps:
                if not x.startswith("$ "):
                    md.append(f"- {x}")
            if cmds:
                md += ["```sh", *cmds, "```"]

    details = [r for r in results if r.detail]
    if details:
        md += ["", "<details><summary>Raw output</summary>", ""]
        for r in details:
            md += [f"**{r.name}**", "```", r.detail, "```", ""]
        md.append("</details>")
    return redact("\n".join(md))


def render_json(results: list[Result]) -> str:
    """Machine-readable, redacted diagnostics for issue trackers and automation."""
    records = []
    for result in results:
        records.append({
            "status": result.status,
            "name": result.name,
            "message": result.message,
            "hint": result.hint,
            "detail": result.detail,
            "steps": result.steps,
            "repair_available": result.repair is not None,
            "repair_description": result.repair.description if result.repair else None,
        })
    return redact(json.dumps({
        "tool": "caelestia-doctor",
        "os": _os_name(),
        "kernel": platform.release(),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "?"),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "?"),
        "summary": summary(results),
        "checks": records,
    }, ensure_ascii=False, indent=2))
