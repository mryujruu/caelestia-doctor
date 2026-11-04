import io
import urllib.error

import pytest

from caelestia_doctor import restore


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def capture(monkeypatch, body=b"{}"):
    seen = []

    def fake_urlopen(request, timeout=None):
        seen.append(request)
        return FakeResponse(body)

    monkeypatch.setattr(restore.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_no_token_means_no_authorization_header(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    seen = capture(monkeypatch)
    restore._request(restore.API + "/commits/main")
    assert seen[0].get_header("Authorization") is None


def test_token_is_sent_only_to_the_api_host(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    seen = capture(monkeypatch)
    restore._request(restore.API + "/commits/main")
    restore._request(restore.RAW + "/abc/manifest.toml")
    assert seen[0].get_header("Authorization") == "Bearer t0ken"
    assert seen[1].get_header("Authorization") is None


@pytest.mark.parametrize("code", [403, 429])
def test_rate_limit_gives_a_helpful_message(monkeypatch, code):
    def boom(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, code, "Forbidden", {}, None)

    monkeypatch.setattr(restore.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError) as info:
        restore._request(restore.API + "/commits/main")
    assert "GITHUB_TOKEN" in str(info.value) and str(code) in str(info.value)


def test_other_http_errors_are_not_hidden(monkeypatch):
    def boom(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(restore.urllib.request, "urlopen", boom)
    with pytest.raises(urllib.error.HTTPError):
        restore._request(restore.API + "/commits/main")
