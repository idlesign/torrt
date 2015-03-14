import requests
import logging
from urlparse import urljoin

from torrt.base_rpc import BaseRPC, TorrtRPCException
from torrt.utils import RPCClassesRegistry, make_soup


LOGGER = logging.getLogger(__name__)


class UTorrentRPC(BaseRPC):
    """See http://www.utorrent.com/community/developers/webapi for protocol spec details.

    idle sign: What a shame - uTorrent API is a load of mess.

    """

    alias = 'utorrent'
    token_page_path = 'token.html'

    def __init__(self, url=None, host='localhost', port=8080, user=None, password=None, enabled=False):
        self.cookies = {}
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port
        self.csrf_token = ''
        if url is not None:
            self.url = url
        else:
            self.url = 'http://%s:%s/gui/' % (host, port)

    def login(self):
        try:
            response = requests.get(
                urljoin(self.url, self.token_page_path),
                auth=(self.user, self.password),
                cookies=self.cookies
            )
            self.csrf_token = make_soup(response.text).find(id='token').text
            if not self.csrf_token:
                raise UTorrentRPCException('Unable to fetch CSRF token.')
            self.cookies = response.cookies
        except Exception as e:
            LOGGER.error('Failed to login using `%s` RPC: %s', self.url, e.message)
            raise UTorrentRPCException(e.message)

    def build_params(self, action=None, params=None):
        document = {'action': action}
        if params is not None:
            document.update(params)
        return document

    def get_request_url(self, params):
        rest = []
        join = lambda l: '&'.join(l)
        for param_name, param_val in params.items():
            if param_val is None:
                continue
            val = param_val
            if isinstance(param_val, list):
                val = join(param_val)
            rest.append('%s=%s' % (param_name, val))
        return '%s?token=%s&%s' % (self.url,  self.csrf_token, join(rest))

    def query(self, data, files=None):
        LOGGER.debug('RPC action `%s` ...', data['action'] or 'list')

        if not self.cookies:
            self.login()

        url = self.get_request_url(data)

        request_kwargs = {
            'cookies': self.cookies
        }

        method = requests.get
        if files is not None:
            method = requests.post
            request_kwargs['files'] = files

        try:
            response = method(url, auth=(self.user, self.password), **request_kwargs)
            if response.status_code != 200:
                raise UTorrentRPCException(response.text.strip())
        except Exception as e:
            LOGGER.error('Failed to query RPC `%s`: %s', url, e.message)
            raise UTorrentRPCException(e.message)
        response = response.json()

        return response

    def method_get_torrents(self, hashes=None):
        result = self.query(self.build_params(params={'list': 1}))

        torrents_info = {}
        for torrent_data in result['torrents']:
            if hashes is None or torrent_data[0] in hashes:
                torrents_info[torrent_data[0]] = {
                    'hash': torrent_data[0],
                    'name': torrent_data[2],
                    'download_to': torrent_data[26]
                }

        return torrents_info

    def method_add_torrent(self, torrent, download_to=None):
        # NB: `download_to` is ignored, as existing API approach to it is crippled.
        file_data = {'torrent_file': ('from_torrt.torrent', torrent)}
        return self.query(self.build_params(action='add-file'), file_data)

    def method_remove_torrent(self, hash_str, with_data=False):
        action = 'remove'
        if with_data:
            action = 'removedata'
        self.query(self.build_params(action=action, params={'hash': hash_str}))
        return True

    def method_get_version(self):
        result = self.query(self.build_params(action='getversion'))
        return result['version']['ui_version']


class UTorrentRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(UTorrentRPC)
