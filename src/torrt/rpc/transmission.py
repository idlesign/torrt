from typing import Dict, Any, Union, List

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import base64encode, TorrentData


class TransmissionRPC(BaseRPC):
    """See https://github.com/transmission/transmission/blob/master/extras/rpc-spec.txt
    for protocol spec details.

    """
    csrf_header: str = 'X-Transmission-Session-Id'

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
        self.session_id: str = ''

        if url is not None:
            self.url = url

        else:
            self.url = f'http://{host}:{port}/transmission/rpc'

        super().__init__()

    def query_(self, data: dict) -> dict:

        json_data = self.client.request(
            url=self.url,
            data=data,
            auth=(self.user, self.password),
            headers={self.csrf_header: self.session_id},
            json=True,
            silence_exceptions=True,
        )

        if json_data is None:
            raise TransmissionRPCException(self.client.last_error)

        response = self.client.last_response
        status_code = response.status_code

        if status_code == 409:
            self.session_id = response.headers[self.csrf_header]
            json_data = self.query_(data)

        else:
            if not json_data and not response.ok:
                raise TransmissionRPCException(response.text)

        return json_data

    def query(self, data: dict) -> dict:

        self.log_debug(f"RPC method `{data['method']}` ...")

        json_data = self.query_(data)

        if json_data.get('result', '') != 'success':
            raise TransmissionRPCException(json_data)

        return json_data['arguments']

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
        return result['rpc-version']


class TransmissionRPCException(TorrtRPCException):
    """"""
