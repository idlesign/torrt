from torrt.utils import TorrtException, WithSettings, RPCObjectsRegistry


class BaseRPC(WithSettings):
    """"""

    alias = None
    config_entry_name = 'rpc'
    fields_map = {}
    enabled = False

    def register(self):
        RPCObjectsRegistry.add(self)

    @classmethod
    def normalize_field_names(cls, torrent_info):
        for old_name, new_name in cls.fields_map.items():
            if old_name in torrent_info:
                torrent_info[new_name] = torrent_info[old_name]

    def method_get_torrents(self, hashes=None):
        raise NotImplementedError('`%s` class must implement `method_get_torrents()` method.' % self.__class__.__name__)

    def method_add_torrent(self, torrent, download_to=None):
        raise NotImplementedError('`%s` class must implement `method_add_torrent()` method.' % self.__class__.__name__)

    def method_remove_torrent(self, hash, with_data=False):
        raise NotImplementedError('`%s` class must implement `method_remove_torrent()` method.' % self.__class__.__name__)

    def method_get_version(self):
        raise NotImplementedError('`%s` class must implement `method_get_version()` method.' % self.__class__.__name__)


class TorrtRPCException(TorrtException):
    """"""
