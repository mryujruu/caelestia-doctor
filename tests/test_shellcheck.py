from caelestia_doctor import shellcheck
from caelestia_doctor.utils import FAIL, OK, WARN, Proc


def test_fish_bash_assignment_is_identified_and_suggested(monkeypatch):
    monkeypatch.setattr(shellcheck, "have", lambda cmd: cmd == "fish")
    calls = []

    def run(command, timeout):
        calls.append(command)
        return Proc(127, "", "Unsupported use of '='. In fish, use set.")

    monkeypatch.setattr(shellcheck, "run", run)
    result = shellcheck.check_command('backup="$HOME/archive.tar.gz"')[0]
    assert result.status == FAIL
    assert "set backup \"$HOME/archive.tar.gz\"" in result.steps
    assert calls[0][:3] == ["fish", "--no-config", "--no-execute"]


def test_valid_fish_pipeline_reports_missing_less(monkeypatch):
    monkeypatch.setattr(shellcheck, "have", lambda cmd: cmd == "fish")
    monkeypatch.setattr(shellcheck, "run", lambda *_a, **_k: Proc(0, "", ""))
    results = shellcheck.check_command('tar -tzf "$backup" | less')
    assert results[0].status == OK
    assert results[1].status == WARN
    assert "not installed" in results[1].message


def test_parser_error_does_not_offer_rewrite_for_arbitrary_text(monkeypatch):
    monkeypatch.setattr(shellcheck, "have", lambda cmd: cmd == "fish")
    monkeypatch.setattr(shellcheck, "run", lambda *_a, **_k: Proc(1, "", "parse error"))
    result = shellcheck.check_command("if test x\n echo x")[0]
    assert result.status == FAIL
    assert not any("Suggested Fish form" in step for step in result.steps)
