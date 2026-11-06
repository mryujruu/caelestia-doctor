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


QKK_MIXED = """\
warning: bash: /etc/bash.bashrc (Modification time mismatch)
warning: bash: /etc/bash.bashrc (Size mismatch)
warning: bash: /etc/bash.bashrc (SHA256 checksum mismatch)
bash: 130 total files, 1 altered files
warning: dbus: /var/lib/dbus (Permissions mismatch)
warning: filesystem: /usr/share/man/man1/x.1.gz (No such file or directory)
warning: sudo: /etc/sudoers.d (Permission denied)
warning: foo: /usr/bin/foo (Size mismatch)
warning: foo: /usr/bin/foo (SHA256 checksum mismatch)
warning: bar: /usr/lib/bar.so (No such file or directory)
foo: 10 total files, 1 altered files
"""

QKK_HARMLESS = """\
warning: bash: /etc/bash.bashrc (SHA256 checksum mismatch)
warning: dbus: /var/lib/dbus (Permissions mismatch)
warning: dbus: /var/lib/dbus (Modification time mismatch)
warning: filesystem: /usr/share/locale/de/x.mo (No such file or directory)
warning: sudo: /etc/sudoers.d (Permission denied)
"""


def test_each_altered_file_is_counted_once_and_classified():
    data = arch.parse_pacman_qkk(QKK_MIXED)
    assert len(data["files"]) == 6  # three reasons for one file count as one file
    g = data["groups"]
    assert [x[1] for x in g["content"]] == ["/usr/bin/foo"]
    assert [x[1] for x in g["missing"]] == ["/usr/lib/bar.so"]
    assert [x[1] for x in g["config"]] == ["/etc/bash.bashrc"]
    assert [x[1] for x in g["removable"]] == ["/usr/share/man/man1/x.1.gz"]
    assert [x[1] for x in g["metadata"]] == ["/var/lib/dbus"]
    assert [x[1] for x in g["unreadable"]] == ["/etc/sudoers.d"]


def test_real_content_changes_outside_etc_warn_and_name_the_files():
    r = arch.summarize_pacman_qkk(QKK_MIXED)
    assert r.status == WARN
    assert "6 altered files" in r.message and "1 content changed outside /etc" in r.message
    steps = " ".join(r.steps)
    assert "/usr/bin/foo (package foo)" in steps and "/usr/lib/bar.so (package bar)" in steps
    assert "$ pacman -Qkk foo" in r.steps
    assert "$ sudo pacman -Qkk" in r.steps  # something could not be read without root


def test_expected_kinds_only_are_informational_not_a_warning():
    r = arch.summarize_pacman_qkk(QKK_HARMLESS)
    assert r.status == INFO
    assert "4 altered files" in r.message and "None of these need action" in r.message
    assert "deep-check --full" in " ".join(r.steps)


def test_nothing_altered_returns_nothing():
    assert arch.summarize_pacman_qkk("bash: 130 total files, 0 altered files\n") is None


def test_a_long_list_is_cut_but_points_to_full(monkeypatch):
    lines = "".join(f"warning: p{i}: /usr/bin/f{i} (Size mismatch)\n" for i in range(14))
    r = arch.summarize_pacman_qkk(lines)
    assert r.status == WARN and any("and 4 more" in s for s in r.steps)


def test_full_flag_prints_every_file(monkeypatch, capsys):
    from caelestia_doctor import cli
    from caelestia_doctor.utils import Result

    monkeypatch.setattr(cli.arch, "run_deep_checks",
                        lambda: [Result("Pacman file integrity", INFO, "x", detail="== config (1)\n/etc/a  [p: Size mismatch]")])
    assert cli.main(["--no-color", "deep-check", "--full"]) == 0
    out = capsys.readouterr().out
    assert "every file by category" in out and "/etc/a" in out
