import re
import os
import json
import logging
from datetime import datetime
from collections import Mapping
from pkgutil import iter_modules
from inspect import getargspec

import libtorrent as lt


LOGGER = logging.getLogger(__name__)


# This regex is used to get hyperlink from torrent comment.
RE_LINK = re.compile(r'(?P<url>https?://[^\s]+)')


def import_classes():
    """Dynamically imports RPC classes and tracker handlers from directories."""
    LOGGER.debug('Importing RPC classes ...')
    import_from_path('rpc')

    LOGGER.debug('Importing Tracker classes ...')
    import_from_path('trackers')


def import_from_path(path):
    """Dynamically imports modules from package.
    It is an .egg-friendly alternative to os.listdir() walking.

    """
    for mloader, pname, ispkg in iter_modules([os.path.join(os.path.dirname(__file__), path)]):
        __import__('torrt.%s.%s' % (path, pname))


def parse_torrent(torrent):
    """Returns a dictionary with basic information from torrent contents.

    Dict keys:
        hash - Torrent hash.
        files - A list of files within the torrent.
        torrent - Torrent file contents from input.

    """
    torrent_info = lt.torrent_info(lt.bdecode(torrent))
    files_from_torrent = [a_file.path.decode('utf-8') for a_file in torrent_info.files()]
    info = {'hash': str(torrent_info.info_hash()), 'name': str(torrent_info.name()), 'files': files_from_torrent, 'torrent': torrent}
    return info


def parse_torrent_file(filepath):
    """Reads a torrent file from filesystem and returns information about it."""
    with open(filepath, 'rb') as f:
        contents = f.read()
    return parse_torrent(contents)


def get_url_from_string(string):
    """Returns URL from a string, e.g. torrent comment."""
    return RE_LINK.search(string).group('url')


def get_iso_from_timestamp(ts):
    return datetime.fromtimestamp(ts).isoformat(' ')


def update_dict(old_dict, new_dict):
    for key, val in new_dict.iteritems():
        if isinstance(val, Mapping):
            old_dict[key] = update_dict(old_dict.get(key, {}), val)
        else:
            old_dict[key] = new_dict[key]
    return old_dict


def structure_torrent_data(target_dict, hash, data):
    data = dict(data)

    if 'hash' not in data:
        data['hash'] = hash

    if 'name' not in data:
        data['name'] = None

    target_dict[hash] = {
        'hash': data['hash'],
        'name': data['name']
    }


def get_torrent_from_url(url):
    LOGGER.info('Downloading torrent file from `%s` ...' % url)

    tracker = TrackerObjectsRegistry.get_for_string(url)
    if tracker:
        result = tracker.get_torrent(url)
        if result is None:
            LOGGER.info('Unable to get torrent from `%s`' % url)
        else:
            LOGGER.info('Torrent was downloaded from `%s`' % url)
            return result
    else:
        LOGGER.warning('Tracker handler for `%s` is not registered' % url)
    return None


def iter_rpc():
    rpc_objects = RPCObjectsRegistry.get()
    if not rpc_objects:
        LOGGER.error('No RPC objects registered, unable to proceed')
        raise StopIteration()

    for rpc_alias, rpc_object in rpc_objects.items():
        if not rpc_object.enabled:
            LOGGER.info('RPC `%s` is disabled, skipped.' % rpc_object.alias)
            continue

        yield rpc_alias, rpc_object


class WithSettings(object):

    config_entry_name = None
    settings = {}
    alias = None

    @classmethod
    def spawn_with_settings(cls, settings):
        LOGGER.debug('Spawning `%s` object with the given settings ...' % cls.__name__)
        return cls(**settings)

    def get_settings(self, name=None):
        """Returns RPC specific settings dictionary.
        Use `name` param to get a definite settings value.

        """
        if name is None:
            return self.settings
        return self.settings.get(name)

    def save_settings(self):
        settings = {}

        try:
            settings_names = getargspec(self.__init__)[0]
            del settings_names[0]  # do not need `self`
            for name in settings_names:
                settings[name] = getattr(self, name)
        except TypeError:
            pass  # Probably __init__ method is not user-defined.

        TorrtConfig.update({self.config_entry_name: {self.alias: settings}})


class TorrtConfig(object):

    USER_DATA_PATH = os.path.join(os.path.expanduser('~'), '.torrt')
    USER_SETTINGS_FILE = os.path.join(USER_DATA_PATH, 'config.json')

    @classmethod
    def bootstrap(cls):
        if not os.path.exists(cls.USER_DATA_PATH):
            os.makedirs(cls.USER_DATA_PATH)

        if not os.path.exists(cls.USER_SETTINGS_FILE):
            basic_settings = {
                'time_last_check': 0,
                'walk_interval_hours': 1,
                'rpc': {},
                'trackers': {},
                'torrents': {}
            }
            cls.save(basic_settings)

        # My precious.
        os.chmod(cls.USER_SETTINGS_FILE, 0600)

    @classmethod
    def update(cls, settings):
        cls.save(update_dict(cls.load(), settings))

    @classmethod
    def load(cls):
        LOGGER.debug('Loading configuration file %s ...' % cls.USER_SETTINGS_FILE)
        cls.bootstrap()
        with open(cls.USER_SETTINGS_FILE) as f:
            return json.load(f)

    @classmethod
    def save(cls, cfg_dict):
        LOGGER.debug('Saving configuration file %s ...' % cls.USER_SETTINGS_FILE)
        with open(cls.USER_SETTINGS_FILE, 'w') as f:
            json.dump(cfg_dict, f, indent=4)


class Registry(object):

    __slots__ = ['_items']

    def __init__(self):
        self._items = {}

    def add(self, item):
        name = getattr(item, 'alias')
        LOGGER.debug('Registering `%s` from %s ...' % (name, item))
        self._items[name] = item

    def get(self, item_alias=None):
        if item_alias is None:
            return self._items
        return self._items.get(item_alias)

    def get_for_string(self, string):
        for name in self._items.keys():
            if name in string:
                return self._items[name]
        return None


class TorrtException(Exception):
    """"""

RPCClassesRegistry = Registry()
RPCObjectsRegistry = Registry()
TrackerClassesRegistry = Registry()
TrackerObjectsRegistry = Registry()
