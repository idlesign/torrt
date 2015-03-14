import requests
import logging
import json
import base64

from torrt.base_rpc import BaseRPC, TorrtRPCException
from torrt.utils import RPCClassesRegistry


LOGGER = logging.getLogger(__name__)


class TransmissionRPC(BaseRPC):
    """See https://trac.transmissionbt.com/browser/trunk/extras/rpc-spec.txt for protocol spec details"""

    csrf_header = 'X-Transmission-Session-Id'
    session_id = None
    alias = 'transmission'
    torrent_fields_map = {
        'hashString': 'hash',
        'downloadDir': 'download_to',
    }

    def __init__(self, url=None, host='localhost', port=9091, user=None, password=None, enabled=False):
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port
        if url is not None:
            self.url = url
        else:
            self.url = 'http://%s:%s/transmission/rpc' % (host, port)

    def query_(self, data):
        try:
            response = requests.post(
                self.url,
                auth=(self.user, self.password),
                data=json.dumps(data),
                headers={self.csrf_header: self.session_id}
            )
        except requests.exceptions.RequestException as e:
            LOGGER.error('Failed to query RPC `%s`: %s', self.url, e.message)
            raise TransmissionRPCException(e.message)
        return response

    def query(self, data):
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
    def build_request_payload(method, arguments=None, tag=None):
        document = {'method': method}
        if arguments is not None:
            document.update({'arguments': arguments})
        if tag is not None:
            document.update({'tag': tag})
        return document

    def method_get_torrents(self, hashes=None):
        fields = [
            'id',
            'name',
            'hashString',
            'comment',
            'downloadDir'
        ]
        args = {'fields': fields}
        if hashes is not None:
            args.update({'ids': hashes})

        result = self.query(self.build_request_payload('torrent-get', args))
        for torrent_info in result['torrents']:
            self.normalize_field_names(torrent_info)
        return result['torrents']

    def method_add_torrent(self, torrent, download_to=None):
        args = {
            'metainfo': base64.encodestring(torrent),
        }
        if download_to is not None:
            args['download-dir'] = download_to
        return self.query(self.build_request_payload('torrent-add', args))  # torrent-added

    def method_remove_torrent(self, hash_str, with_data=False):
        args = {
            'ids': [hash_str],
            'delete-local-data': with_data
        }
        self.query(self.build_request_payload('torrent-remove', args))
        return True

    def method_get_version(self):
        result = self.query(self.build_request_payload('session-get', ['rpc-version-minimum']))
        return result['rpc-version-minimum']


class TransmissionRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(TransmissionRPC)
