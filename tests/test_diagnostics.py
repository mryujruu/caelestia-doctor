from caelestia_doctor import diagnostics
from caelestia_doctor.utils import INFO, WARN, Proc


def test_log_collection_reports_runtime_errors_as_review_warnings(monkeypatch):
    monkeypatch.setattr(diagnostics, "run", lambda command, timeout: Proc(0, "INFO started\nERROR bad config\n", ""))
    results = diagnostics.collect_runtime_logs()
    assert len(results) == 2
    assert all(result.status == WARN for result in results)
    assert "historical" in results[0].message
    assert "ERROR bad config" in results[0].detail


def test_missing_log_commands_are_informational(monkeypatch):
    monkeypatch.setattr(diagnostics, "run", lambda *_a, **_k: None)
    results = diagnostics.collect_runtime_logs()
    assert all(result.status == INFO for result in results)


def test_log_collection_redacts_home_from_details(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(diagnostics, "run", lambda *_a, **_k: Proc(0, f"log {tmp_path}/secret", ""))
    results = diagnostics.collect_runtime_logs()
    assert str(tmp_path) not in results[0].detail
    assert "~/secret" in results[0].detail
