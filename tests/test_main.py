from os.path import dirname, realpath, join

from torrentool.torrent import Torrent

from torrt.base_rpc import BaseRPC
from torrt.base_tracker import GenericPublicTracker
from torrt.toolbox import bootstrap, TrackerClassesRegistry, NotifierClassesRegistry, RPCClassesRegistry, \
    configure_rpc, configure_tracker, add_torrent_from_url, get_registered_torrents, walk, remove_torrent, toggle_rpc
from torrt.utils import RPCObjectsRegistry, TorrentData

CURRENT_DIR = dirname(realpath(__file__))


def test_basic():
    assert TrackerClassesRegistry.get()
    assert NotifierClassesRegistry.get()
    assert RPCClassesRegistry.get()


class DummyTracker(GenericPublicTracker):

    alias = 'dummy.local'
    mirrors = ['dummy-a.local']

    def get_download_link(self, url):
        return url


TrackerClassesRegistry.add(DummyTracker)


class DummyRPC(BaseRPC):

    alias = 'dummy'

    def __init__(self, enabled=False):
        self.enabled = enabled
        self.torrents = {}
        super().__init__()

    def method_add_torrent(self, torrent: TorrentData, download_to: str = None, params: dict = None):
        parsed = Torrent.from_string(torrent.raw)
        self.torrents[parsed.info_hash] = parsed

    def method_remove_torrent(self, hash_str, with_data=False):
        self.torrents.pop(hash_str)

    def method_get_torrents(self, hashes=None):
        results = []

        for hash_str, parsed in self.torrents.items():

            if hash_str not in hashes:
                continue

            results.append({
                'id': parsed.info_hash,
                'name': parsed.name,
                'hash': parsed.info_hash,
                'download_to': None,
                'comment': 'http://dummy-a.local/id/one',
            })

        return results

    def method_get_version(self):
        return '0.0.1'


def test_fullcycle(monkeypatch, datafix_dir):

    # todo Dummy notifier
    # todo Dummy bot

    from torrt.utils import TorrtConfig

    class DummyConfig(TorrtConfig):

        cfg = TorrtConfig._basic_settings

        @classmethod
        def bootstrap(cls):
            pass

        @classmethod
        def load(cls):
            return cls.cfg

        @classmethod
        def save(cls, settings_dict):
            cls.cfg = settings_dict

    def patch_requests(response_contents):
        monkeypatch.setattr('torrt.utils.Session.get', lambda self, url, **kwargs: DummyResponse(url, response_contents))

    torrent_one_hash = 'c815be93f20bf8b12fed14bee35c14b19b1d1984'
    torrent_one_data = (datafix_dir / 'torr_one.torrent').read_bytes()

    torrent_two_hash = '65f491bbdef45a26388a9337a91826a75c4c59fb'
    torrent_two_data = (datafix_dir / 'torr_two.torrent').read_bytes()

    class DummyResponse(object):

        def __init__(self, url, data):
            self.url = url
            self.data = data

        @property
        def content(self):
            return self.data

    patch_requests(torrent_one_data)

    monkeypatch.setattr('torrt.utils.config', DummyConfig)
    monkeypatch.setattr('torrt.toolbox.config', DummyConfig)

    rpc_old = RPCObjectsRegistry._items
    RPCObjectsRegistry._items = {}

    try:
        configure_tracker('dummy.local', {})

        assert configure_rpc('dummy', {}).enabled

        toggle_rpc('dummy')  # Enable RPC in config.

        bootstrap()
        rpc_dummy = RPCObjectsRegistry.get('dummy')

        # Add new torrent.
        add_torrent_from_url('http://dummy-a.local/id/one')

        assert len(rpc_dummy.torrents) == 1
        assert torrent_one_hash in rpc_dummy.torrents
        assert torrent_one_hash in get_registered_torrents()

        # Walk and update.
        patch_requests(torrent_two_data)
        walk(forced=True)

        assert len(rpc_dummy.torrents) == 1
        assert torrent_two_hash in rpc_dummy.torrents

        # Remove updated.
        remove_torrent(torrent_two_hash)

        assert not rpc_dummy.torrents
        assert torrent_one_hash not in get_registered_torrents()
        assert torrent_two_hash not in get_registered_torrents()

    finally:
        RPCObjectsRegistry._items = rpc_old
