import pytest

from torrt.rpc.transmission import TransmissionRPC, TransmissionRPCException


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

    with response_mock(
        f'POST {transmission.url} -> 200:'
        '{"arguments":{},"result":"success"}',
        bypass=False
    ):
        response = transmission.method_add_torrent(
            torrent=torrent_data,
            download_to='/here/',
            params=torrent_params,
        )
        assert response == {}
