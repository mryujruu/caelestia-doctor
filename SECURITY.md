# Security

## What this tool can do

Most commands only read. These can change your system, and only after you confirm:

- `fix` and `undo` edit small config files, with a backup first.
- `restore` and `backup restore` write files into your home folder. They never overwrite an existing file, and refuse paths that leave your home.
- `packages` and `install` run `sudo pacman -S` (or an AUR helper) for the package you approve. The exact command is shown first.

`restore` and `packages` read the current `main` branch of `caelestia-dots/caelestia` over HTTPS. Each downloaded file is checked against its Git blob hash from the pinned commit. **The trust root is GitHub and that repository**, so read every command before you answer `y`.

An optional `GITHUB_TOKEN` or `GH_TOKEN` is sent only to `api.github.com` and is never stored or printed. Use a token with no write permissions.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's private reporting: the **Security** tab of this repository, then **Report a vulnerability**. Include the version (`caelestia-doctor --version`) and the steps to reproduce.

## Supported versions

Only the latest release gets fixes.
