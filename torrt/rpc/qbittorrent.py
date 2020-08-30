from typing import Dict, List, Any
from urllib.parse import urljoin

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import TorrentData, Response


class QBittorrentRPC(BaseRPC):
    """See https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
    for protocol spec details

    """
    alias: str = 'qbittorrent'

    api_map: dict = {
        'login': 'auth/login',
        'api_version_path': 'app/webapiVersion',
        'add_torrent': 'torrents/add',
        'rem_torrent': 'torrents/delete',
        'get_torrent': 'torrents/properties',
        'get_torrents': 'torrents/info'
    }

    torrent_fields_map: Dict[str, str] = {
        'save_path': 'download_to',
    }

    def __init__(
            self,
            url: str = None,
            host: str = 'localhost',
            port: int = 8080,
            user: str = 'admin',
            password: str = 'admin',
            enabled: bool = False
    ):
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port

        if url is not None:
            self.url = url

        else:
            self.url = f'http://{host}:{port}/api/v2/'

        super().__init__()

    def login(self):

        try:
            data = {
                'username': self.user,
                'password': self.password
            }

            result = self.query(self.build_params('login', {'data': data}))

            if result.text != 'Ok.' or result.cookies is None:
                raise QBittorrentRPCException('Unable to auth credentials incorrect.')

            self.logged_in = True

        except Exception as e:

            self.log_error(f'Failed to login using `{self.url}` RPC: {e}')
            raise QBittorrentRPCException(str(e))

    @staticmethod
    def build_params(action: str = None, params: dict = None) -> dict:

        document = {'action': action}

        if params is not None:
            document.update(params)

        return document

    def get_request_url(self, params: dict) -> str:

        key = params['action']

        url_segment = self.api_map[key]

        if 'action_params' in params:
            url_segment = url_segment % params['action_params']

        return urljoin(self.url, url_segment )

    def query(self, data: dict, files: dict = None) -> Response:

        action = data['action'] or 'list'
        self.log_debug(f'RPC action `{action}` ...')

        try:
            url = self.get_request_url(data)

            request_kwargs = {}

            if 'data' in data:
                request_kwargs['data'] = data['data']

            if files is not None:
                request_kwargs['files'] = files

            try:
                response = self.client.request(
                    url=url,
                    json=False,
                    silence_exceptions=False,
                    **request_kwargs
                )

                if response.status_code != 200:
                    raise QBittorrentRPCException(response.text.strip() or response.reason)

            except Exception as e:

                self.log_error(f'Failed to query RPC `{url}`: {e}')
                raise QBittorrentRPCException(f'{e}')

        except Exception as e:

            self.log_error(f'Failed to query RPC `{action}`: {e}')
            raise QBittorrentRPCException(f'{e}')

        return response

    def auth_query(self, data: dict, files: dict = None):

        if not self.logged_in:
            self.login()

        return self.query(data, files)

    def auth_query_json(self, data: dict, files: dict = None) -> dict:

        if not self.logged_in:
            self.login()

        response = self.query(data, files)

        return response.json()

    def method_get_torrents(self, hashes: List[str] = None) -> List[dict]:

        result = self.auth_query_json(self.build_params('get_torrents', {'reverse': 'true'}))

        torrents_info = []

        for torrent_data in result:
            self.normalize_field_names(torrent_data)

            torrent_data_hash = torrent_data['hash']

            if hashes is None or torrent_data_hash in hashes:

                addition_data = self.auth_query_json(
                    self.build_params('get_torrent', {'data': {'hash': torrent_data_hash}}),
                )
                self.normalize_field_names(addition_data)

                torrents_info.append({
                    'hash': torrent_data_hash,
                    'name': torrent_data['name'],
                    'download_to': torrent_data['download_to'],
                    'comment' : addition_data['comment']
                })

        return torrents_info

    def method_add_torrent(self, torrent: TorrentData, download_to: str = None, params: dict = None) -> Any:

        file_data = {'torrents': torrent.raw}

        if download_to is not None:
            file_data.update({'savepath': download_to})

        return self.auth_query(self.build_params(action='add_torrent'), file_data)

    def method_remove_torrent(self, hash_str: str, with_data: bool = False) -> Any:

        data = {'hashes': hash_str}

        if with_data:
            data['deleteFiles'] = 'true'

        return self.auth_query(self.build_params('rem_torrent', {'data': data}))

    def method_get_version(self) -> str:
        result = self.auth_query(self.build_params(action='api_version_path'))
        return result.text


class QBittorrentRPCException(TorrtRPCException):
    """"""
