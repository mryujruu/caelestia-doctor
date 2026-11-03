from caelestia_doctor.report import redact, render_markdown, render_text
from caelestia_doctor.utils import FAIL, OK, WARN, Repair, Result


def test_text_shows_steps_commands_and_repairs():
    rs = [
        Result("A", FAIL, "bad thing", "because", steps=["Do this:", "$ run-me"]),
        Result("B", WARN, "meh", repair=Repair(__import__("pathlib").Path("/x"), "change x to y", lambda: None)),
        Result("C", OK, "fine"),
    ]
    out = render_text(rs, color=False, width=80)
    assert "What to do" in out and "$ run-me" in out
    assert "Can be fixed automatically" in out and "change x to y" in out
    assert "1 problem" in out and "1 warning" in out
    assert "\033[" not in out


def test_color_output_uses_ansi():
    assert "\033[" in render_text([Result("A", FAIL, "x")], color=True)


def test_markdown_has_code_block_for_commands():
    md = render_markdown([Result("A", FAIL, "bad", steps=["note", "$ ls -la"])])
    assert "```sh\nls -la\n```" in md and "- note" in md


def test_redact_removes_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert redact(f"see {tmp_path}/x") == "see ~/x"
