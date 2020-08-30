from typing import Dict, List, Any

from .utils import WithSettings, RPCObjectsRegistry, TorrentData, RPCClassesRegistry, HttpClient


class BaseRPC(WithSettings):
    """Base RPC class. All RPC classes should inherit from this."""

    config_entry_name: str = 'rpc'

    torrent_fields_map: Dict[str, str] = {}
    """mapping from torrent fields names in terms of RPC to field names in term of torrt"""

    enabled: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.client = HttpClient(
            silence_exceptions=True,
            dump_fname_tpl=f'%(ts)s_{self.__class__.__name__}.json',
            tunnel=False,
            json=True,
        )
        self.logged_in = False

    def __init_subclass__(cls, **kwargs):
        if cls.alias:
            RPCClassesRegistry.add(cls)

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

    def method_get_torrents(self, hashes: List[str] = None) -> List[dict]:  # pragma: nocover
        """This should return a dictionary with torrents info from RPC.
        Each torrent info should be normalized (see normalize_field_names()).

        :param hashes: torrent hashes

        """
        raise NotImplementedError

    def method_add_torrent(
            self, torrent: TorrentData, download_to: str = None, params: dict = None) -> Any:  # pragma: nocover
        """Adds torrent to torrent client using RPC.

        :param torrent: torrent info
        :param download_to: path to download files from torrent into (in terms of torrent client filesystem)
        :param params: optional information attached to torrent that should be saved

        """
        raise NotImplementedError

    def method_remove_torrent(self, hash_str: str, with_data: bool = False) -> Any:  # pragma: nocover
        """Removes torrent from torrent client using RPC.

        :param hash_str: torrent identifying hash
        :param with_data: flag to also remove files from torrent

        """
        raise NotImplementedError

    def method_get_version(self) -> str:  # pragma: nocover
        """Returns torrent client API version."""
        raise NotImplementedError

    def test_configuration(self) -> str:
        # This is to conform to common interface.
        return self.method_get_version()
