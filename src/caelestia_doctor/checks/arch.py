"""Read-only health checks for an Arch-based host running Caelestia."""

from __future__ import annotations

import shutil
import os
import re
from pathlib import Path

from ..utils import FAIL, INFO, OK, WARN, Result, home, have, read_text, run, short


def _os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    text = read_text(Path("/etc/os-release")) or ""
    for line in text.splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def _systemd_check(user: bool) -> Result | None:
    command = ["systemctl"]
    if user:
        command.append("--user")
    command += ["--failed", "--no-legend", "--no-pager"]
    proc = run(command, timeout=8)
    scope = "user" if user else "system"
    if proc is None:
        return None
    if proc.rc != 0:
        reason = proc.err or proc.out or f"systemctl exited with code {proc.rc}"
        return Result(
            f"systemd {scope} services",
            INFO,
            f"could not inspect {scope} units: {reason}",
            steps=[f"$ systemctl {'--user ' if user else ''}--failed --no-pager"],
        )
    failed = [line for line in proc.out.splitlines() if line.strip()]
    if not failed:
        return Result(f"systemd {scope} services", OK, "no failed units")
    return Result(
        f"systemd {scope} services",
        WARN,
        f"{len(failed)} failed {scope} unit(s)",
        "A failed unit may be unrelated to Caelestia; inspect its status before restarting or changing it.",
        detail="\n".join(failed),
        steps=[f"$ systemctl {'--user ' if user else ''}--failed --no-pager"],
    )


def _pacman_files_check() -> Result:
    """Check for absent files owned by installed packages without changing them."""
    proc = run(["pacman", "-Qkq"], timeout=120)
    if proc is None:
        return Result("Installed package files", INFO, "pacman command is unavailable")
    if proc.rc == 124:
        return Result(
            "Installed package files",
            INFO,
            "pacman file check timed out after 120 seconds",
            "Run the check manually when the system is idle.",
            steps=["$ pacman -Qkq"],
        )
    if proc.rc != 0:
        return Result(
            "Installed package files",
            INFO,
            f"pacman file check could not complete (exit {proc.rc})",
            "Review pacman's output; this check is read-only and will not reinstall packages.",
            detail=proc.err or proc.out,
            steps=["$ pacman -Qkq"],
        )
    missing = [line for line in proc.out.splitlines() if line.strip()]
    if not missing:
        return Result("Installed package files", OK, "all checked package-owned files are present")
    shown = missing[:80]
    detail = "\n".join(shown)
    if len(missing) > len(shown):
        detail += f"\n... and {len(missing) - len(shown)} more missing path(s)"
    return Result(
        "Installed package files",
        WARN,
        f"{len(missing)} package-owned file path(s) are missing",
        "Some missing files may be intentional. Identify the owning package and review its status before reinstalling anything.",
        detail=detail,
        steps=["Check a package's files:", "$ pacman -Qk <package>", "Reinstall only a confirmed damaged package:", "$ sudo pacman -S <package>"],
    )


# --- pacman -Qkk -------------------------------------------------------------------------------

_MISMATCH = re.compile(r"^(?:warning|error):\s+(?P<pkg>[^:\s]+):\s+(?P<path>/.*?)\s+\((?P<reason>[^()]+)\)\s*$")
_SUMMARY = re.compile(r"\b\d+\s+total files?,\s*(\d+)\s+altered files?\b", re.IGNORECASE)

# What each pacman reason means. Only real content changes outside /etc deserve a warning.
_CONTENT = {"size mismatch", "md5 checksum mismatch", "sha256 checksum mismatch", "type mismatch",
            "symlink path mismatch"}
_MISSING = {"no such file or directory"}
_UNREADABLE = {"permission denied"}
# Files people remove on purpose (documentation and translations), so "missing" is expected there.
_REMOVABLE = ("/usr/share/doc/", "/usr/share/man/", "/usr/share/info/", "/usr/share/locale/",
              "/usr/share/help/", "/usr/share/gtk-doc/")

CATEGORY_TITLES = {
    "content": "content changed outside /etc",
    "missing": "missing from disk",
    "config": "changed under /etc (usually your own edits)",
    "removable": "removed docs or translations",
    "metadata": "only time, owner or permission differences",
    "unreadable": "unreadable without root, so not checked",
}
# Shown first, and the only ones that make the result a warning.
ATTENTION = ("content", "missing")


def classify_file(path: str, reasons: set[str]) -> str:
    low = {r.lower() for r in reasons}
    if low & _UNREADABLE:
        return "unreadable"
    if low & _MISSING:
        return "removable" if path.startswith(_REMOVABLE) else "missing"
    if path.startswith("/etc/") or path == "/etc":
        return "config"
    if low & _CONTENT:
        return "content"
    return "metadata"


