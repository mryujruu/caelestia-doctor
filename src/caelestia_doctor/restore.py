"""Offer missing default Caelestia dotfiles from the official upstream repository.

Only files listed by the repository's default components are considered. The
tool never overwrites an existing file and verifies every download against the
Git blob SHA published by GitHub before writing it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from .utils import config_dir, home, run

REPOSITORY = "caelestia-dots/caelestia"
API = f"https://api.github.com/repos/{REPOSITORY}"
RAW = f"https://raw.githubusercontent.com/{REPOSITORY}"
USER_AGENT = "caelestia-doctor/1"
TIMEOUT = 20


@dataclass(frozen=True)
class UpstreamFile:
    component: str
    source: str
    target: Path
    sha: str
    mode: int
    revision: str


def _token() -> str | None:
    """Optional GitHub token, only used to raise the anonymous API rate limit (read-only access)."""
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _request(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = _token()
    if token and url.startswith(API + "/"):  # never send the token to any other host
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise RuntimeError(
                f"GitHub refused the request (HTTP {exc.code}). This is usually the limit for anonymous "
                "API calls. Wait a while and try again, or run it with a token to raise the limit: "
                "GITHUB_TOKEN=$(gh auth token) caelestia-doctor restore"
            ) from exc
        raise


def _relative_source(value: str) -> PurePosixPath | None:
    path = PurePosixPath(value)
    if path.is_absolute() or not value or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path


def _destination_root(value: str) -> Path | None:
    """Expand only supported home config variables; reject globs and other roots."""
    if any(mark in value for mark in ("*", "?", "[", "]")):
        return None
    xdg = config_dir()
    expanded = value.replace("${XDG_CONFIG_HOME:-$HOME/.config}", str(xdg))
    expanded = expanded.replace("$XDG_CONFIG_HOME", str(xdg)).replace("$HOME", str(home()))
    expanded = os.path.expanduser(expanded)
    if "$" in expanded:
        return None
    target = Path(expanded)
    resolved_home = home().resolve()
    try:
        target.resolve(strict=False).relative_to(resolved_home)
    except (OSError, ValueError):
        return None
    return target


def upstream_files(component_filter: str | None = None) -> tuple[str, list[UpstreamFile]]:
    """Fetch the official manifest and Git tree, returning the default-file catalog."""
    commit_info = json.loads(_request(f"{API}/commits/main"))
    revision = commit_info["sha"]
    manifest = tomllib.loads(_request(f"{RAW}/{revision}/manifest.toml").decode("utf-8"))
    tree_data = json.loads(_request(f"{API}/git/trees/{revision}?recursive=1"))
    if tree_data.get("truncated"):
        raise RuntimeError("GitHub returned a truncated file list; no downloads were attempted")

    blobs: dict[str, dict] = {
        item["path"]: item
        for item in tree_data.get("tree", [])
        if item.get("type") == "blob" and item.get("mode") in ("100644", "100755")
    }
    catalog: list[UpstreamFile] = []
    for component in manifest.get("components", []):
        name = component.get("name", "unnamed")
        if not component.get("default", False):
            continue
        if component_filter and name != component_filter:
            continue
        for entry in component.get("entries", []):
            source = _relative_source(entry.get("src", ""))
            target_root = _destination_root(entry.get("dest", ""))
            if source is None or target_root is None:
                continue

            source_text = source.as_posix()
            is_tree = any(p.startswith(source_text + "/") for p in blobs)
            if is_tree:
                items = (
                    (repo_path, blob, PurePosixPath(repo_path).relative_to(source))
                    for repo_path, blob in blobs.items()
                    if repo_path.startswith(source_text + "/")
                )
            elif source_text in blobs:
                items = ((source_text, blobs[source_text], PurePosixPath(".")),)
            else:
                continue

            for repo_path, blob, relative in items:
                target = target_root if str(relative) == "." else target_root / Path(*relative.parts)
                try:
                    target.resolve(strict=False).relative_to(home().resolve())
                except (OSError, ValueError):
                    continue
                catalog.append(
                    UpstreamFile(
                        component=name,
                        source=repo_path,
                        target=target,
                        sha=blob["sha"],
                        mode=0o755 if blob["mode"] == "100755" else 0o644,
                        revision=revision,
                    )
                )

    # An entry may map to the same target more than once; keep a stable unique list.
    unique: dict[Path, UpstreamFile] = {}
    for item in catalog:
        unique.setdefault(item.target, item)
    return revision, sorted(unique.values(), key=lambda x: (x.component, str(x.target)))


def missing_files(files: list[UpstreamFile]) -> list[UpstreamFile]:
    missing: list[UpstreamFile] = []
    for item in files:
        # A dangling symlink is still a user-managed path; never replace it.
        if item.target.exists() or item.target.is_symlink():
            continue
        missing.append(item)
    return missing


def _installed_hyprland_version() -> tuple[int, int] | None:
    """Read the installed package version without requiring a running session."""
    proc = run(["pacman", "-Q", "hyprland"])
    if proc is None or proc.rc != 0:
        proc = run(["hyprctl", "version"])
    if proc is None or proc.rc != 0:
        return None
    match = re.search(r"(\d+)\.(\d+)", proc.out)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _download(item: UpstreamFile, fetch: Callable[[str], bytes] = _request) -> None:
    data = fetch(f"{RAW}/{item.revision}/{item.source}")
    actual_sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if actual_sha != item.sha:
        raise ValueError(f"integrity check failed for upstream file {item.source}")
    if item.target.exists() or item.target.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing path: {item.target}")

    # Check both before and after creating parents so an existing symlink cannot
    # redirect directory creation outside the user's home.
    try:
        item.target.parent.resolve(strict=False).relative_to(home().resolve())
    except (OSError, ValueError) as exc:
        raise ValueError("destination escaped the user's home directory") from exc
    item.target.parent.mkdir(parents=True, exist_ok=True)
    try:
        item.target.parent.resolve().relative_to(home().resolve())
    except (OSError, ValueError) as exc:
        raise ValueError("destination escaped the user's home directory") from exc
    fd, temp_name = tempfile.mkstemp(prefix=f".{item.target.name}.", suffix=".tmp", dir=item.target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, item.mode)
        # A hard link is an exclusive atomic install on Linux. If the platform
        # forbids hard links, create the destination with O_EXCL instead; this
        # still refuses to overwrite a file created after our earlier check.
        try:
            os.link(temp_name, item.target)
        except OSError:
            fd = os.open(item.target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, item.mode)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(item.target, item.mode)
            except BaseException:
                try:
                    item.target.unlink()
                except OSError:
                    pass
                raise
    finally:
        try:
            os.unlink(temp_name)
        except OSError:
            pass


def _offer_empty_user_config(ask: Callable[[str], str], say: Callable[[str], None]) -> int:
    """Create the empty Fish hook file used by the upstream install manifest."""
    target = config_dir() / "caelestia" / "user-config.fish"
    if target.exists() or target.is_symlink():
        return 0
    say(f"\nMissing generated default: {target}")
    say("The official Fish component creates this empty per-user hook file during install.")
    try:
        answer = ask("Create this empty file? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        say("\nCancelled.")
        return 0
    if answer not in ("y", "yes"):
        say("Skipped.")
        return 0
    try:
        target.parent.resolve(strict=False).relative_to(home().resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.parent.resolve().relative_to(home().resolve())
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        say("The file appeared while confirming; it was left untouched.")
        return 0
    except (OSError, ValueError) as exc:
        say(f"Could not safely create the file: {exc}")
        return 0
    say(f"Created {target}")
    return 1


def _offer_scheme_initialization(
    ask: Callable[[str], str], say: Callable[[str], None]
) -> tuple[int, int]:
    """Use Caelestia's documented post-install command rather than inventing state JSON."""
    target = Path(os.environ.get("XDG_STATE_HOME", str(home() / ".local" / "state"))) / "caelestia" / "scheme.json"
    if target.exists() or target.is_symlink():
        return 0, 0
    say(f"\nMissing Caelestia state file: {target}")
    say("The official install manifest initializes this file with `caelestia scheme set -n caelestia`.")
    try:
        answer = ask("Run that command to initialize the default scheme? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        say("\nCancelled.")
        return 0, 0
    if answer not in ("y", "yes"):
        say("Skipped; no state file was created.")
        return 0, 0
    proc = run(["caelestia", "scheme", "set", "-n", "caelestia"], timeout=20)
    if proc is None:
        say("Could not run `caelestia`; install or repair caelestia-cli first.")
        return 0, 1
    if proc.rc != 0:
        say(f"Caelestia initialization failed (exit {proc.rc}): {proc.err or proc.out}")
        return 0, 1
    if not target.exists():
        say("The command completed, but scheme.json was not created. Review Caelestia's output and logs.")
        return 0, 1
    say(f"Initialized {target}")
    return 1, 0


def restore_missing(
    component_filter: str | None = None,
    *,
    dry_run: bool = False,
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
    fetch: Callable[[str], bytes] = _request,
) -> tuple[int, int]:
    """Show missing official defaults and ask Y/N before each individual download."""
    try:
        revision, catalog = upstream_files(component_filter)
    except (OSError, urllib.error.URLError, KeyError, ValueError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        say(f"Could not read the official Caelestia file list: {exc}")
        return 0, 1

    missing = missing_files(catalog)
    hypr_lua = [item for item in missing if item.component == "hypr" and item.source.endswith(".lua")]
    version = _installed_hyprland_version() if hypr_lua else None
    compatibility_skip = False
    if version is not None and version < (0, 55):
        say(
            f"Hyprland {version[0]}.{version[1]} cannot use the current upstream Lua config "
            "(Lua config support starts at 0.55); Hyprland config downloads were skipped."
        )
        missing = [item for item in missing if item.component != "hypr"]
        compatibility_skip = True
    elif version is None and hypr_lua and not dry_run:
        try:
            answer = ask(
                "Could not verify your Hyprland version. Current upstream defaults use Lua; "
                "continue to per-file confirmation? [y/N] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            say("\nCancelled. No files were downloaded.")
            return 0, 0
        if answer not in ("y", "yes"):
            say("Hyprland files skipped because version compatibility could not be confirmed.")
            missing = [item for item in missing if item.component != "hypr"]
            compatibility_skip = True
    if missing:
        say(f"Found {len(missing)} missing default file(s) in the official Caelestia dots.")
        say(f"Source: https://github.com/{REPOSITORY}/tree/{revision}")
    elif compatibility_skip:
        say("No compatible missing files remain to restore in the selected components.")
    else:
        say("No tracked default dotfiles are missing in the selected components.")
    say(f"Upstream revision checked: {revision}")
    if dry_run:
        for item in missing:
            say(f"Would offer: {item.target} (component {item.component})")
        say("Dry run only; no files were downloaded or created.")
        return 0, 0
    restored = 0
    errors = 0
    cancelled = False
    for item in missing:
        say(f"\nMissing: {item.target}")
        say(f"Component: {item.component}; upstream file: {item.source}")
        try:
            answer = ask("Download this file from the official Caelestia repository? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            say("\nCancelled. No further files were downloaded.")
            cancelled = True
            break
        if answer not in ("y", "yes"):
            say("Skipped.")
            continue
        try:
            _download(item, fetch)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            errors += 1
            say(f"Download failed; no existing file was replaced: {exc}")
        else:
            restored += 1
            say(f"Downloaded to {item.target}")
    if not cancelled and component_filter in (None, "fish"):
        restored += _offer_empty_user_config(ask, say)
    if not cancelled and component_filter is None:
        state_restored, state_errors = _offer_scheme_initialization(ask, say)
        restored += state_restored
        errors += state_errors
    say(f"\nRestored or initialized {restored} item(s); {errors} error(s).")
    return restored, errors
