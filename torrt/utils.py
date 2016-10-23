import re
import os
import json
import logging
from datetime import datetime
from collections import Mapping
from pkgutil import iter_modules
from inspect import getargspec

import libtorrent as lt
from bs4 import BeautifulSoup

from torrt.exceptions import TorrtException  # Imported for backward compatibility.

LOGGER = logging.getLogger(__name__)


# This regex is used to get hyperlink from torrent comment.
RE_LINK = re.compile(r'(?P<url>https?://[^\s]+)')


def import_classes():
    """Dynamically imports RPC classes and tracker handlers from their directories.

    :return:
    """
    LOGGER.debug('Importing RPC classes ...')
    import_from_path('rpc')

    LOGGER.debug('Importing Tracker classes ...')
    import_from_path('trackers')

    LOGGER.debug('Importing Notifier classes ...')
    import_from_path('notifiers')


def import_from_path(path):
    """Dynamically imports modules from package.
    It is an .egg-friendly alternative to os.listdir() walking.

    :param path: str - path under torrt
    :return:
    """
    for _, pname, ispkg in iter_modules([os.path.join(os.path.dirname(__file__), path)]):
        __import__('torrt.%s.%s' % (path, pname))


def parse_torrent(torrent):
    """Returns a dictionary with basic information from torrent contents.

    :param torrent:
    :return: torrent info dict - keys: hash; name; files; torrent (torrent file contents just from input).
    :rtype: dict
    """
    torrent_info = lt.torrent_info(lt.bdecode(torrent))
    files_from_torrent = [a_file.path.decode('utf-8') for a_file in torrent_info.files()]
    info = {
        'hash': str(torrent_info.info_hash()),
        'name': str(torrent_info.name()),
        'files': files_from_torrent,
        'torrent': torrent
    }
    return info


def parse_torrent_file(filepath):
    """Reads a torrent file from filesystem and returns information about it.

    :param filepath: str
    :return: file contents
    :rtype: str
    """
    with open(filepath, 'rb') as f:
        contents = f.read()
    return parse_torrent(contents)


def make_soup(html):
    """Returns BeautifulSoup object from a html.

    :param html: str
    :return: object
    :rtype: BeautifulSoup
    """
    return BeautifulSoup(html, 'lxml')


def get_url_from_string(string):
    """Returns URL from a string, e.g. torrent comment.

    :param string:
    :return: url
    :rtype: str
    """
    match = RE_LINK.search(string)
    try:
        match = match.group('url')
    except AttributeError:
        match = ''
    return match


def get_iso_from_timestamp(ts):
    """Get ISO formatted string from timestamp.

    :param ts: int - timestamp
    :return: string
    :rtype: str
    """
    return datetime.fromtimestamp(ts).isoformat(' ')


def update_dict(old_dict, new_dict):
    """Updates old dictionary with data from a new one with respect to existing values.

    :param old_dict:
    :param new_dict:
    :return: updated dict
    :rtype: dict
    """
    for key, val in new_dict.iteritems():
        if isinstance(val, Mapping):
            old_dict[key] = update_dict(old_dict.get(key, {}), val)
        else:
            old_dict[key] = new_dict[key]
    return old_dict


def structure_torrent_data(target_dict, hash_str, data):
    """Updated target dict with torrent data structured suitably
    for config storage.

    :param target_dict: dict - dictionary to update
    :param hash_str: str - torrent identifying hash
    :param data: dict - torrent data recieved from RPC (see parse_torrent())
    :return:
    """
    data = dict(data)

    if 'hash' not in data:
        data['hash'] = hash_str

    if 'name' not in data:
        data['name'] = None

    target_dict[hash_str] = {
        'hash': data['hash'],
        'name': data['name']
    }


def get_torrent_from_url(url):
    """Downloads torrent from a given URL and returns it as string.

    :param url: str or None
    :return: torrent contents
    :rtype: str
    """
    LOGGER.debug('Downloading torrent file from `%s` ...', url)

    tracker = TrackerObjectsRegistry.get_for_string(url)
    if tracker:
        result = tracker.get_torrent(url)
        if result is None:
            LOGGER.warning('Unable to get torrent from `%s`', url)
        else:
            LOGGER.debug('Torrent was downloaded from `%s`', url)
            return result
    else:
        LOGGER.warning('Tracker handler for `%s` is not registered', url)
    return None


def iter_rpc():
    """Generator to iterate through available and enable RPC objects.

    :return: tuple - rpc_alias, rpc_object
    :rtype: tuple
    """
    rpc_objects = RPCObjectsRegistry.get()
    if not rpc_objects:
        LOGGER.error('No RPC objects registered, unable to proceed')
        raise StopIteration()

    for rpc_alias, rpc_object in rpc_objects.items():
        if not rpc_object.enabled:
            LOGGER.debug('RPC `%s` is disabled, skipped.', rpc_object.alias)
            continue

        yield rpc_alias, rpc_object


