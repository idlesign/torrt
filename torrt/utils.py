import base64
import json
import logging
import os
import re
import threading
from collections import Mapping, namedtuple
from datetime import datetime
from inspect import getfullargspec
from pkgutil import iter_modules
from typing import Any, Optional, Union, Generator, Tuple

from bs4 import BeautifulSoup
from requests import Response
from torrentool.api import Torrent

if False:  # pragma: nocover
    from .base_tracker import GenericTracker
    from .base_rpc import BaseRPC
    from .base_bot import BaseBot
    from .base_notifier import BaseNotifier


LOGGER = logging.getLogger(__name__)

_THREAD_LOCAL = threading.local()

# This regex is used to get hyperlink from torrent comment.
RE_LINK = re.compile(r'(?P<url>https?://[^\s]+)')


def encode_value(value: str, encoding: str = None) -> Union[str, bytes]:
    """Encodes a value.

    :param value:
    :param encoding: Encoding charset.

    """
    if encoding is None:
        return value

    return value.encode(encoding)


def base64encode(string_or_bytes: Union[str, bytes]) -> bytes:
    """Return base64 encoded input

    :param string_or_bytes:

    """
    if isinstance(string_or_bytes, str):
        string_or_bytes = string_or_bytes.encode()

    return base64.encodebytes(string_or_bytes).decode('ascii').encode()


class GlobalParam:
    """Represents global parameter value holder.
    Global params can used anywhere in torrt.

    """
    @staticmethod
    def set(name: str, value: Any):
        setattr(_THREAD_LOCAL, name, value)

    @staticmethod
    def get(name: str) -> Any:
        return getattr(_THREAD_LOCAL, name, None)


def dump_contents(filename: str, contents: Union[bytes, Response]):
    """Dumps contents into a file with a given name.

    :param filename:
    :param contents:

    """
    dump_into = GlobalParam.get('dump_into')

    if not dump_into:
        return

    if hasattr(contents, 'encode_contents'):
        # soup
        text = contents.encode_contents()

    else:
        # requests lib response
        text = contents.content

    with open(os.path.join(dump_into, filename), 'wb') as f:
        f.write(text)


def configure_entity(type_name: str, registry, alias: str, settings_dict: dict = None) -> Optional['WithSettings']:
    """Configures and spawns objects using given settings.

    Successful configuration is saved.

    :param type_name: Entity type name to be used in massages.
    :param registry: Registry object.
    :param alias: Entity alias.
    :param settings_dict: Settings dictionary to configure object with.

    """
    LOGGER.info(f'Configuring `{alias}` {type_name.lower()} ...')

    entity_cls = registry.get(alias)

    if entity_cls is not None:

        obj = entity_cls.spawn_with_settings(settings_dict or {})
        configured = obj.test_configuration()

        if configured:
            obj.save_settings()
            LOGGER.info(f'{type_name} `{alias}` is configured')

            return obj

        else:
            LOGGER.error(f'{type_name} `{alias}` configuration failed. Check your settings')

    else:
        LOGGER.error(f'{type_name} `{alias}` is unknown')


def import_classes():
    """Dynamically imports RPC classes and tracker handlers from their directories."""

    LOGGER.debug('Importing RPC classes ...')
    import_from_path('rpc')

    LOGGER.debug('Importing Tracker classes ...')
    import_from_path('trackers')

    LOGGER.debug('Importing Notifier classes ...')
    import_from_path('notifiers')

    LOGGER.debug('Importing Bot classes ...')
    import_from_path('bots')


def import_from_path(path: str):
    """Dynamically imports modules from package.
    It is an .egg-friendly alternative to os.listdir() walking.

    :param path: path under torrt

    """
    for _, pname, ispkg in iter_modules([os.path.join(os.path.dirname(__file__), path)]):
        __import__(f'torrt.{path}.{pname}')


