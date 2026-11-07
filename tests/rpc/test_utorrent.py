import base64
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import pytest
from requests import ConnectionError
from responses import RequestsMock

from torrt.base_rpc import TorrentFile, TorrentStatus
from torrt.rpc.utorrent import UTorrentRPC, UTorrentRPCException
from torrt.utils import TorrentData


@pytest.fixture
def utorrent() -> UTorrentRPC:
    return UTorrentRPC(user="review", password="review_password")

def add_utorrent_responses(mocked: RequestsMock, rpc: UTorrentRPC, result: dict, *, method: str = "GET") -> None:
    mocked.add("GET", f"{rpc.url}token.html", body="<html><div id=token>review_csrf</div></html>")
    mocked.add(method, rpc.url, json=result)

@pytest.mark.parametrize("params, expected", [
    pytest.param({"optional": None}, {}, id="none"),
    pytest.param({"offset": 0}, {"offset": ["0"]}, id="zero"),
    pytest.param({"path": ""}, {"path": [""]}, id="empty"),
    pytest.param({"hash": ["one", "two"]}, {"hash": ["one", "two"]}, id="list"),
    pytest.param({"path": "/Загрузки/a & b"}, {"path": ["/Загрузки/a & b"]}, id="encoded-path"),
])
def test_get_request_url(utorrent: UTorrentRPC, params: dict, expected: dict[str, list[str]]) -> None:
    utorrent.csrf_token = "review+& token"

    url = utorrent.get_request_url(params)

    assert url.startswith(f"{utorrent.url}?")
    assert parse_qs(urlparse(url).query, keep_blank_values=True) == {"token": ["review+& token"], **expected}
    assert "None" not in url

def test_get_version(response_mock: Callable, utorrent: UTorrentRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"version": {"ui_version": "3.6"}})

        assert utorrent.method_get_version() == "3.6"
        assert utorrent.logged_in
        assert utorrent.csrf_token == "review_csrf"
        assert len(mocked.calls) == 2
        assert mocked.calls[0].request.url == f"{utorrent.url}token.html"
        assert parse_qs(urlparse(mocked.calls[1].request.url).query) == {
            "token": ["review_csrf"], "action": ["getversion"],
        }
        authorization = base64.b64encode(b"review:review_password").decode()

        for request in mocked.calls:
            assert request.request.headers["Authorization"] == f"Basic {authorization}"

def test_get_torrents(response_mock: Callable, utorrent: UTorrentRPC, torrent_data: TorrentData) -> None:
    torrent_row = [None] * 27
    torrent_row[0] = torrent_data.hash.upper()
    torrent_row[2] = torrent_data.name
    torrent_row[26] = "/downloads"
    other_row = list(torrent_row)
    other_row[0] = "OTHER_HASH"

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"torrents": [torrent_row, other_row]})

        assert utorrent.method_get_torrents(hashes=[torrent_data.hash]) == [{
            "hash": torrent_data.hash, "name": torrent_data.name, "download_to": "/downloads", "comment": "",
        }]
        assert parse_qs(urlparse(mocked.calls[-1].request.url).query) == {"token": ["review_csrf"], "list": ["1"]}

def test_add_torrent(
    response_mock: Callable, utorrent: UTorrentRPC, torrent_data: TorrentData, torrent_params: dict,
) -> None:
    download_to = "/Загрузки/review & files"
    torrent_data.raw = torrent_data.parsed.to_string()

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"result": "added"}, method="POST")

        result = utorrent.method_add_torrent(torrent_data, download_to=download_to, params=torrent_params)
        assert result == {"result": "added"}
        request = mocked.calls[-1].request
        assert parse_qs(urlparse(request.url).query) == {
            "token": ["review_csrf"], "action": ["add-file"], "path": [download_to],
        }
        assert request.headers["Content-Type"].startswith("multipart/form-data;")
        assert b"name=\"torrent_file\"; filename=\"from_torrt.torrent\"" in request.body
        assert torrent_data.raw in request.body

@pytest.mark.parametrize("with_data, action", [(False, "remove"), (True, "removedata")])
def test_remove_torrent(response_mock: Callable, utorrent: UTorrentRPC, with_data: bool, action: str) -> None:

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"result": "removed"})

        assert utorrent.method_remove_torrent("review_hash", with_data=with_data) == {"result": "removed"}
        assert parse_qs(urlparse(mocked.calls[-1].request.url).query) == {
            "token": ["review_csrf"], "action": [action], "hash": ["review_hash"],
        }

