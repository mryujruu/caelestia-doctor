# Upstream-informed checks

This project treats upstream reports as diagnostic clues, not proof that every machine has the same defect. It reports a finding and evidence; automatic changes remain limited to reversible file repairs and user-approved downloads from the official default dotfiles manifest.

| Finding or recurring report | Project response |
|---|---|
| Caelestia's dotfiles, shell, and CLI are separate components; the current dotfiles install flow is `caelestia install`. The upstream dotfiles moved Hyprland settings to Lua. | Check the installed commands and Hyprland config. Offer only the manifest-listed missing defaults from `caelestia-dots/caelestia`, one file at a time, and never overwrite custom files. |
| Shell issue #1177 reports theme changes that silently do nothing when Caelestia state files are missing. The issue describes a suspected cause, not a confirmed universal fix. | Check `scheme.json`, `wallpaper/path.txt`, and whether the saved wallpaper exists. Suggest starting the shell or selecting a wallpaper; do not invent state contents. |
| Shell issue #525 reports no valid wallpapers; maintainer replies point to `CAELESTIA_WALLPAPERS_DIR` and minimum image dimensions as possible causes. | Check configured wallpaper directories and path existence. Explain that a valid image may still be filtered if it is too small; do not alter wallpaper selection automatically. |
| Hyprland exposes `hyprctl configerrors` for active config diagnostics, but reports show it can sometimes be empty despite an on-screen error. | Query it when a session is reachable and also run `luac -p` when installed. A clean result is not presented as proof that runtime/plugin behavior is correct. |
| Shell issue #1788 describes launcher shortcut failures associated with a missing/unloaded Hyprland plugin and an outdated shell configuration. | Report installed versions and active Hyprland diagnostics; leave plugin compilation, dispatcher edits, and shell config migrations for an explicit user decision. |

## Sources

- [Caelestia dotfiles repository and current installation/configuration guidance](https://github.com/caelestia-dots/caelestia)
- [Official Caelestia dotfiles manifest](https://raw.githubusercontent.com/caelestia-dots/caelestia/main/manifest.toml)
- [Caelestia shell configuration and state guidance](https://github.com/caelestia-dots/shell)
- [Caelestia shell issue #1177: state and theme pipeline report](https://github.com/caelestia-dots/shell/issues/1177)
- [Caelestia shell issue #525: wallpaper selection report](https://github.com/caelestia-dots/shell/issues/525)
- [Caelestia shell issue #1788: launcher shortcut / plugin report](https://github.com/caelestia-dots/shell/issues/1788)
- [Hyprland `configerrors` discussion](https://github.com/hyprwm/Hyprland/discussions/15142)