def parse_pacman_qkk(output: str) -> dict:
    """Group `pacman -Qkk` output by file and category.

    Returns {"files": {(pkg, path): set(reasons)}, "groups": {category: [(pkg, path, reasons)]},
    "summary_altered": int} where summary_altered is what pacman itself counted.
    """
    files: dict[tuple[str, str], set[str]] = {}
    summary = 0
    for line in output.splitlines():
        m = _MISMATCH.match(line.strip())
        if m:
            files.setdefault((m["pkg"], m["path"]), set()).add(m["reason"].strip())
            continue
        m = _SUMMARY.search(line)
        if m:
            summary += int(m.group(1))
    groups: dict[str, list] = {k: [] for k in CATEGORY_TITLES}
    for (pkg, path), reasons in sorted(files.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        groups[classify_file(path, reasons)].append((pkg, path, sorted(reasons)))
    return {"files": files, "groups": groups, "summary_altered": summary}


def _detail(groups: dict, limit: int = 60) -> str:
    lines: list[str] = []
    for cat in (*ATTENTION, "config", "removable", "metadata", "unreadable"):
        items = groups[cat]
        if not items:
            continue
        lines.append(f"== {CATEGORY_TITLES[cat]} ({len(items)})")
        for pkg, path, reasons in items[:limit]:
            lines.append(f"{path}  [{pkg}: {', '.join(reasons)}]")
        if len(items) > limit:
            lines.append(f"... and {len(items) - limit} more")
        lines.append("")
    return "\n".join(lines).rstrip()


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def summarize_pacman_qkk(output: str) -> Result | None:
    """Turn `pacman -Qkk` output into one result, or None when nothing was altered."""
    data = parse_pacman_qkk(output)
    groups, total = data["groups"], len(data["files"])

    if total == 0:
        altered = data["summary_altered"]
        if not altered:
            return None
        # pacman counted files but printed no per-file lines we understand: report it as before.
        return Result(
            "Pacman file integrity", WARN, f"pacman reports {altered} altered package-owned file(s)",
            "Some changes, especially under /etc, may be intentional. Review the package and file before reinstalling.",
            detail="\n".join(output.splitlines()[:120]),
            steps=["Inspect a specific package:", "$ pacman -Qkk <package>",
                   "Only reinstall a confirmed damaged package after reviewing the diff."],
        )

    parts = [f"{len(groups[c])} {CATEGORY_TITLES[c]}" for c in (*ATTENTION, "config", "removable", "metadata", "unreadable")
             if groups[c]]
    message = f"pacman lists {_plural(total, 'altered file')}: " + "; ".join(parts)
    detail = _detail(groups)
    attention = [item for c in ATTENTION for item in groups[c]]

    if not attention:
        return Result(
            "Pacman file integrity", INFO, message + ". None of these need action by themselves.",
            detail=detail,
            steps=["See every file by category:", "$ caelestia-doctor deep-check --full"],
        )

    steps = ["These files need a look:"]
    for pkg, path, reasons in attention[:10]:
        steps.append(f"{path} (package {pkg}): {', '.join(reasons)}")
    if len(attention) > 10:
        steps.append(f"... and {len(attention) - 10} more. List them all with: caelestia-doctor deep-check --full")
    steps += ["Compare the package's files with what is on disk:", f"$ pacman -Qkk {attention[0][0]}",
              "Reinstall a package only after you have confirmed it is damaged and not changed on purpose."]
    if groups["unreadable"]:
        steps += ["Some files cannot be read without root. To check them too (read-only):", "$ sudo pacman -Qkk"]
    return Result(
        "Pacman file integrity", WARN, message,
        "Changes under /etc, timestamps, owners and permissions are common and usually harmless. "
        "Changed content or missing files elsewhere are worth reviewing.",
        detail=detail, steps=steps,
    )


def run_deep_checks() -> list[Result]:
    """Run pacman's slower checksum/metadata verification for installed package files."""
    if not have("pacman"):
        return [Result("Pacman file integrity", INFO, "pacman command is unavailable")]
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    proc = run(["pacman", "-Qkk"], timeout=240, env=env)
    if proc is None:
        return [Result("Pacman file integrity", INFO, "pacman command is unavailable")]
    if proc.rc == 124:
        return [Result("Pacman file integrity", INFO, "deep package check timed out after 240 seconds",
                       steps=["Run this check again when the system is idle:", "$ caelestia-doctor deep-check"])]
    output = "\n".join(part for part in (proc.out, proc.err) if part)
    result = summarize_pacman_qkk(output)
    if result is not None:
        return [result]
    details = "\n".join(output.splitlines()[:120])
    if proc.rc != 0:
        return [Result("Pacman file integrity", INFO, f"pacman -Qkk could not finish (exit {proc.rc})",
                       detail=details, steps=["$ pacman -Qkk"])]
    return [Result("Pacman file integrity", OK, "pacman found no altered package-owned files", detail=details)]


def run_checks() -> list[Result]:
    results: list[Result] = []
    release = _os_release()
    os_id = release.get("ID", "").lower()
    os_like = release.get("ID_LIKE", "").lower().split()
    # CachyOS identifies itself as `cachyos`; some releases may not provide
    # ID_LIKE, so recognize it explicitly instead of relying on the family hint.
    if os_id in {"arch", "cachyos"} or "arch" in os_like:
        results.append(Result("Operating system", OK, release.get("PRETTY_NAME", "Arch-based Linux")))
    else:
        results.append(
            Result(
                "Operating system",
                WARN,
                f"{release.get('PRETTY_NAME', 'unknown Linux')} detected; this tool targets Arch-based Linux, including CachyOS",
                "Package and default-file guidance is based on the official Caelestia Arch-compatible installation.",
            )
        )

    try:
        usage = shutil.disk_usage(home())
        used_pct = round((usage.total - usage.free) * 100 / usage.total) if usage.total else 0
        free_gib = usage.free / (1024**3)
        if used_pct >= 95 or free_gib < 1:
            results.append(
                Result(
                    "Home filesystem space",
                    WARN,
                    f"{used_pct}% used; {free_gib:.1f} GiB free at {short(home())}",
                    "Low disk space can prevent package upgrades, logs, and shell state from being written.",
                    steps=["Review large files before deleting anything:", "$ df -h ~", "$ du -h -d 1 ~ | sort -h"],
                )
            )
        else:
            results.append(
                Result("Home filesystem space", OK, f"{used_pct}% used; {free_gib:.1f} GiB free")
            )
    except OSError as exc:
        results.append(Result("Home filesystem space", INFO, f"could not inspect disk space: {exc}"))

    lock = Path("/var/lib/pacman/db.lck")
    if lock.exists():
        proc = run(["pgrep", "-a", "-x", "pacman"])
        running = proc is not None and proc.rc == 0
        results.append(
            Result(
                "Pacman database lock",
                INFO if running else WARN,
                "pacman is currently running" if running else f"lock file exists: {lock}",
                "Do not remove the lock while a package operation is active. If no pacman process is running, verify no package manager is working before removing a stale lock.",
                detail=proc.out if running and proc else "",
                steps=["Check for active package operations:", "$ pgrep -a pacman", "$ pgrep -a paru", "$ pgrep -a yay"],
            )
        )
    else:
        results.append(Result("Pacman database lock", OK, "no lock file"))

    if have("pacman"):
        db = run(["pacman", "-Dk"], timeout=20)
        if db is None:
            results.append(Result("Pacman database", INFO, "pacman command is unavailable"))
        elif db.rc == 0:
            results.append(Result("Pacman database", OK, "package database dependencies are consistent"))
        else:
            results.append(
                Result(
                    "Pacman database",
                    FAIL,
                    f"pacman -Dk reported an issue (exit {db.rc})",
                    "Review the package database output before attempting repair.",
                    detail=db.out or db.err,
                    steps=["Check database consistency:", "$ pacman -Dk"],
                )
            )
        results.append(_pacman_files_check())
    else:
        results.append(Result("Pacman database", INFO, "pacman command is unavailable"))

    for user_scope in (False, True):
        result = _systemd_check(user_scope)
        if result is not None:
            results.append(result)

    session = run(["hyprctl", "version"])
    proc_root = Path("/proc")
    if session is not None and session.rc == 0 and proc_root.is_dir():
        shell_processes: list[str] = []
        for process in proc_root.iterdir():
            if not process.name.isdigit():
                continue
            try:
                command_line = (process / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            if "quickshell" in command_line.lower() and "caelestia" in command_line.lower():
                shell_processes.append(command_line.strip())
        if shell_processes:
            results.append(Result("Caelestia shell process", OK, "Quickshell is running a Caelestia configuration"))
        else:
            results.append(
                Result(
                    "Caelestia shell process",
                    WARN,
                    "no running Quickshell process references Caelestia",
                    "This check only inspects process arguments; a custom wrapper may hide its config path.",
                    steps=["Start the shell and inspect its terminal output:", "$ caelestia shell -d"],
                )
            )
    return results