def parse_torrent(torrent: bytes) -> dict:
    """Returns a dictionary with basic information from torrent contents.

        keys:
            * hash;
            * name;
            * files;
            * torrent (torrent file contents just from input).

    :param torrent:

    """
    torrent_info = Torrent.from_string(torrent)

    files_from_torrent = [a_file[0] for a_file in torrent_info.files]
    info = {
        'hash': str(torrent_info.info_hash),
        'name': torrent_info.name,
        'files': files_from_torrent,
        'torrent': torrent
    }
    return info


def parse_torrent_file(filepath: str) -> dict:
    """Reads a torrent file from filesystem and returns information about it.

    :param filepath:

    """

    with open(filepath, 'rb') as f:
        contents = f.read()

    return parse_torrent(contents)


def make_soup(html: str) -> BeautifulSoup:
    """Returns BeautifulSoup object from a html.

    :param html:

    """
    return BeautifulSoup(html, 'lxml')


def get_url_from_string(string: str) -> str:
    """Returns URL from a string, e.g. torrent comment.

    :param string:

    """
    match = RE_LINK.search(string)

    try:
        match = match.group('url')

    except AttributeError:
        match = ''

    return match


def get_iso_from_timestamp(ts: int) -> str:
    """Get ISO formatted string from timestamp.

    :param ts: timestamp

    """
    return datetime.fromtimestamp(ts).isoformat(' ')


def update_dict(old_dict: dict, new_dict: dict) -> dict:
    """Updates [inplace] old dictionary with data from a new one with respect to existing values.

    :param old_dict:
    :param new_dict:

    """
    for key, val in new_dict.items():

        if isinstance(val, Mapping):
            old_dict[key] = update_dict(old_dict.get(key, {}), val)

        else:
            old_dict[key] = new_dict[key]

    return old_dict


def structure_torrent_data(target_dict: dict, hash_str: str, data: dict):
    """Updated target dict with torrent data structured suitably
    for config storage.

    :param target_dict: dictionary to update inplace
    :param hash_str: torrent identifying hash
    :param data: torrent data received from RPC (see parse_torrent())

    """
    data = dict(data)

    if 'hash' not in data:
        data['hash'] = hash_str

    if 'name' not in data:
        data['name'] = None

    if 'url' not in data:
        data['url'] = None

    target_dict[hash_str] = {
        'hash': data['hash'],
        'name': data['name'],
        'url': data['url']
    }


def get_torrent_from_url(url: Optional[str]) -> Optional[dict]:
    """Downloads torrent from a given URL and returns it as string.

    :param url:

    """
    LOGGER.debug(f'Downloading torrent file from `{url}` ...')

    tracker = TrackerObjectsRegistry.get_for_string(url)  # type: GenericTracker

    if tracker:
        result = tracker.get_torrent(url)

        if result is None:
            LOGGER.warning(f'Unable to get torrent from `{url}`')

        else:
            LOGGER.debug(f'Torrent was downloaded from `{url}`')
            return result

    else:
        LOGGER.warning(f'Tracker handler for `{url}` is not registered')

    return None


def iter_rpc() -> Generator[Tuple[str, 'BaseRPC'], None, None]:
    """Generator to iterate through available and enable RPC objects.
        tuple - rpc_alias, rpc_object

    """
    rpc_objects = RPCObjectsRegistry.get()

    if not rpc_objects:
        LOGGER.error('No RPC objects registered, unable to proceed')
        return

    for rpc_alias, rpc_object in rpc_objects.items():

        if not rpc_object.enabled:
            LOGGER.debug(f'RPC `{rpc_object.alias}` is disabled, skipped.')
            continue

        yield rpc_alias, rpc_object


def iter_bots() -> Generator[Tuple[str, 'BaseBot'], None, None]:
    """Generator to iterate through available bots objects.
        tuple - bot_alias, bot_object

    """
    bot_objects = BotObjectsRegistry.get()

    if not bot_objects:
        LOGGER.error('No Bot objects registered, unable to proceed')
        return

    for alias, object in bot_objects.items():
        yield alias, object


def iter_notifiers() -> Generator[Tuple[str, 'BaseNotifier'], None, None]:
    """Generator to iterate through available notifier objects.
        tuple - notifier_alias, notifier_object

    """
    notifier_objects = NotifierObjectsRegistry.get()

    if not notifier_objects:
        LOGGER.debug('No Notifier registered. Notification skipped')
        return

    for notifier_alias, notifier_object in notifier_objects.items():

        yield notifier_alias, notifier_object


