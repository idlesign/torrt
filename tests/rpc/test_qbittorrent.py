import pytest

from torrt.rpc.qbittorrent import QBittorrentRPC


@pytest.fixture
def qbit():
    rpc = QBittorrentRPC(password='adminadmin')
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


def test_get_version(response_mock, qbit, torrent_params, torrent_data):

    with response_mock([
            f'POST {qbit.url}auth/login -> 200:Ok.',
            f'GET {qbit.url}app/webapiVersion -> 200:2.2',
        ],
        bypass=False
    ):
        response = qbit.method_get_version()
        assert response == '2.2'
