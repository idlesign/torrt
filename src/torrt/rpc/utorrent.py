from typing import Any
from urllib.parse import urlencode, urljoin

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import TorrentData, make_soup


class UTorrentRPC(BaseRPC):
    """See http://www.utorrent.com/community/developers/webapi for protocol spec details.

    idle sign: What a shame - uTorrent API is a load of mess.

    """
    alias: str = 'utorrent'

    token_page_path: str = 'token.html'

    def __init__(
            self,
            *,
            url: str = '',
            host: str = 'localhost',
            port: int = 8080,
            user: str = '',
            password: str = '',
            enabled: bool = False
    ):
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port
        self.csrf_token = ''
        self.url = url or f'http://{host}:{port}/gui/'

        super().__init__()

    def login(self):

        try:
            response = self.client.request(
                urljoin(self.url, self.token_page_path),
                auth=(self.user, self.password),
                json=False,
                silence_exceptions=False,
            )

            self.csrf_token = make_soup(response.text).find(id='token').text

            if not self.csrf_token:
                raise UTorrentRPCException('Unable to fetch CSRF token.')

            self.logged_in = True

        except Exception as e:

            self.log_error(f'Failed to login using `{self.url}` RPC: {e}')
            raise UTorrentRPCException(f'{e}') from e

    def build_params(self, *, action: str = '', params: dict | None = None) -> dict:

        document = {'action': action or None}

        if params is not None:
            document.update(params)

        return document

    def get_request_url(self, params: dict) -> str:
        """Build a request URL with encoded query values and the current CSRF token."""
        query_params = [("token", self.csrf_token)]
        query_params.extend((name, value) for name, value in params.items() if value is not None)

        return f"{self.url}?{urlencode(query_params, doseq=True)}"

    def query(self, data: dict, *, files: dict | None = None) -> dict:

        action = data['action'] or 'list'
        self.log_debug(f'RPC action `{action}` ...', )

        if not self.logged_in:
            self.login()

        url = self.get_request_url(data)

        request_kwargs = {}

        if files is not None:
            request_kwargs['files'] = files

        try:
            response = self.client.request(
                url=url, auth=(self.user, self.password), **request_kwargs)

            if self.client.last_response.status_code != 200:
                raise UTorrentRPCException(response.text.strip())

        except Exception as e:

            self.log_error(f'Failed to query RPC `{url}`: {e}')
            raise UTorrentRPCException(f'{e}') from e

        return response

    def method_get_torrents(self, hashes: list[str] | None = None) -> list[dict]:

        result = self.query(self.build_params(params={'list': 1}))

        torrents_info = []

        for torrent_data in result['torrents']:
            hash_ = torrent_data[0].lower()

            if hashes is None or hash_ in hashes:

                torrents_info.append({
                    'hash': hash_,
                    'name': torrent_data[2],
                    'download_to': torrent_data[26],
                    'comment': ''
                })

        return torrents_info

    def method_add_torrent(self, torrent: TorrentData, *, download_to: str = '', params: dict | None = None) -> Any:

        # NB: `download_to` is ignored, as existing API approach to it is crippled.
        file_data = {'torrent_file': ('from_torrt.torrent', torrent.raw)}

        return self.query(self.build_params(action='add-file', params={'path': download_to or None}), files=file_data)

    def method_remove_torrent(self, hash_str: str, *, with_data: bool = False) -> Any:

        action = 'remove'

        if with_data:
            action = 'removedata'

        return self.query(self.build_params(action=action, params={'hash': hash_str}))

    def method_get_version(self) -> str:
        result = self.query(self.build_params(action='getversion'))
        return result['version']['ui_version']


class UTorrentRPCException(TorrtRPCException):
    """"""
