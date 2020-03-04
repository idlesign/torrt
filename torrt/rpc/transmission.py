import logging
from typing import Dict, Any, Union, List

import requests
from requests import Response

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import RPCClassesRegistry, base64encode, parse_torrent

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
            self.url = 'http://%s:%s/transmission/rpc' % (host, port)

    def query_(self, data: dict) -> Response:

        try:
            response = requests.post(
                self.url,
                auth=(self.user, self.password),
                json=data,
                headers={self.csrf_header: self.session_id}
            )

        except requests.exceptions.RequestException as e:

            LOGGER.error('Failed to query RPC `%s`: %s', self.url, e)
            raise TransmissionRPCException(str(e))

        return response

    def query(self, data: dict) -> Any:

        LOGGER.debug('RPC method `%s` ...', data['method'])

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
            torrent_info['exclude_files'] = self.__get_unwanted_files(torrent_info)

        return result['torrents']

    def method_add_torrent(self, torrent: bytes, download_to: str = None, exclude_files: List[str] = None) -> Any:
        args = {
            'metainfo': base64encode(torrent).decode(),
        }

        if exclude_files:
            # REVIEW: I don't have good idea on how not to parse torrent again.
            # We can pass list of indices, so we don't need to parse torrent again.
            # But I think list of file names is more generic then list of file indices
            # and RPC implementation must adapt the list accordingly
            torrent = parse_torrent(torrent)
            excluded_indices = []
            for i, f in enumerate(torrent['files']):
                if f in exclude_files:
                    excluded_indices.append(i)

            if not excluded_indices:
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

    @staticmethod
    def __get_unwanted_files(torrent_info):
        result = []
        for i, file_stat in enumerate(torrent_info['fileStats']):
            if not file_stat['wanted']:
                result.append(torrent_info['files'][i]['name'])
        return result


class TransmissionRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(TransmissionRPC)
