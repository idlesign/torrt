from typing import Dict, List

from .utils import WithSettings, RPCObjectsRegistry


class BaseRPC(WithSettings):
    """Base RPC class. All RPC classes should inherit from this."""

    config_entry_name: str = 'rpc'

    torrent_fields_map: Dict[str, str] = {}
    """mapping from torrent fields names in terms of RPC to field names in term of torrt"""

    enabled: bool = False

    def register(self):
        """Adds this object into RPCObjectsRegistry."""

        RPCObjectsRegistry.add(self)

    @classmethod
    def normalize_field_names(cls, torrent_info: dict):
        """Translates from torrent fields names in terms of RPC to field names in term of torrt.
        Updates accordingly a given torrent_info inplace.

        :param torrent_info:

        """
        for old_name, new_name in cls.torrent_fields_map.items():
            if old_name in torrent_info:
                torrent_info[new_name] = torrent_info[old_name]

    def method_get_torrents(self, hashes: List[str] = None) -> dict:
        """This should return a dictionary with torrents info from RPC.
        Each torrent info should be normalized (see normalize_field_names()).

        :param hashes: torrent hashes

        """
        raise NotImplementedError  # pragma: nocover

    def method_add_torrent(self, torrent: str, download_to: str = None):
        """Adds torrent to torrent client using RPC.

        :param torrent: torrent file contents
        :param download_to: path to download files from torrent into (in terms of torrent client filesystem)

        """
        raise NotImplementedError  # pragma: nocover

    def method_remove_torrent(self, hash_str: str, with_data: bool = False):
        """Removes torrent from torrent client using RPC.

        :param hash_str: torrent identifying hash
        :param with_data: flag to also remove files from torrent

        """
        raise NotImplementedError  # pragma: nocover

    def method_get_version(self) -> str:
        """Returns torrent client API version."""

        raise NotImplementedError  # pragma: nocover

    def test_configuration(self) -> str:
        # This is to conform to common interface.
        return self.method_get_version()
