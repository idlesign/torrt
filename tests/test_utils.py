import logging
from collections.abc import Callable
from types import SimpleNamespace
from urllib.parse import quote, quote_plus

import pytest
from requests import ConnectionError

import torrt.utils as utils
from torrt.trackers.anidub import AniDUBTracker
from torrt.trackers.rutracker import RuTrackerTracker


def test_base64encode_str():
    string_to_encode = 'this is string'
    encoded_bytes = utils.base64encode(string_to_encode)

    assert isinstance(encoded_bytes, bytes)
    assert encoded_bytes == b'dGhpcyBpcyBzdHJpbmc=\n'


def test_base64encode_bytes():
    bytes_to_encode = b'this is bytes to encode'
    encoded_bytes = utils.base64encode(bytes_to_encode)

    assert isinstance(encoded_bytes, bytes)
    assert encoded_bytes == b'dGhpcyBpcyBieXRlcyB0byBlbmNvZGU=\n'


def test_save_settings(mock_config):
    RuTrackerTracker(username='user', password='pass', query_string='qs').save_settings()

    assert mock_config['trackers']['rutracker.org'] == {
        'username': 'user',
        'password': 'pass',
        'cookies': {},
        'query_string': 'qs',
    }

def test_registry_respects_tracker_rejection() -> None:
    registry = utils.ObjectsRegistry()
    tracker = AniDUBTracker()
    registry.add(tracker)

    assert registry.get_for_string("https://attacker.invalid/tr.anidub.com/") is None
    assert registry.get_for_string("https://tr.anidub.com/review") is tracker

def test_registry_matches_objects_without_can_handle() -> None:
    registry = utils.ObjectsRegistry()
    registered = SimpleNamespace(alias="legacy")
    registry.add(registered)

    assert registry.get_for_string("legacy item") is registered
    assert registry.get_for_string("unknown item") is None
    assert registry.get_for_string(None) is None

@pytest.mark.parametrize("configured_silence, override, should_silence", [
    pytest.param(True, None, True, id="configured-silent"),
    pytest.param(False, None, False, id="configured-raising"),
    pytest.param(True, False, False, id="override-raising"),
    pytest.param(False, True, True, id="override-silent"),
])
def test_http_client_redacts_request_errors(
    response_mock: Callable, caplog: pytest.LogCaptureFixture,
    configured_silence: bool, override: bool | None, should_silence: bool,
) -> None:
    secret = "123:review/secret +"
    encoded_secret = quote(secret, safe="")
    url = f"https://service.invalid/bot{encoded_secret}/status"
    error = ConnectionError(f"Connection failed for {url}: {secret}; {quote_plus(secret)}")
    client = utils.HttpClient(silence_exceptions=configured_silence, sensitive_values=("", secret))
    caplog.set_level(logging.DEBUG, logger="torrt")

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", url, body=error)

        if should_silence:
            assert client.request(url, silence_exceptions=override) is None

        else:

            with pytest.raises(ConnectionError, match="Connection failed") as raised:
                client.request(url, silence_exceptions=override)

            assert raised.value is error

        assert mocked.calls[0].request.url == url

    for value in (secret, encoded_secret, quote_plus(secret)):
        assert value not in caplog.text
        assert value not in client.last_error

    assert "Fetching https://service.invalid/bot[REDACTED]/status" in caplog.text
    assert "Failed to get response" in caplog.text
    assert "Connection failed" in client.last_error
    assert "[REDACTED]" in client.last_error

def test_http_client_redacts_successful_request(response_mock: Callable, caplog: pytest.LogCaptureFixture) -> None:
    secret = "123:review_secret"
    url = f"https://service.invalid/bot{secret}/status"
    client = utils.HttpClient(json=True, sensitive_values=(secret,))
    caplog.set_level(logging.DEBUG, logger="torrt")

    with response_mock(f"GET {url} -> 200:{{\"ok\": true}}", bypass=False) as mocked:
        assert client.request(url) == {"ok": True}
        assert mocked.calls[0].request.url == url

    assert secret not in caplog.text
    assert "Fetching https://service.invalid/bot[REDACTED]/status" in caplog.text
    assert client.last_error == ""
