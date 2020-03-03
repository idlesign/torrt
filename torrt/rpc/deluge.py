import json
import logging
from typing import Dict, Any, List

import requests
from requests import Response

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import RPCClassesRegistry, base64encode

LOGGER = logging.getLogger(__name__)


class DelugeRPC(BaseRPC):
    """Requires deluge-webapi plugin to function.
    https://github.com/idlesign/deluge-webapi

    """
    alias: str = 'deluge'

    headers: dict = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    torrent_fields_map: Dict[str, str] = {
        'save_path': 'download_to',
    }

    def __init__(
            self,
            url: str = None,
            host: str = 'localhost',
            port: int = 8112,
            user: str = None,
            password: str = None,
            enabled: bool = False
    ):
        self.cookies = {}
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port

        if url is not None:
            self.url = url

        else:
            self.url = 'http://%s:%s/json' % (host, port)

    def method_login(self) -> bool:

        LOGGER.debug('Logging in ...')

        data = self.build_request_payload('auth.login', [self.password])

        response = self.query_(data)
        response_json = response.json()

        if response_json['result']:
            self.cookies = response.cookies
            return self.method_is_connected()

        LOGGER.error('Login failed')

        return False

    def method_is_connected(self):

        result = self.query(self.build_request_payload('auth.check_session'))

        if not result:
            raise DelugeRPCException('Deluge WebUI is not connected to a daemon')

        return result

    def query_(self, data: dict) -> Response:

        try:
            response = requests.post(
                self.url, data=json.dumps(data), cookies=self.cookies, headers=self.headers)

        except requests.exceptions.RequestException as e:

            LOGGER.error('Failed to query RPC `%s`: %s', self.url, str(e))
            raise DelugeRPCException(str(e))

        return response

    def query(self, data: dict) -> Any:

        if not self.cookies:
            self.method_login()

        LOGGER.debug('RPC method `%s` ...', data['method'])

        response = self.query_(data)
        response = response.json()

        if response['error'] is not None:
            raise DelugeRPCException(response['error'])

        return response['result']

    @staticmethod
    def build_request_payload(method: str, params: list = None) -> dict:

        document = {
            'id': 1,
            'method': method,
        }

        if params is None:
            params = []

        document.update({'params': params})

        return document

    def method_get_torrents(self, hashes: List[str] = None) -> List[dict]:

        fields = ['name', 'comment', 'hash', 'save_path']

        result = self.query(self.build_request_payload(
            'webapi.get_torrents',  [hashes, fields]))

        for torrent_info in result['torrents']:
            self.normalize_field_names(torrent_info)

        return result['torrents']

    def method_add_torrent(self, torrent: bytes, download_to: str = None, excluded_files: List[str] = None) -> Any:

        torrent_dump = base64encode(torrent).decode()

        return self.query(
            self.build_request_payload(
                'webapi.add_torrent', [torrent_dump, {'download_location': download_to}]
            )
        )

    def method_remove_torrent(self, hash_str: str, with_data: bool = False) -> Any:
        return self.query(self.build_request_payload('webapi.remove_torrent', [hash_str, with_data]))

    def method_get_version(self) -> str:
        return self.query(self.build_request_payload('webapi.get_api_version'))


class DelugeRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(DelugeRPC)