def iter_notifiers():
    """Generator to iterate through available notifier objects.

    :return: tuple - notifier_alias, notifier_object
    :rtype: tuple
    """
    notifier_objects = NotifierObjectsRegistry.get()
    if not notifier_objects:
        LOGGER.error('No Notifier objects registered, unable to proceed')
        raise StopIteration()

    for notifier_alias, notifier_object in notifier_objects.items():

        yield notifier_alias, notifier_object


class WithSettings(object):
    """Introduces settings support for class objects.

    NB: * Settings names are taken from inheriting classes __init__() methods.
        * __init__() method MUST use keyword arguments only.
        * Inheriting classes MUST save settings under object properties with the same name as in __init__().

    """

    config_entry_name = None
    settings = {}
    alias = None

    @classmethod
    def spawn_with_settings(cls, settings):
        """Spawns and returns object initialized with given settings.

        :param settings:
        :return: object
        """
        LOGGER.debug('Spawning `%s` object with the given settings ...', cls.__name__)
        return cls(**settings)

    def save_settings(self):
        """Saves object settings into torrt configuration file.

        :return:
        """
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
    """Gives methods to work with torrt configuration file."""

    USER_DATA_PATH = os.path.join(os.path.expanduser('~'), '.torrt')
    USER_SETTINGS_FILE = os.path.join(USER_DATA_PATH, 'config.json')

    _basic_settings = {
        'time_last_check': 0,
        'walk_interval_hours': 1,
        'rpc': {},
        'trackers': {},
        'torrents': {},
        'notifiers': {}
    }

    @classmethod
    def bootstrap(cls):
        """Initializes configuration file if needed,

        :return:
        """
        if not os.path.exists(cls.USER_DATA_PATH):
            os.makedirs(cls.USER_DATA_PATH)

        if not os.path.exists(cls.USER_SETTINGS_FILE):
            cls.save(cls._basic_settings)

        # My precious.
        os.chmod(cls.USER_SETTINGS_FILE, 0600)

    @classmethod
    def update(cls, settings_dict):
        """Updates configuration file with given settings.

        :param settings_dict: dict
        :return:
        """
        cls.save(update_dict(cls.load(), settings_dict))

    @classmethod
    def load(cls):
        """Returns current settings dictionary.

        :return: settings dict
        :rtype: dict
        """
        LOGGER.debug('Loading configuration file %s ...', cls.USER_SETTINGS_FILE)
        cls.bootstrap()
        with open(cls.USER_SETTINGS_FILE) as f:
            settings = json.load(f)

        # Pick up settings entries added in new version
        # and put them into old user config.
        for k, v in cls._basic_settings.items():
            if k not in settings:
                settings[k] = v

        return settings

    @classmethod
    def save(cls, settings_dict):
        """Saves a given dict as torrt configuration.

        :param settings_dict: dict
        :return:
        """
        LOGGER.debug('Saving configuration file %s ...', cls.USER_SETTINGS_FILE)
        with open(cls.USER_SETTINGS_FILE, 'w') as f:
            json.dump(settings_dict, f, indent=4)


class ObjectsRegistry(object):

    __slots__ = ['_items']

    def __init__(self):
        self._items = {}

    def add(self, obj):
        """Add an object to registry.

        NB: object MUST have `alias` attribute.

        :param obj: object
        :return:
        """
        name = getattr(obj, 'alias')
        LOGGER.debug('Registering `%s` from %s ...', name, obj)
        self._items[name] = obj

    def get(self, obj_alias=None):
        """Returns registered objects or a definite object by its alias.

        :param obj_alias: str or None
        :return: dict or object
        :rtype: dict or object
        """
        if obj_alias is None:
            return self._items
        return self._items.get(obj_alias)

    def get_for_string(self, string):
        """Returns registered object which can handle a given string.

        :param string: str
        :return: object or None
        :rtype: object or None
        """
        for name, obj in self._items.items():
            can_handle_method = getattr(obj, 'can_handle', None)

            if can_handle_method and can_handle_method(string):
                return obj

            elif name in string:
                return self._items[name]

        return None


RPCClassesRegistry = ObjectsRegistry()
RPCObjectsRegistry = ObjectsRegistry()
TrackerClassesRegistry = ObjectsRegistry()
TrackerObjectsRegistry = ObjectsRegistry()
NotifierClassesRegistry = ObjectsRegistry()
NotifierObjectsRegistry = ObjectsRegistry()
