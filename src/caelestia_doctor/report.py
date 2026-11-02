"""Turn a list of Results into terminal text or a GitHub-ready Markdown report."""

from __future__ import annotations

import getpass
import os
import platform

from .utils import FAIL, INFO, OK, WARN, Result, home, read_text
from pathlib import Path

COLORS = {OK: "\033[32m", INFO: "\033[36m", WARN: "\033[33m", FAIL: "\033[31m"}
RESET = "\033[0m"
ORDER = {FAIL: 0, WARN: 1, INFO: 2, OK: 3}


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


def render_text(results: list[Result], color: bool = False) -> str:
    lines = []
    for r in sorted(results, key=lambda r: ORDER[r.status]):
        tag = f"[{r.status}]".ljust(7)
        if color:
            tag = f"{COLORS[r.status]}{tag}{RESET}"
        lines.append(f"{tag} {r.name}: {r.message}")
        if r.hint and r.status in (WARN, FAIL):
            lines.append(f"        → {r.hint}")
    s = summary(results)
    lines.append("")
    lines.append(f"{s[FAIL]} problem(s), {s[WARN]} warning(s), {s[OK]} ok.")
    return "\n".join(lines)


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

    hints = [r for r in results if r.hint and r.status in (WARN, FAIL)]
    if hints:
        md += ["", "#### Hints"]
        for r in hints:
            md.append(f"- **{r.name}**: {r.hint}")

    details = [r for r in results if r.detail]
    if details:
        md += ["", "<details><summary>Raw output</summary>", ""]
        for r in details:
            md += [f"**{r.name}**", "```", r.detail, "```", ""]
        md.append("</details>")
    return redact("\n".join(md))
