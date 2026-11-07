import base64
import json
from collections.abc import Callable
from typing import Any

import pytest
from requests import ConnectionError
from responses import RequestsMock

from torrt.base_rpc import TorrentFile, TorrentStatus
from torrt.rpc.deluge import DelugeRPC, DelugeRPCException
from torrt.utils import TorrentData


@pytest.fixture
def deluge() -> DelugeRPC:
    return DelugeRPC(password="review_password")

def add_deluge_responses(mocked: RequestsMock, rpc: DelugeRPC, *results: Any) -> None:

    for result in (True, True, *results):
        mocked.add("POST", rpc.url, json={"id": 1, "result": result, "error": None})

def test_get_version(response_mock: Callable, deluge: DelugeRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, "2.0")

        assert deluge.method_get_version() == "2.0"
        assert deluge.logged_in
        assert [json.loads(request.request.body) for request in mocked.calls] == [
            {"id": 1, "method": "auth.login", "params": ["review_password"]},
            {"id": 1, "method": "auth.check_session", "params": []},
            {"id": 1, "method": "webapi.get_api_version", "params": []},
        ]

def test_login_rejected(response_mock: Callable, deluge: DelugeRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", deluge.url, json={"id": 1, "result": False, "error": None})

        assert deluge.method_login() is False
        assert not deluge.logged_in
        assert len(mocked.calls) == 1
        assert json.loads(mocked.calls[0].request.body)["params"] == ["review_password"]

def test_session_disconnected(response_mock: Callable, deluge: DelugeRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", deluge.url, json={"id": 1, "result": True, "error": None})
        mocked.add("POST", deluge.url, json={"id": 1, "result": False, "error": None})

        with pytest.raises(DelugeRPCException, match="not connected to a daemon"):
            deluge.method_get_version()

        assert json.loads(mocked.calls[-1].request.body)["method"] == "auth.check_session"
        assert len(mocked.calls) == 2

def test_get_torrents(response_mock: Callable, deluge: DelugeRPC) -> None:
    torrent = {"hash": "review_hash", "name": "Review", "comment": "Review comment", "save_path": "/downloads"}

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, {"torrents": [torrent]})

        assert deluge.method_get_torrents(hashes=["review_hash"]) == [{**torrent, "download_to": "/downloads"}]
        assert json.loads(mocked.calls[-1].request.body) == {
            "id": 1, "method": "webapi.get_torrents",
            "params": [["review_hash"], ["name", "comment", "hash", "save_path"]],
        }

@pytest.mark.parametrize("download_to", ["", "/Загрузки/review & files"])
def test_add_torrent(
    response_mock: Callable, deluge: DelugeRPC, torrent_data: TorrentData, torrent_params: dict, download_to: str,
) -> None:
    torrent_data.raw = torrent_data.parsed.to_string()

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, "added")

        assert deluge.method_add_torrent(torrent_data, download_to=download_to, params=torrent_params) == "added"
        payload = json.loads(mocked.calls[-1].request.body)
        assert payload["method"] == "webapi.add_torrent"
        assert payload["id"] == 1
        assert len(payload["params"]) == 2
        assert base64.decodebytes(payload["params"][0].encode()) == torrent_data.raw
        assert payload["params"][1] == {"download_location": download_to or None}

@pytest.mark.parametrize("with_data", [False, True])
def test_remove_torrent(response_mock: Callable, deluge: DelugeRPC, with_data: bool) -> None:

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, True)

        assert deluge.method_remove_torrent("review_hash", with_data=with_data) is True
        assert json.loads(mocked.calls[-1].request.body) == {
            "id": 1, "method": "webapi.remove_torrent", "params": ["review_hash", with_data],
        }

def test_network_error(response_mock: Callable, deluge: DelugeRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", deluge.url, body=ConnectionError("Review network failure"))

        with pytest.raises(DelugeRPCException, match="Review network failure"):
            deluge.method_get_version()

def test_rpc_error(response_mock: Callable, deluge: DelugeRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge)
        mocked.add("POST", deluge.url, json={"id": 1, "result": None, "error": "Review RPC error"})

        with pytest.raises(DelugeRPCException, match="Review RPC error"):
            deluge.method_get_version()


def test_add_magnet(response_mock: Callable, deluge: DelugeRPC, magnet_torrent: TorrentData) -> None:

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, magnet_torrent.hash)

        assert deluge.method_add_torrent(magnet_torrent, download_to="/downloads") == magnet_torrent.hash
        assert json.loads(mocked.calls[-1].request.body) == {
            "id": 1, "method": "webapi.add_torrent",
            "params": [magnet_torrent.magnet, {"download_location": "/downloads"}],
        }


@pytest.mark.parametrize("result", [None, False])
def test_add_magnet_rejected(
    response_mock: Callable, deluge: DelugeRPC, magnet_torrent: TorrentData, result: Any,
) -> None:

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, result)

        with pytest.raises(DelugeRPCException, match="did not accept the magnet"):
            deluge.method_add_torrent(magnet_torrent)



@pytest.mark.parametrize("torrents, expected", [
    pytest.param([], None, id="absent"),
    pytest.param([{"hash": "another_hash"}], None, id="wrong-hash"),
    pytest.param(
        [{"hash": "REVIEW_HASH", "files": []}],
        TorrentStatus(hash="review_hash", metadata_ready=False), id="metadata-pending",
    ),
    pytest.param(
        [{"hash": "REVIEW_HASH", "files": [{"index": 3, "path": "Review/one.avi"}]}],
        TorrentStatus(hash="review_hash", metadata_ready=True, files=(TorrentFile(index=3, name="Review/one.avi"),)),
        id="metadata-ready",
    ),
])
def test_get_torrent_status(
    response_mock: Callable, deluge: DelugeRPC, torrents: list[dict], expected: TorrentStatus | None,
) -> None:

    with response_mock([], bypass=False) as mocked:
        add_deluge_responses(mocked, deluge, {"torrents": torrents})

        status = deluge.method_get_torrent_status("REVIEW_HASH")
        assert type(status) is type(expected)
        assert status == expected
        assert json.loads(mocked.calls[-1].request.body) == {
            "id": 1, "method": "webapi.get_torrents", "params": [["review_hash"], ["hash", "files"]],
        }
