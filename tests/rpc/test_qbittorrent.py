import pytest

from torrt.rpc.qbittorrent import QBittorrentRPC


@pytest.fixture
def qbit():
    rpc = QBittorrentRPC()
    return rpc


def test_get_torrents(response_mock, qbit, torrent_params):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'GET {qbit.url}torrents/info -> 200:' + '[{"hash": "xxxxx", "name": "mytorr", "save_path": "/home/idle"}]',
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
