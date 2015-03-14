import requests
import logging
import json
import base64

from torrt.base_rpc import BaseRPC, TorrtRPCException
from torrt.utils import RPCClassesRegistry


LOGGER = logging.getLogger(__name__)


class DelugeRPC(BaseRPC):
    """Requires deluge-webapi plugin to function.
    https://github.com/idlesign/deluge-webapi

    """

    alias = 'deluge'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    torrent_fields_map = {
        'save_path': 'download_to',
    }

    def __init__(self, url=None, host='localhost', port=8112, user=None, password=None, enabled=False):
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

    def method_login(self):
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
        result = self.query(self.build_request_payload('web.connected'))
        if not result:
            raise DelugeRPCException('Deluge WebUI is not connected to a daemon')
        return result

    def query_(self, data):
        try:
            response = requests.post(self.url, data=json.dumps(data), cookies=self.cookies, headers=self.headers)
        except requests.exceptions.RequestException as e:
            LOGGER.error('Failed to query RPC `%s`: %s', self.url, e.message)
            raise DelugeRPCException(e.message)
        return response

    def query(self, data):
        if not self.cookies:
            self.method_login()

        LOGGER.debug('RPC method `%s` ...', data['method'])
        response = self.query_(data)
        response = response.json()

        if response['error'] is not None:
            raise DelugeRPCException(response['error'])

        return response['result']

    @staticmethod
    def build_request_payload(method, params=None):
        document = {
            'id': 1,
            'method': method
        }
        if params is None:
            params = []
        document.update({'params': params})
        return document

    def method_get_torrents(self, hashes=None):
        fields = ['name', 'comment', 'hash', 'save_path']
        result = self.query(self.build_request_payload('webapi.get_torrents',  [hashes, fields]))

        for torrent_info in result['torrents']:
            self.normalize_field_names(torrent_info)

        return result['torrents']

    def method_add_torrent(self, torrent, download_to=None):
        return self.query(
            self.build_request_payload(
                'webapi.add_torrent', [base64.encodestring(torrent), {'download_location': download_to}]
            )
        )

    def method_remove_torrent(self, hash_str, with_data=False):
        return self.query(self.build_request_payload('webapi.remove_torrent', [hash_str, with_data]))

    def method_get_version(self):
        return self.query(self.build_request_payload('webapi.get_api_version'))


class DelugeRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(DelugeRPC)