class WithSettings:
    """Introduces settings support for class objects.

    NB: * Settings names are taken from inheriting classes __init__() methods.
        * __init__() method MUST use keyword arguments only.
        * Inheriting classes MUST save settings under object properties with the same name as in __init__().

    """

    alias: str = None

    config_entry_name: str = None
    settings: dict = {}

    @classmethod
    def spawn_with_settings(cls, settings: dict) -> 'WithSettings':
        """Spawns and returns object initialized with given settings.

        :param settings:

        """
        LOGGER.debug(f'Spawning `{cls.__name__}` object with the given settings ...')

        return cls(**settings)

    def save_settings(self):
        """Saves object settings into torrt configuration file."""

        settings = {}

        try:
            settings_names = getfullargspec(self.__init__)[0]

            del settings_names[0]  # do not need `self`

            for name in settings_names:
                settings[name] = getattr(self, name)

        except TypeError:
            pass  # Probably __init__ method is not user-defined.

        config.update({self.config_entry_name: {self.alias: settings}})


class TorrtConfig:
    """Gives methods to work with torrt configuration file."""

    USER_DATA_PATH = os.path.join(os.path.expanduser('~'), '.torrt')
    USER_SETTINGS_FILE = os.path.join(USER_DATA_PATH, 'config.json')

    _basic_settings = {
        'time_last_check': 0,
        'walk_interval_hours': 1,
        'rpc': {},
        'trackers': {},
        'torrents': {},
        'notifiers': {},
        'bots': {}
    }

    @classmethod
    def drop_section(cls, realm: str, key: str):
        """Drops config section by its key (name) and updates config.

        :param realm:
        :param key:

        """
        try:
            cfg = cls.load()
            del cfg[realm][key]
            cls.save(cfg)

        except KeyError:
            pass

    @classmethod
    def bootstrap(cls):
        """Initializes configuration file if needed."""

        if not os.path.exists(cls.USER_DATA_PATH):
            os.makedirs(cls.USER_DATA_PATH)

        if not os.path.exists(cls.USER_SETTINGS_FILE):
            cls.save(cls._basic_settings)

        # My precious.
        os.chmod(cls.USER_SETTINGS_FILE, 0o600)

    @classmethod
    def update(cls, settings_dict: dict):
        """Updates configuration file with given settings.

        :param settings_dict:

        """
        cls.save(update_dict(cls.load(), settings_dict))

    @classmethod
    def load(cls) -> dict:
        """Returns current settings dictionary."""

        LOGGER.debug(f'Loading configuration file {cls.USER_SETTINGS_FILE} ...')

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
    def save(cls, settings_dict: dict):
        """Saves a given dict as torrt configuration.

        :param settings_dict:

        """
        LOGGER.debug(f'Saving configuration file {cls.USER_SETTINGS_FILE} ...')

        with open(cls.USER_SETTINGS_FILE, 'w') as f:
            json.dump(settings_dict, f, indent=4)


config = TorrtConfig


class ObjectsRegistry:

    __slots__ = ['_items']

    def __init__(self):
        self._items = {}

    def add(self, obj: Any):
        """Add an object to registry.

        NB: object MUST have `alias` attribute.

        :param obj:

        """
        name = getattr(obj, 'alias')

        LOGGER.debug(f'Registering `{name}` from {obj} ...')

        self._items[name] = obj

    def get(self, obj_alias: str = None) -> Union[dict, Any]:
        """Returns registered objects or a definite object by its alias,
        or registry items if no alias provided.

        :param obj_alias:

        """
        if obj_alias is None:
            return self._items

        return self._items.get(obj_alias)

    def get_for_string(self, string: str) -> Optional[Any]:
        """Returns registered object which can handle a given string.

        :param string:

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
BotClassesRegistry = ObjectsRegistry()
BotObjectsRegistry = ObjectsRegistry()
