import pytest

from torrt.rpc.qbittorrent import QBittorrentRPC, QBittorrentRPCException


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
