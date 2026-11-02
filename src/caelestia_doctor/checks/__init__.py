"""Every check module exposes run_checks() -> list[Result]."""

from . import config, hyprland, state, versions

ALL = [
    ("versions", versions.run_checks),
    ("config", config.run_checks),
    ("hyprland", hyprland.run_checks),
    ("state", state.run_checks),
]
