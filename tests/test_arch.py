from caelestia_doctor.checks import arch
from caelestia_doctor.utils import INFO, OK, WARN, Proc


def test_package_file_check_clean(monkeypatch):
    monkeypatch.setattr(arch, "run", lambda *args, **kwargs: Proc(0, "", ""))
    result = arch._pacman_files_check()
    assert result.status == OK
    assert "present" in result.message


def test_package_file_check_reports_missing_paths(monkeypatch):
    monkeypatch.setattr(arch, "run", lambda *args, **kwargs: Proc(0, "core/foo /usr/bin/foo\n", ""))
    result = arch._pacman_files_check()
    assert result.status == WARN
    assert "1 package-owned" in result.message
    assert "/usr/bin/foo" in result.detail
    assert "$ sudo pacman -S <package>" in result.steps


def test_package_file_check_timeout_is_informational(monkeypatch):
    monkeypatch.setattr(arch, "run", lambda *args, **kwargs: Proc(124, "", "timed out"))
    result = arch._pacman_files_check()
    assert result.status == INFO
    assert "timed out" in result.message


def test_deep_package_check_reports_altered_files(monkeypatch):
    monkeypatch.setattr(arch, "have", lambda _cmd: True)
    monkeypatch.setattr(arch, "run", lambda *args, **kwargs: Proc(0, "foo: 20 total files, 2 altered files\n", ""))
    result = arch.run_deep_checks()[0]
    assert result.status == WARN
    assert "2 altered" in result.message


def test_deep_package_check_uses_c_locale(monkeypatch):
    monkeypatch.setattr(arch, "have", lambda _cmd: True)
    calls = []

    def run(*args, **kwargs):
        calls.append(kwargs["env"].get("LC_ALL"))
        return Proc(0, "", "")

    monkeypatch.setattr(arch, "run", run)
    assert arch.run_deep_checks()[0].status == OK
    assert calls == ["C"]
