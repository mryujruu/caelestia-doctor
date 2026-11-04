"""Catch syntax and indentation errors in any module before a release (0.5.0 shipped with one)."""

import importlib
import pkgutil

import caelestia_doctor


def test_every_module_imports():
    names = [m.name for m in pkgutil.walk_packages(caelestia_doctor.__path__, "caelestia_doctor.")]
    assert len(names) >= 15
    for name in names:
        importlib.import_module(name)


def test_cli_help_lists_every_command(capsys):
    from caelestia_doctor import cli

    try:
        cli.main(["--help"])
    except SystemExit:
        pass
    out = capsys.readouterr().out
    for command in ("check", "deep-check", "fix", "restore", "install", "packages",
                    "backup", "undo", "logs", "command-check", "report"):
        assert command in out
