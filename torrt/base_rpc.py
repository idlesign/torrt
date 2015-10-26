from torrt.utils import WithSettings, RPCObjectsRegistry
from torrt.exceptions import TorrtException


class BaseRPC(WithSettings):
    """Base RPC class. All RPC classes should inherit from this."""

    # class alias (required to work with registries)
    alias = None
    # entry name under which RPCs settings are stored
    config_entry_name = 'rpc'
    # mapping from torrent fields names in terms of RPC to field names in term of torrt
    torrent_fields_map = {}

    enabled = False

    def register(self):
        """Adds this object into RPCObjectsRegistry.

        :return:
        """
        RPCObjectsRegistry.add(self)

    @classmethod
    def normalize_field_names(cls, torrent_info):
        """Translates from torrent fields names in terms of RPC to field names in term of torrt.
        Updates accordingly a given torrent_info.

        :param torrent_info: dict
        :return:
        """
        for old_name, new_name in cls.torrent_fields_map.items():
            if old_name in torrent_info:
                torrent_info[new_name] = torrent_info[old_name]

    def method_get_torrents(self, hashes=None):
        """This should return a dictionary with torrents info from RPC.
        Each torrent info should be normaziled (see normalize_field_names()).

        :param hashes: list - torrent hashes
        :return: dict
        :rtype: dict
        """
        raise NotImplementedError(
            '`%s` class must implement `method_get_torrents()` method.' % self.__class__.__name__)

    def method_add_torrent(self, torrent, download_to=None):
        """Adds torrent to torrent client using RPC.

        :param torrent: str - torrent file contents
        :param download_to: str or None - path to download files from torrent into
        (in terms of torrent client filesystem)
        :return:
        """
        raise NotImplementedError(
            '`%s` class must implement `method_add_torrent()` method.' % self.__class__.__name__)

    def method_remove_torrent(self, hash_str, with_data=False):
        """Removes torrent from torrent client using RPC.

        :param hash_str: str - torrent identifying hash
        :param with_data: bool - flag to also remove files from torrent
        :return:
        """
        raise NotImplementedError(
            '`%s` class must implement `method_remove_torrent()` method.' % self.__class__.__name__)

    def method_get_version(self):
        """Returns torrent client API version.

        :return: str
        :rtype: str
        """
        raise NotImplementedError(
            '`%s` class must implement `method_get_version()` method.' % self.__class__.__name__)


class TorrtRPCException(TorrtException):
    """Base torrt RPC exception. All other RPC related exception should inherit from that."""
