import base64
import json
import logging
import os
import re
import threading
from collections import Mapping
from datetime import datetime
from inspect import getfullargspec
from pathlib import Path
from pkgutil import iter_modules
from time import time
from typing import Any, Optional, Union, Generator, Tuple, Callable

from bs4 import BeautifulSoup
from requests import Response, Session, RequestException
from torrentool.api import Torrent

if False:  # pragma: nocover
    from .base_tracker import GenericTracker  # noqa
    from .base_rpc import BaseRPC  # noqa
    from .base_bot import BaseBot  # noqa
    from .base_notifier import BaseNotifier  # noqa


LOGGER = logging.getLogger('torrt')

_THREAD_LOCAL = threading.local()

# This regex is used to get hyperlink from torrent comment.
RE_LINK = re.compile(r'(?P<url>https?://[^\s]+)')


class HttpClient:
    """Common client to perform HTTP requests."""

    timeout: int = 10

    user_agent: str = (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')

    def __init__(
            self,
            silence_exceptions: bool = False,
            dump_fname_tpl: str = '%(ts)s.txt',
            json: bool = False,
            tunnel: bool = True,
    ):
        session = Session()

        session.headers.update({
            'User-agent': self.user_agent,
        })

        self.session = session
        self.silence_exceptions = silence_exceptions,
        self.dump_fname_tpl = dump_fname_tpl
        self.json = json
        self.last_error: str = ''
        self.last_response: Optional[Response] = None
        self.tunnel = tunnel

    def request(
            self,
            url: str,
            *,
            data: dict = None,
            referer: str = '',
            allow_redirects: bool = True,
            cookies: dict = None,
            headers: dict = None,
            json: bool = None,
            silence_exceptions: bool = None,
            timeout: int = None,
            **kwargs
    ) -> Optional[Union[Response, dict]]:
        """

        :param url: URL to address
        :param data: Data to send to URL
        :param referer:
        :param allow_redirects:
        :param cookies:
        :param headers: Additional headers
        :param json: Send and receive data as JSON
        :param silence_exceptions: Do not raise exceptions
        :param timeout: Override timeout.
        :param kwargs:

        """
        LOGGER.debug(f'Fetching {url} ...')

        headers = {**(headers or {})}

        r_kwargs = {
            'timeout': timeout or self.timeout,
            'cookies': cookies,
            'headers': headers,
            'allow_redirects': allow_redirects,
            **kwargs,
        }

        if referer:
            headers['Referer'] = referer

        if not self.tunnel:
            # Drop globally set tunnels settings. See toolbox.tunnel().
            r_kwargs['proxies'] = {'http': None, 'https': None}

        if json is None:
            json = self.json

        try:

            if data or r_kwargs.get('files'):

                if json:
                    r_kwargs['json'] = data
                else:
                    r_kwargs['data'] = data

                method = self.session.post

            else:
                method = self.session.get

            response = method(url, **r_kwargs)

            self.last_response = response

        except RequestException as e:

            self.last_error = f'{e}'
            LOGGER.warning(f"Failed to get response from `{url}`: {e}")

            if silence_exceptions is None:
                silence_exceptions = self.silence_exceptions

            if silence_exceptions:
                return None

            raise

        else:

            dump_contents(
                self.dump_fname_tpl,
                contents=response.content
            )

            if json:
                try:
                    response = response.json()

                except:
                    return {}

        return response


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


def dump_contents(filename: str, contents: bytes):
    """Dumps contents into a file with a given name.

    :param filename:
    :param contents:

    """
    dump_into = GlobalParam.get('dump_into')

    if not dump_into:
        return

    filename = filename % {
        'ts': time(),
    }

    with open(str(Path(dump_into) / filename), 'wb') as f:
        f.write(contents)


def configure_entity(
        type_name: str,
        registry, alias: str,
        settings_dict: dict = None,
        *,
        before_save: Callable = None
) -> Optional['WithSettings']:
    """Configures and spawns objects using given settings.

    Successful configuration is saved.

    :param type_name: Entity type name to be used in massages.

    :param registry: Registry object.

    :param alias: Entity alias.

    :param settings_dict: Settings dictionary to configure object with.

    :param before_save: Function to trigger right before configuration is saved.
        Should accept entity object as argument.

    """
    LOGGER.info(f'Configuring `{alias}` {type_name.lower()} ...')

    entity_cls = registry.get(alias)

    if entity_cls is not None:

        obj = entity_cls.spawn_with_settings(settings_dict or {})
        configured = obj.test_configuration()

        if configured:
            before_save and before_save(obj)
            obj.save_settings()
            LOGGER.info(f'{type_name} `{alias}` is configured')

            return obj

        else:
            LOGGER.error(f'{type_name} `{alias}` configuration failed. Check your settings')

    else:
        LOGGER.error(f'{type_name} `{alias}` is unknown')


def import_classes():
    """Dynamically imports RPC classes and tracker handlers from their directories."""

    for package_name in ('rpc', 'trackers', 'notifiers', 'bots'):
        LOGGER.debug(f'Importing {package_name} ...')
        import_from_path(package_name)


def import_from_path(path: str):
    """Dynamically imports modules from package.
    It is an .egg-friendly alternative to os.listdir() walking.

    :param path: path under torrt

    """
    for _, pname, ispkg in iter_modules([str(Path(__file__).parent / path)]):
        __import__(f'torrt.{path}.{pname}')


def parse_torrent(torrent: bytes) -> Torrent:
    """Returns Torrent object from torrent contents.

    :param torrent: Torrent file contents.

    """
    return Torrent.from_string(torrent)


def parse_torrent_file(filepath: str) -> Torrent:
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


class PageData:
    """Represents data extracted from torrent page."""

    def __init__(self, title: str, cover: str, date_updated: str):
        self.title = title
        self.cover = cover
        self.date_updated = date_updated

    def to_dict(self):
        data = {
            'title': self.title,
            'cover': self.cover,
            'date_updated': self.date_updated,
        }
        return data


class TorrentData:
    """Represents information about torrent."""

    def __init__(
            self,
            *,
            hash: str = '',
            name: str = '',
            url: str = '',
            url_file: str = '',
            raw: bytes = b'',
            page: PageData = None,
            parsed: Torrent = None,
    ):
        self.url = url
        self.url_file = url_file

        self.raw = raw
        self.parsed = parsed
        self.page = page

        self._name = name
        self._hash = hash

    def _get_hash(self):
        return self._hash or getattr(self.parsed, 'info_hash', '') or ''

    def _set_hash(self, val: str):
        self._hash = val

    def _get_name(self):
        return self._name or getattr(self.parsed, 'name', '') or ''

    def _set_name(self, val: str):
        self._name = val

    hash: str = property(_get_hash, _set_hash)
    name: str = property(_get_name, _set_name)

    def to_dict(self) -> dict:
        page = self.page

        result = {
            'hash': self.hash,
            'name': self.name,
            'url': self.url,
            'url_file': self.url_file,
            'page': page.to_dict() if page else {},
        }
        return result


def structure_torrent_data(target_dict: dict, hash_str: str, data: TorrentData):
    """Updated target dict with torrent data structured suitably
    for config storage.

    :param target_dict: dictionary to update inplace
    :param hash_str: torrent identifying hash
    :param data: torrent data (e.g. from tracker page or received from RPC (see parse_torrent()))

    """

    if not data.hash:
        data.hash = hash_str

    target_dict[hash_str] = data.to_dict()


def get_torrent_from_url(url: Optional[str]) -> Optional[TorrentData]:
    """Downloads torrent from a given URL and returns torrent data.

    :param url:

    """
    LOGGER.debug(f'Downloading torrent file from `{url}` ...')

    tracker = TrackerObjectsRegistry.get_for_string(url)  # type: GenericTracker

    if tracker:
        torrent_info = tracker.get_torrent(url)

        if torrent_info is None:
            LOGGER.warning(f'Unable to get torrent from `{url}`')

        else:
            LOGGER.debug(f'Torrent was downloaded from `{url}`')
            return torrent_info

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

    def __init__(self, **kwargs):
        pass

    def __str__(self) -> str:
        return self.alias

    @classmethod
    def spawn_with_settings(cls, settings: dict) -> 'WithSettings':
        """Spawns and returns object initialized with given settings.

        :param settings:

        """
        LOGGER.debug(f'Spawning `{cls.__name__}` object with the given settings ...')

        return cls(**settings)

    @classmethod
    def log_debug(cls, msg: str):
        """Sends the message to debug log.

        :param msg:

        """
        LOGGER.debug(f'{cls.__name__}: {msg}')

    @classmethod
    def log_info(cls, msg: str):
        """Sends the message to info log.

        :param msg:

        """
        LOGGER.info(f'{cls.__name__}: {msg}')

    @classmethod
    def log_warning(cls, msg: str):
        """Sends the message to warning log.

        :param msg:

        """
        LOGGER.warning(f'{cls.__name__}: {msg}')

    @classmethod
    def log_error(cls, msg: str):
        """Sends the message to error log.

        :param msg:

        """
        LOGGER.error(f'{cls.__name__}: {msg}')

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

    USER_DATA_PATH = Path('~').expanduser() / '.torrt'
    USER_SETTINGS_FILE = USER_DATA_PATH / 'config.json'

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

        if not cls.USER_DATA_PATH.exists():
            os.makedirs(str(cls.USER_DATA_PATH))

        if not cls.USER_SETTINGS_FILE.exists():
            cls.save(cls._basic_settings)

        # My precious.
        os.chmod(str(cls.USER_SETTINGS_FILE), 0o600)

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

        with open(str(cls.USER_SETTINGS_FILE)) as f:
            settings = json.load(f)

        # Pick up settings entries added in new version
        # and put them into old user config.
        for key, val in cls._basic_settings.items():
            if key not in settings:
                settings[key] = val

        return settings

    @classmethod
    def save(cls, settings_dict: dict):
        """Saves a given dict as torrt configuration.

        :param settings_dict:

        """
        LOGGER.debug(f'Saving configuration file {cls.USER_SETTINGS_FILE} ...')

        with open(str(cls.USER_SETTINGS_FILE), 'w') as f:
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
