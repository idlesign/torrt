import requests
import logging
import json

from six.moves.urllib.parse import urljoin
from torrt.base_rpc import BaseRPC, TorrtRPCException
from torrt.utils import RPCClassesRegistry


LOGGER = logging.getLogger(__name__)


class QBittorrentRPC(BaseRPC):
    """See https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-Documentation for protocol spec details"""

    alias = 'qbittorrent'

    api_map = {
        'login': 'login',
        'api_version_path': 'version/api',
        'add_torrent': 'command/upload',
        'rem_torrent': 'command/delete',
        'rem_torrent_with_data': 'command/deletePerm',
        'get_torrent': 'query/propertiesGeneral/%s',
        'get_torrents': 'query/torrents'
    }

    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    torrent_fields_map = {
        'save_path': 'download_to',
    }

    def __init__(self, url=None, host='localhost', port=8080, user='admin', password='admin', enabled=False):
        self.cookies = {}
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port
        if url is not None:
            self.url = url
        else:
            self.url = 'http://%s:%s/' % (host, port)

    def login(self):
        try:
            data = {
                'username': self.user,
                'password': self.password
            }
            result = self.query(self.build_params('login', {'data': data}))

            if result.text != 'Ok.' or result.cookies is None:
                raise QBittorrentRPCException('Unable to auth credentials incorrect.')

            self.cookies = result.cookies

        except Exception as e:
            LOGGER.error('Failed to login using `%s` RPC: %s', self.url, e.message)
            raise QBittorrentRPCException(e.message)

    @staticmethod
    def build_params(action=None, params=None):
        document = {'action': action}
        if params is not None:
            document.update(params)
        return document

    def get_request_url(self, params):

        key = params['action']
        url_segment = self.api_map[key]
        if 'action_params' in params:
            url_segment = url_segment % params['action_params']

        url = urljoin(self.url, url_segment )
        return url

    def query(self, data, files=None):
        LOGGER.debug('RPC action `%s` ...', data['action'] or 'list')
        try:
            url = self.get_request_url(data)

            request_kwargs = {}
            if self.cookies is not None:
                request_kwargs['cookies'] = self.cookies

            method = requests.get
            if 'data' in data:
                method = requests.post
                request_kwargs['data'] = data['data']

            if files is not None:
                method = requests.post
                request_kwargs['files'] = files

            try:
                response = method(url, **request_kwargs)
                if response.status_code != 200:
                    raise QBittorrentRPCException(response.text.strip())
            except Exception as e:
                LOGGER.error('Failed to query RPC `%s`: %s', url, e.message)
                raise QBittorrentRPCException(e.message)

        except Exception as e:
            LOGGER.error('Failed to query RPC `%s`: %s', data['action'], e.message)
            raise QBittorrentRPCException(e.message)

        return response

    def auth_query(self, data, files=None):

        if not self.cookies:
            self.login()

        response = self.query(data, files)
        return response

    def auth_query_json(self, data, files=None):

        if not self.cookies:
            self.login()

        response = self.query(data, files)
        return json.loads(response .text)

    def method_get_torrents(self, hashes=None):
        result = self.auth_query_json(self.build_params('get_torrents', {'reverse': 'true'}))

        torrents_info = []
        for torrent_data in result:
            self.normalize_field_names(torrent_data)

            torrent_data_hash = torrent_data['hash']
            if hashes is None or torrent_data_hash in hashes:
                # TODO: because query/torrents not return `comment` field
                addition_data = self.auth_query_json(
                    self.build_params('get_torrent', {'action_params': torrent_data_hash})
                )
                self.normalize_field_names(addition_data)

                torrents_info.append({
                    'hash': torrent_data_hash,
                    'name': torrent_data['name'],
                    'download_to': torrent_data['download_to'],
                    'comment' : addition_data['comment']
                })

        return torrents_info

    def method_add_torrent(self, torrent, download_to=None):

        file_data = {'torrents': torrent}
        if download_to is not None:
            file_data.update({'savepath': download_to})

        return self.auth_query(self.build_params(action='add_torrent'), file_data)

    def method_remove_torrent(self, hash_str, with_data=False):
        action = 'rem_torrent'
        if with_data:
            action = 'rem_torrent_with_data'

        data = {
            'hashes': hash_str
        }
        self.auth_query(self.build_params(action, {'data': data}))
        return True

    def method_get_version(self):
        result = self.auth_query(self.build_params(action='api_version_path'))
        return result.text


class QBittorrentRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(QBittorrentRPC)
