"""Every check module exposes run_checks() -> list[Result]."""

from . import arch, config, fish, hyprland, state, versions

ALL = [
    ("arch", arch.run_checks),
    ("versions", versions.run_checks),
    ("config", config.run_checks),
    ("fish", fish.run_checks),
    ("hyprland", hyprland.run_checks),
    ("state", state.run_checks),
]
