import base64
import json
from collections.abc import Callable

import pytest
from requests import ConnectionError

from torrt.base_rpc import TorrentFile, TorrentStatus
from torrt.rpc.transmission import TransmissionRPC, TransmissionRPCException
from torrt.utils import TorrentData


@pytest.fixture
def transmission():
    rpc = TransmissionRPC()
    return rpc


def test_auth(response_mock):

    transmission = TransmissionRPC(user='wrong', password='wrongwrong')

    with response_mock(
        f'POST {transmission.url} -> 401:<h1>401: Unauthorized</h1>Unauthorized User',
        bypass=False
    ):
        with pytest.raises(TransmissionRPCException):
            transmission.method_get_version()


def test_get_version(response_mock, transmission):

    with response_mock(
        f'POST {transmission.url} -> 200:'
        '{"arguments":{"rpc-version":15,"rpc-version-minimum":1,"version":"2.94 (d8e60ee44f)"},"result":"success"}\n',
        bypass=False
    ):
        version = transmission.method_get_version()
        assert version == 15


def test_get_torrents(response_mock, transmission, datafix_read, torrent_params):

    with response_mock(
        f"POST {transmission.url} -> 200:{datafix_read('transm_gettorents.json')}",
        bypass=False
    ):
        response = transmission.method_get_torrents(hashes=['xxxxx'])
        assert response == [{
            'comment': 'somecomment',
            'downloadDir': '/home/idle',
            'hashString': 'xxxxx',
            'id': 1,
            'name': 'mytorr',
            'hash': 'xxxxx',
            'download_to': '/home/idle',
            'params': torrent_params,
        }]


def test_remove_torrent(response_mock, transmission):

    with response_mock(
        f'POST {transmission.url} -> 200:'
        '{"arguments":{},"result":"success"}',
        bypass=False
    ):
        response = transmission.method_remove_torrent(hash_str='xxxxx')
        assert response == {}


def test_add_torrent(response_mock, transmission, torrent_params, torrent_data):
    torrent_data.raw = torrent_data.parsed.to_string()

    with response_mock(
        f'POST {transmission.url} -> 200:'
        '{"arguments":{},"result":"success"}',
        bypass=False
    ) as mocked:
        response = transmission.method_add_torrent(
            torrent=torrent_data,
            download_to='/here/',
            params=torrent_params,
        )
        assert response == {}
        arguments = json.loads(mocked.calls[-1].request.body)["arguments"]
        assert base64.decodebytes(arguments["metainfo"].encode()) == torrent_data.raw
        assert arguments["files-unwanted"] == [0, 2]
        assert arguments["download-dir"] == "/here/"


@pytest.mark.parametrize("params", [
    None, {"files": {"old/file": {"exclude": False}}}, {"files": {"old/file": {"exclude": True}}},
])
def test_add_magnet(
    response_mock: Callable, transmission: TransmissionRPC, magnet_torrent: TorrentData, params: dict | None,
) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", transmission.url, json={"result": "success", "arguments": {}})

        assert transmission.method_add_torrent(magnet_torrent, download_to="/downloads", params=params) == {}
        assert json.loads(mocked.calls[-1].request.body) == {
            "method": "torrent-add", "arguments": {"filename": magnet_torrent.magnet, "download-dir": "/downloads"},
        }


@pytest.mark.parametrize("torrents, expected", [
    pytest.param([], None, id="absent"),
    pytest.param([{"hashString": "another_hash"}], None, id="wrong-hash"),
    pytest.param(
        [{"hashString": "REVIEW_HASH", "metadataPercentComplete": 0.5, "files": []}],
        TorrentStatus(hash="review_hash", metadata_ready=False), id="metadata-pending",
    ),
    pytest.param(
        [{"hashString": "REVIEW_HASH", "metadataPercentComplete": 1, "files": [{"name": "Review/one.avi"}]}],
        TorrentStatus(hash="review_hash", metadata_ready=True, files=(TorrentFile(index=0, name="Review/one.avi"),)),
        id="metadata-ready",
    ),
])
def test_get_torrent_status(
    response_mock: Callable, transmission: TransmissionRPC, torrents: list[dict], expected: TorrentStatus | None,
) -> None:

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", transmission.url, json={"result": "success", "arguments": {"torrents": torrents}})

        status = transmission.method_get_torrent_status("REVIEW_HASH")
        assert type(status) is type(expected)
        assert status == expected
        assert json.loads(mocked.calls[-1].request.body) == {
            "method": "torrent-get",
            "arguments": {"ids": ["review_hash"], "fields": ["hashString", "metadataPercentComplete", "files"]},
        }


@pytest.mark.parametrize("excluded_names, expected_indices", [
    pytest.param(["Review/one.avi", "Review/removed.avi"], [2], id="new-indices"),
    pytest.param(["Review/removed.avi"], [], id="removed-files"),
])
def test_apply_file_exclusions(
    response_mock: Callable, transmission: TransmissionRPC, excluded_names: list[str], expected_indices: list[int],
) -> None:
    status = TorrentStatus(
        hash="review_hash", metadata_ready=True,
        files=(
            TorrentFile(index=0, name="Review/three.avi"),
            TorrentFile(index=1, name="Review/two.avi"),
            TorrentFile(index=2, name="Review/one.avi"),
        ),
    )

    with response_mock([], bypass=False) as mocked:

        if expected_indices:
            mocked.add("POST", transmission.url, json={"result": "success", "arguments": {}})

        transmission.method_apply_file_exclusions(status, excluded_names)

        assert len(mocked.calls) == (1 if expected_indices else 0)

        if expected_indices:
            assert json.loads(mocked.calls[-1].request.body) == {
                "method": "torrent-set", "arguments": {"ids": ["review_hash"], "files-unwanted": expected_indices},
            }


def test_apply_exclusions_before_metadata_rejected(response_mock: Callable, transmission: TransmissionRPC) -> None:

    with response_mock([], bypass=False) as mocked:

        with pytest.raises(TransmissionRPCException, match="metadata is not available"):
            transmission.method_apply_file_exclusions(
                TorrentStatus(hash="review_hash", metadata_ready=False), ["Review/one.avi"],
            )

        assert len(mocked.calls) == 0


def test_empty_exclusions_skip_request(response_mock: Callable, transmission: TransmissionRPC) -> None:

    with response_mock([], bypass=False) as mocked:
        transmission.method_apply_file_exclusions(TorrentStatus(hash="review_hash", metadata_ready=False), [])

        assert len(mocked.calls) == 0


@pytest.mark.parametrize("failure", ["rpc", "http", "network"])
def test_add_magnet_errors(
    response_mock: Callable, transmission: TransmissionRPC, magnet_torrent: TorrentData, failure: str,
) -> None:
    error_message = "Review add failure"

    with response_mock([], bypass=False) as mocked:

        if failure == "rpc":
            mocked.add("POST", transmission.url, json={"result": error_message})

        elif failure == "http":
            mocked.add("POST", transmission.url, body=error_message, status=400)

        else:
            mocked.add("POST", transmission.url, body=ConnectionError(error_message))

        with pytest.raises(TransmissionRPCException, match=error_message):
            transmission.method_add_torrent(magnet_torrent)

        assert len(mocked.calls) == 1
