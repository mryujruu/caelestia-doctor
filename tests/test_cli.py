import pytest

from caelestia_doctor import cli
from caelestia_doctor.utils import FAIL, OK, WARN, Repair, Result


def _empty_file_result(path):
    if path.read_text():
        return Result(path.name, OK, "valid")
    return Result(path.name, WARN, "empty",
                  repair=Repair(path, "write an empty object", lambda: path.write_text("{}\n")))


def answers(monkeypatch, *values):
    it = iter(values)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))
    monkeypatch.setattr(cli, "_interactive", lambda: True)


def test_fix_can_apply_all_safe_repairs(tmp_path, monkeypatch, capsys):
    path = tmp_path / "shell.json"
    path.write_text("")
    monkeypatch.setattr(cli, "run_all", lambda: [_empty_file_result(path)])
    answers(monkeypatch, "a", "y")

    assert cli.main(["fix"]) == 0
    assert path.read_text() == "{}\n"
    assert "Backup:" in capsys.readouterr().out


def test_fix_can_apply_one_selected_repair(tmp_path, monkeypatch):
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text("")
    second.write_text("")
    monkeypatch.setattr(cli, "run_all", lambda: [_empty_file_result(first), _empty_file_result(second)])
    answers(monkeypatch, "2", "y")

    assert cli.main(["fix"]) == 0
    assert first.read_text() == ""
    assert second.read_text() == "{}\n"


@pytest.mark.parametrize("reply", ["n", "", "7", "abc"])
def test_fix_changes_nothing_on_cancel_or_bad_input(tmp_path, monkeypatch, reply):
    path = tmp_path / "shell.json"
    path.write_text("")
    monkeypatch.setattr(cli, "run_all", lambda: [_empty_file_result(path)])
    answers(monkeypatch, reply)
    cli.main(["fix"])
    assert path.read_text() == ""


def test_fix_does_not_apply_without_final_yes(tmp_path, monkeypatch):
    path = tmp_path / "shell.json"
    path.write_text("")
    monkeypatch.setattr(cli, "run_all", lambda: [_empty_file_result(path)])
    answers(monkeypatch, "a", "no")
    cli.main(["fix"])
    assert path.read_text() == ""


def test_fix_survives_closed_stdin(tmp_path, monkeypatch):
    path = tmp_path / "shell.json"
    path.write_text("")
    monkeypatch.setattr(cli, "run_all", lambda: [_empty_file_result(path)])
    monkeypatch.setattr(cli, "_interactive", lambda: True)

    def eof(_prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    cli.main(["fix"])  # must not raise
    assert path.read_text() == ""


def test_fix_refuses_when_not_interactive(tmp_path, monkeypatch):
    path = tmp_path / "shell.json"
    path.write_text("")
    monkeypatch.setattr(cli, "run_all", lambda: [_empty_file_result(path)])
    monkeypatch.setattr(cli, "_interactive", lambda: False)
    assert cli.main(["fix"]) == 2
    assert path.read_text() == ""


def test_check_exit_code_and_plain_output(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run_all", lambda: [Result("x", FAIL, "broken", steps=["$ echo hi"])])
    assert cli.main(["--no-color", "check"]) == 1
    out = capsys.readouterr().out
    assert "\033[" not in out and "What to do" in out and "$ echo hi" in out


def test_report_goes_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run_all", lambda: [Result("x", WARN, "hmm", "why", steps=["$ ls"])])
    target = tmp_path / "r.md"
    assert cli.main(["report", "-o", str(target)]) == 0
    text = target.read_text()
    assert "Suggested fixes" in text and "```sh" in text
