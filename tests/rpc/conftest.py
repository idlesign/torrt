import pytest

from torrt.toolbox import TorrentData
from torrt.utils import Torrent


@pytest.fixture
def torrent_data():

    return TorrentData(parsed=Torrent({
        'info': {
            'name': 'mytorr',
            'pieces': 1,
            'piece length': 1,
            'files': [
                {'length': 10, 'path': ['one.avi']},
                {'length': 20, 'path': ['two.avi']},
                {'length': 30, 'path': ['three.avi']},
                {'length': 40, 'path': ['four.avi']},
            ],
        }
    }))


@pytest.fixture
def torrent_params():
    return {
        'files': {
            'mytorr/one.avi': {'name': 'mytorr/one.avi', 'exclude': True, 'priority': 0},
            'mytorr/two.avi': {'name': 'mytorr/two.avi', 'exclude': False, 'priority': 0},
            'mytorr/three.avi': {'name': 'mytorr/three.avi', 'exclude': True, 'priority': 0}
        }
    }
