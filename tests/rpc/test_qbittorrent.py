from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import pytest
from requests import ConnectionError

from torrt.base_rpc import TorrentFile, TorrentStatus
from torrt.rpc.qbittorrent import QBittorrentRPC, QBittorrentRPCException
from torrt.utils import TorrentData


@pytest.fixture
def qbit():
    rpc = QBittorrentRPC(password='adminadmin')
    return rpc


def test_get_torrents(response_mock, qbit, torrent_params):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'GET {qbit.url}torrents/info -> 200:'
            '[{"hash": "xxxxx", "name": "mytorr", "save_path": "/home/idle", "category": "tv"}]',
            f'POST {qbit.url}torrents/properties -> 200:' + '{"comment": "somecomment"}',
        ],
        bypass=False
    ):
        response = qbit.method_get_torrents(hashes=['xxxxx'])
        assert response == [{
            'comment': 'somecomment',
            'name': 'mytorr',
            'hash': 'xxxxx',
            'download_to': '/home/idle',
            'params': {'category': 'tv'},
        }]


def test_get_torrents_no_category(response_mock, qbit, torrent_params):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'GET {qbit.url}torrents/info -> 200:'
            '[{"hash": "xxxxx", "name": "mytorr", "save_path": "/home/idle", "category": ""}]',
            f'POST {qbit.url}torrents/properties -> 200:' + '{"comment": "somecomment"}',
        ],
        bypass=False
    ):
        response = qbit.method_get_torrents(hashes=['xxxxx'])
        assert response == [{
            'comment': 'somecomment',
            'name': 'mytorr',
            'hash': 'xxxxx',
            'download_to': '/home/idle',
            'params': {},
        }]


def test_add_torrent(response_mock, qbit, torrent_params, torrent_data):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'POST {qbit.url}torrents/add -> 200:',
        ],
        bypass=False
    ):
        response = qbit.method_add_torrent(
            torrent=torrent_data,
            download_to='/here/',
            params=torrent_params,
        )
        assert response.ok


def test_remove_torrent(response_mock, qbit, torrent_params, torrent_data):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'POST {qbit.url}torrents/delete -> 200:',
        ],
        bypass=False
    ):
        response = qbit.method_remove_torrent(
            hash_str='3dc61b1936e55d983ad774bf59b932b0a31eedd3',
            with_data=True,
        )
        assert response.ok


def test_login_qbittorrent_5(response_mock, qbit, torrent_params):
    """qBittorrent 5.x replies to a successful login with 204 and an empty body."""

    with response_mock([
            f'POST {qbit.url}auth/login -> 204:',
            f'GET {qbit.url}app/webapiVersion -> 200:2.11',
        ],
        bypass=False
    ):
        assert qbit.method_get_version() == '2.11'
        assert qbit.logged_in


def test_login_failed(response_mock, qbit, torrent_params):
    """Wrong credentials are still reported as a failure."""

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Fails.',
        ],
        bypass=False
    ):
        with pytest.raises(QBittorrentRPCException):
            qbit.login()

        assert not qbit.logged_in


def test_get_version(response_mock, qbit, torrent_params, torrent_data):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'GET {qbit.url}app/webapiVersion -> 200:2.2',
        ],
        bypass=False
    ):
        response = qbit.method_get_version()
        assert response == '2.2'


def test_add_magnet(response_mock: Callable, qbit: QBittorrentRPC, magnet_torrent: TorrentData) -> None:
    magnet_torrent.set_params({"category": "from_page"})

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", f"{qbit.url}auth/login", body="Ok.")
        mocked.add("POST", f"{qbit.url}torrents/add", body="Ok.")

        assert qbit.method_add_torrent(
            magnet_torrent, download_to="/Загрузки/review & files", params={"category": "old_category"},
        ).ok
        request = mocked.calls[-1].request
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert parse_qs(request.body) == {
            "urls": [magnet_torrent.magnet], "category": ["from_page"], "savepath": ["/Загрузки/review & files"],
        }


def test_add_magnet_rejected(response_mock: Callable, qbit: QBittorrentRPC, magnet_torrent: TorrentData) -> None:
    qbit.logged_in = True

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", f"{qbit.url}torrents/add", body="Fails.")

        with pytest.raises(QBittorrentRPCException, match="did not accept the magnet"):
            qbit.method_add_torrent(magnet_torrent)



@pytest.mark.parametrize("torrents, files, expected", [
    pytest.param([], [], None, id="absent"),
    pytest.param([{"hash": "another_hash"}], [], None, id="wrong-hash"),
    pytest.param(
        [{"hash": "REVIEW_HASH"}], [], TorrentStatus(hash="review_hash", metadata_ready=False),
        id="metadata-pending",
    ),
    pytest.param(
        [{"hash": "REVIEW_HASH"}], [{"index": 3, "name": "Review/one.avi"}, {"name": "Review/two.avi"}],
        TorrentStatus(
            hash="review_hash", metadata_ready=True,
            files=(TorrentFile(index=3, name="Review/one.avi"), TorrentFile(index=1, name="Review/two.avi")),
        ),
        id="metadata-ready",
    ),
])
def test_get_torrent_status(
    response_mock: Callable, qbit: QBittorrentRPC, torrents: list[dict], files: list[dict],
    expected: TorrentStatus | None,
) -> None:
    qbit.logged_in = True

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", f"{qbit.url}torrents/info", json=torrents)

        if expected:
            mocked.add("POST", f"{qbit.url}torrents/files", json=files)

        status = qbit.method_get_torrent_status("REVIEW_HASH")
        assert type(status) is type(expected)
        assert status == expected
        assert len(mocked.calls) == (2 if expected else 1)
        assert parse_qs(urlparse(mocked.calls[0].request.url).query) == {"hashes": ["review_hash"]}
        assert mocked.calls[0].request.body is None

        if expected:
            assert parse_qs(mocked.calls[-1].request.body) == {"hash": ["review_hash"]}


@pytest.mark.parametrize("failure", ["http", "network"])
def test_add_magnet_errors(
    response_mock: Callable, qbit: QBittorrentRPC, magnet_torrent: TorrentData, failure: str,
) -> None:
    error_message = "Review add failure"
    qbit.logged_in = True

    with response_mock([], bypass=False) as mocked:

        if failure == "http":
            mocked.add("POST", f"{qbit.url}torrents/add", body=error_message, status=400)

        else:
            mocked.add("POST", f"{qbit.url}torrents/add", body=ConnectionError(error_message))

        with pytest.raises(QBittorrentRPCException, match=error_message):
            qbit.method_add_torrent(magnet_torrent)

        assert len(mocked.calls) == 1
