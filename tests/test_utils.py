import logging
import os
from collections.abc import Callable
from pathlib import Path
from stat import S_IMODE
from types import SimpleNamespace

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
def test_http_client_request_errors(
    response_mock: Callable, caplog: pytest.LogCaptureFixture,
    configured_silence: bool, override: bool | None, should_silence: bool,
) -> None:
    url = "https://service.invalid/status?session=review"
    error = ConnectionError(f"Connection failed for {url}")
    client = utils.HttpClient(silence_exceptions=configured_silence)
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

    assert f"Fetching {url} ..." in caplog.text
    assert f"Failed to get response from `{url}`: {error}" in caplog.text
    assert client.last_error == f"{error}"

def test_http_client_json_response(response_mock: Callable, caplog: pytest.LogCaptureFixture) -> None:
    url = "https://service.invalid/status"
    client = utils.HttpClient(json=True)
    caplog.set_level(logging.DEBUG, logger="torrt")

    with response_mock(f"GET {url} -> 200:{{\"ok\": true}}", bypass=False) as mocked:
        assert client.request(url) == {"ok": True}
        assert mocked.calls[0].request.url == url

    assert f"Fetching {url} ..." in caplog.text
    assert client.last_error == ""

def test_config_write_preserves_original_on_serialization_error() -> None:
    original = utils.TorrtConfig.USER_SETTINGS_FILE.read_bytes()
    settings = utils.TorrtConfig.load()
    settings["invalid"] = {"not serializable"}

    with pytest.raises(TypeError, match="not JSON serializable"):
        utils.TorrtConfig.save(settings)

    assert utils.TorrtConfig.USER_SETTINGS_FILE.read_bytes() == original
    assert not list(utils.TorrtConfig.USER_DATA_PATH.glob(".*.tmp"))

def test_config_write_preserves_original_on_replace_error(monkeypatch: pytest.MonkeyPatch) -> None:
    original = utils.TorrtConfig.USER_SETTINGS_FILE.read_bytes()

    def fail_replace(source: Path, target: Path) -> None:
        raise OSError("Replacement failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="Replacement failed"):
        utils.TorrtConfig.update({"prefer_magnet": True})

    assert utils.TorrtConfig.USER_SETTINGS_FILE.read_bytes() == original
    assert not list(utils.TorrtConfig.USER_DATA_PATH.glob(".*.tmp"))

def test_config_saves_private_complete_json() -> None:
    utils.TorrtConfig.update({"prefer_magnet": True})

    assert utils.TorrtConfig.load()["prefer_magnet"] is True
    assert utils.TorrtConfig.USER_SETTINGS_FILE.read_bytes().endswith(b"\n")

@pytest.mark.skipif(os.name == "nt", reason="POSIX file permissions are unavailable on Windows")
def test_config_write_keeps_private_permissions() -> None:
    utils.TorrtConfig.update({"prefer_magnet": True})

    assert S_IMODE(utils.TorrtConfig.USER_SETTINGS_FILE.stat().st_mode) == 0o600

def test_config_default_incomplete_operations_are_independent() -> None:
    settings = utils.TorrtConfig.load()
    settings.pop("incomplete")
    utils.TorrtConfig.save(settings)
    settings = utils.TorrtConfig.load()
    settings["incomplete"]["unsaved"] = {}

    assert utils.TorrtConfig.load()["incomplete"] == {}

def test_http_response_dump_preserves_bytes(response_mock: Callable, tmp_path: Path) -> None:
    body = b"\xff\x00\x80\r\nmagnet:?xt=urn:btih:review&tr=https://tracker.invalid/review/announce\r\n"
    client = utils.HttpClient()
    utils.GlobalParam.set("dump_into", tmp_path)

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", "https://rpc.invalid/status", body=body)
        response = client.request("https://rpc.invalid/status")

    assert response.content == body
    assert next(tmp_path.glob("*.txt")).read_bytes() == body
