import logging
from typing import Dict, Any, Union, List

import requests
from requests import Response

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import base64encode, TorrentData

LOGGER = logging.getLogger(__name__)


class TransmissionRPC(BaseRPC):
    """See https://trac.transmissionbt.com/browser/trunk/extras/rpc-spec.txt for protocol spec details"""

    csrf_header: str = 'X-Transmission-Session-Id'
    session_id: str = ''

    alias: str = 'transmission'

    torrent_fields_map: Dict[str, str] = {
        'hashString': 'hash',
        'downloadDir': 'download_to',
    }

    def __init__(
            self,
            url: str = None,
            host: str = 'localhost',
            port: int = 9091,
            user: str = None,
            password: str = None,
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
            self.url = f'http://{host}:{port}/transmission/rpc'

        super().__init__()

    def query_(self, data: dict) -> Response:

        try:
            response = requests.post(
                self.url,
                auth=(self.user, self.password),
                json=data,
                headers={self.csrf_header: self.session_id},
                proxies={'http': None, 'https': None},  # todo factor out httpclient
            )

        except requests.exceptions.RequestException as e:

            LOGGER.error(f'Failed to query RPC `{self.url}`: {e}')
            raise TransmissionRPCException(str(e))

        return response

    def query(self, data: dict) -> Any:

        LOGGER.debug(f"RPC method `{data['method']}` ...")

        response = self.query_(data)

        if response.status_code == 409:
            self.session_id = response.headers[self.csrf_header]
            response = self.query_(data)

        response = response.json()

        if response['result'] != 'success':
            raise TransmissionRPCException(response['result'])

        return response['arguments']

    @staticmethod
    def build_request_payload(method: str, arguments: Union[dict, list] = None, tag: str = None) -> dict:

        document = {'method': method}

        if arguments is not None:
            document.update({'arguments': arguments})

        if tag is not None:
            document.update({'tag': tag})

        return document

    def method_get_torrents(self, hashes: List[str] = None) -> List[dict]:

        fields = [
            'id',
            'name',
            'hashString',
            'comment',
            'downloadDir',
            'files',
            'fileStats',
        ]

        args = {'fields': fields}

        if hashes is not None:
            args.update({'ids': hashes})

        result = self.query(self.build_request_payload('torrent-get', args))

        for torrent_info in result['torrents']:
            self.normalize_field_names(torrent_info)
            files = {}
            for idx in range(len(torrent_info['files'])):
                filename = torrent_info['files'][idx]['name']
                stats = torrent_info['fileStats'][idx]

                files[filename] = {'name': filename, 'exclude': not stats['wanted'], 'priority': stats['priority']}

            torrent_info['params'] = {'files': files}

            del torrent_info['files']
            del torrent_info['fileStats']

        return result['torrents']

    def method_add_torrent(self, torrent: TorrentData, download_to: str = None, params: dict = None) -> Any:

        args = {
            'metainfo': base64encode(torrent.raw).decode(),
        }

        params_files = (params or {}).get('files')

        if params_files:
            # Handle download exclusions.
            excluded_indices = []
            for idx, (filename, _) in enumerate(torrent.parsed.files):
                file_info: dict = params_files.get(filename, None)
                if file_info and file_info.get('exclude', False):
                    excluded_indices.append(idx)

            if excluded_indices:
                args['files-unwanted'] = excluded_indices

        if download_to is not None:
            args['download-dir'] = download_to

        return self.query(self.build_request_payload('torrent-add', args))

    def method_remove_torrent(self, hash_str: str, with_data: bool = False) -> Any:

        args = {
            'ids': [hash_str],
            'delete-local-data': with_data
        }

        return self.query(self.build_request_payload('torrent-remove', args))

    def method_get_version(self) -> str:
        result = self.query(self.build_request_payload('session-get', ['rpc-version-minimum']))
        return result['rpc-version-minimum']


class TransmissionRPCException(TorrtRPCException):
    """"""
