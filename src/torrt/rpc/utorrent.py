from typing import Any
from urllib.parse import urlencode, urljoin

from ..base_rpc import BaseRPC, TorrentFile, TorrentStatus
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

        except Exception as error:

            self.log_error(f"Failed to login using `{self.url}` RPC: {error}")
            raise UTorrentRPCException(f"{error}") from error

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

            if response is None:
                raise UTorrentRPCException(self.client.last_error or "No response from uTorrent RPC")

            http_response = self.client.last_response

            if http_response.status_code != 200:
                raise UTorrentRPCException(http_response.text.strip() or http_response.reason)

            if error := response.get("error"):
                raise UTorrentRPCException(f"{error}")

        except Exception as error:

            self.log_error(f"Failed to query RPC `{url}`: {error}")
            raise UTorrentRPCException(f"{error}") from error

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

        if torrent.magnet:
            parameters = {"s": torrent.magnet, "path": download_to or None}

            return self.query(self.build_params(action="add-url", params=parameters))

        # NB: `download_to` is ignored, as existing API approach to it is crippled.
        file_data = {'torrent_file': ('from_torrt.torrent', torrent.raw)}

        return self.query(self.build_params(action='add-file', params={'path': download_to or None}), files=file_data)

    def method_get_torrent_status(self, hash_str: str) -> TorrentStatus | None:
        """Inspect the file list only after confirming the torrent exists in the client."""
        normalized_hash = hash_str.lower()
        torrents = self.method_get_torrents([normalized_hash])

        if not torrents:
            return None

        result = self.query(self.build_params(action="getfiles", params={"hash": normalized_hash}))
        response_files = result.get("files", [])

        if len(response_files) != 2 or response_files[0].lower() != normalized_hash:
            raise UTorrentRPCException("Unexpected torrent file response")

        files = tuple(TorrentFile(index=idx, name=file_info[0]) for idx, file_info in enumerate(response_files[1]))
        return TorrentStatus(hash=normalized_hash, metadata_ready=bool(files), files=files)

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
