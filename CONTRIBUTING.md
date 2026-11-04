# Contributing

Thanks for helping. This tool runs on other people's systems, so a few rules keep it trustworthy.

## Set up

```sh
git clone https://github.com/mryujruu/caelestia-doctor
cd caelestia-doctor
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" pyflakes
python -m pytest -q
python -m pyflakes src tests
```

## Rules

1. **Checks only read.** A check must never write, delete, install or run user-supplied text.
2. **Every WARN or FAIL explains itself:** a short `hint` (why it matters) and `steps` (what to do; lines starting with `$ ` are commands).
3. **Add a `repair` only when there is exactly one obviously correct fix.** A repair must back the file up, write it atomically, and be applied only after the user confirms (or passes `fix --all`). When in doubt, give steps instead.
4. **Never guess.** If the right answer depends on the user (a layout code, a package, a wallpaper), explain; do not edit.
5. **Network and `sudo` need a confirmation** for each action, and the exact command must be shown first.
6. **Every module must import cleanly.** `tests/test_imports.py` enforces this.
7. **Add a test** for each new check or repair, using a temporary `HOME` (see `tests/test_config.py`).

## Adding a check

1. Create `src/caelestia_doctor/checks/yourcheck.py` with `run_checks() -> list[Result]`.
2. Register it in `checks/__init__.py`.
3. Add tests, a line in `docs/checks.md`, and an entry in `CHANGELOG.md`.

## Reporting a problem in a check

Run `caelestia-doctor report`, read it, remove anything private, and paste it in a new issue.
