import subprocess

from caelestia_doctor import installer


def test_installer_declined_does_not_run_pacman(monkeypatch):
    monkeypatch.setattr(installer.shutil, "which", lambda cmd: "/usr/bin/pacman" if cmd == "pacman" else None)
    called = []
    rc = installer.install_optional_tools(ask=lambda _prompt: "n", is_tty=True,
                                          execute=lambda *a, **k: called.append(a))
    assert rc == 0
    assert called == []


def test_installer_requires_confirmation_then_verifies(monkeypatch):
    monkeypatch.setattr(installer.shutil, "which", lambda cmd: "/usr/bin/pacman" if cmd == "pacman" else None)
    answers = iter(("y",))
    calls = []

    def execute(args, check=False):
        calls.append((args, check))
        monkeypatch.setattr(installer.shutil, "which", lambda cmd: f"/usr/bin/{cmd}" if cmd in ("pacman", "less") else None)
        return subprocess.CompletedProcess(args, 0)

    assert installer.install_optional_tools(ask=lambda _p: next(answers), is_tty=True, execute=execute) == 0
    assert calls == [(["sudo", "pacman", "-S", "--needed", "less"], False)]


def test_installer_does_not_run_without_terminal(monkeypatch):
    monkeypatch.setattr(installer.shutil, "which", lambda cmd: "/usr/bin/pacman" if cmd == "pacman" else None)
    called = []
    rc = installer.install_optional_tools(is_tty=False, execute=lambda *a, **k: called.append(a))
    assert rc == 2
    assert not called