def test_login_network_error(response_mock: Callable, utorrent: UTorrentRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", f"{utorrent.url}token.html", body=ConnectionError("Review network failure"))

        with pytest.raises(UTorrentRPCException, match="Review network failure"):
            utorrent.method_get_version()

        assert not utorrent.logged_in

def test_login_without_token(response_mock: Callable, utorrent: UTorrentRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", f"{utorrent.url}token.html", body="<html><div id=token></div></html>")

        with pytest.raises(UTorrentRPCException, match="Unable to fetch CSRF token"):
            utorrent.method_get_version()

        assert not utorrent.logged_in


def test_add_magnet(response_mock: Callable, utorrent: UTorrentRPC, magnet_torrent: TorrentData) -> None:
    download_to = "/Загрузки/review & files"

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"build": 1})

        assert utorrent.method_add_torrent(magnet_torrent, download_to=download_to) == {"build": 1}
        request = mocked.calls[-1].request
        assert request.method == "GET"
        assert request.body is None
        assert parse_qs(urlparse(request.url).query) == {
            "token": ["review_csrf"], "action": ["add-url"], "s": [magnet_torrent.magnet], "path": [download_to],
        }


@pytest.mark.parametrize("present_hash, files, expected", [
    pytest.param(None, [], None, id="absent"),
    pytest.param("another_hash", [], None, id="wrong-hash"),
    pytest.param(
        "REVIEW_HASH", [], TorrentStatus(hash="review_hash", metadata_ready=False),
        id="metadata-pending",
    ),
    pytest.param(
        "REVIEW_HASH", [["Review/one.avi", 10, 0, 1]],
        TorrentStatus(hash="review_hash", metadata_ready=True, files=(TorrentFile(index=0, name="Review/one.avi"),)),
        id="metadata-ready",
    ),
])
def test_get_torrent_status(
    response_mock: Callable, utorrent: UTorrentRPC, present_hash: str | None, files: list[list],
    expected: TorrentStatus | None,
) -> None:
    torrent_row = [None] * 27
    torrent_row[0] = present_hash
    torrent_row[2] = "Review"
    torrent_row[26] = "/downloads"

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"torrents": [torrent_row] if present_hash else []})

        if expected:
            mocked.add("GET", utorrent.url, json={"files": ["REVIEW_HASH", files]})

        status = utorrent.method_get_torrent_status("REVIEW_HASH")
        assert type(status) is type(expected)
        assert status == expected
        assert len(mocked.calls) == (3 if expected else 2)

        if expected:
            assert parse_qs(urlparse(mocked.calls[-1].request.url).query) == {
                "token": ["review_csrf"], "action": ["getfiles"], "hash": ["review_hash"],
            }


@pytest.mark.parametrize("files", [[], ["another_hash", []]])
def test_get_torrent_status_rejects_unexpected_files(
    response_mock: Callable, utorrent: UTorrentRPC, files: list,
) -> None:
    torrent_row = [None] * 27
    torrent_row[0] = "review_hash"
    torrent_row[2] = "Review"
    torrent_row[26] = "/downloads"

    with response_mock([], bypass=False) as mocked:
        add_utorrent_responses(mocked, utorrent, {"torrents": [torrent_row]})
        mocked.add("GET", utorrent.url, json={"files": files})

        with pytest.raises(UTorrentRPCException, match="Unexpected torrent file response"):
            utorrent.method_get_torrent_status("review_hash")


@pytest.mark.parametrize("failure", ["rpc", "http", "network"])
def test_add_magnet_errors(
    response_mock: Callable, utorrent: UTorrentRPC, magnet_torrent: TorrentData, failure: str,
) -> None:
    error_message = "Review add failure"
    utorrent.logged_in = True
    utorrent.csrf_token = "review_csrf"

    with response_mock([], bypass=False) as mocked:

        if failure == "rpc":
            mocked.add("GET", utorrent.url, json={"error": error_message})

        elif failure == "http":
            mocked.add("GET", utorrent.url, body=error_message, status=400)

        else:
            mocked.add("GET", utorrent.url, body=ConnectionError(error_message))

        with pytest.raises(UTorrentRPCException, match=error_message):
            utorrent.method_add_torrent(magnet_torrent)

        assert len(mocked.calls) == 1
