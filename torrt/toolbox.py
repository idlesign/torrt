import logging
from time import time
from typing import Optional, List, Dict

from .base_tracker import GenericPrivateTracker
from .exceptions import TorrtException, TorrtRPCException
from .utils import (
    RPCClassesRegistry, TrackerClassesRegistry, config, get_url_from_string,
    get_iso_from_timestamp, import_classes, structure_torrent_data, get_torrent_from_url, iter_rpc,
    NotifierClassesRegistry, iter_notifiers, BotClassesRegistry, iter_bots, configure_entity,
    TorrentData
)

try:
    from envbox import get_environment
    # Allow env vars from .env files.
    environ = get_environment()

except ImportError:
    from os import environ

if False:  # pragma: nocover
    from .base_rpc import BaseRPC  # noqa
    from .base_tracker import BaseTracker  # noqa
    from .base_notifier import BaseNotifier  # noqa
    from .base_bot import BaseBot  # noqa

LOGGER = logging.getLogger(__name__)


def tunnel():
    """Try to setup a tunnel for requests."""
    tunnel_through = environ.get('TORRT_TUNNEL')

    if tunnel_through:

        if tunnel_through == 'local':
            # pip install requests[socks]
            tunnel_through = 'socks5://127.0.0.1:9150'

        # Instruct `requests` https://requests.readthedocs.io/en/master/user/advanced/#socks
        environ['HTTP_PROXY'] = tunnel_through
        environ['HTTPS_PROXY'] = tunnel_through


tunnel()


def configure_logging(log_level: int = logging.INFO, show_logger_names: bool = False):
    """Performs basic logging configuration.

    :param log_level: logging level, e.g. logging.DEBUG
    :param show_logger_names: flag to show logger names in output

    """
    format_str = '%(levelname)s: %(message)s'

    if show_logger_names:
        format_str = '%(name)s\t\t ' + format_str

    logging.basicConfig(format=format_str, level=log_level)
    requests_logger = logging.getLogger('requests')
    requests_logger.setLevel(logging.ERROR)


def configure_rpc(rpc_alias: str, settings_dict: dict) -> Optional['BaseRPC']:
    """Configures RPC using given settings.
    Saves successful configuration.

    :param rpc_alias: RPC alias
    :param settings_dict: settings dictionary to configure RPC with

    """
    def enable(rpc: 'BaseRPC'):
        rpc.enabled = True

    return configure_entity('RPC', RPCClassesRegistry, rpc_alias, settings_dict, before_save=enable)


def configure_tracker(tracker_alias: str, settings_dict: dict) -> Optional['BaseTracker']:
    """Configures tracker using given settings.
    Saves successful configuration.

    :param tracker_alias: tracker alias
    :param settings_dict: settings dictionary to configure tracker with

    """
    return configure_entity('Tracker', TrackerClassesRegistry, tracker_alias, settings_dict)


def configure_notifier(notifier_alias: str, settings_dict: dict) -> Optional['BaseNotifier']:
    """Configures notifier using given settings.
    Saves successful configuration.

    :param notifier_alias: notifier alias
    :param settings_dict: settings dictionary to configure notifier with

    """
    return configure_entity('Notifier', NotifierClassesRegistry, notifier_alias, settings_dict)


def configure_bot(bot_alias: str, settings_dict: dict) -> Optional['BaseBot']:
    """Configures bot using given settings.
    Saves successful configuration.

    :param bot_alias: bot alias
    :param settings_dict: settings dictionary to configure bot with

    """
    return configure_entity('Bot', BotClassesRegistry, bot_alias, settings_dict)


def remove_notifier(alias: str):
    """Removes notifier by alias

    :param alias: Notifier alias to remove.

    """
    LOGGER.info(f'Removing `{alias}` notifier ...')

    config.drop_section('notifiers', alias)


def remove_bot(alias: str):
    """Removes bot by alias

    :param alias: Bot alias to remove.

    """
    LOGGER.info(f'Removing `{alias}` bot ...')

    config.drop_section('bots', alias)


def init_object_registries():
    """Initializes RPC and tracker objects registries with settings from configuration file."""

    LOGGER.debug('Initializing objects registries from configuration file ...')

    cfg = config.load()

    settings_to_registry_map = {
        'rpc': RPCClassesRegistry,
        'notifiers': NotifierClassesRegistry,
        'bots': BotClassesRegistry,
    }

    for settings_entry, registry_cls in settings_to_registry_map.items():

        for alias, settings in cfg[settings_entry].items():
            registry_obj = registry_cls.get(alias)
            registry_obj and registry_obj.spawn_with_settings(settings).register()

    # Special case for trackers to initialize public trackers automatically.
    for alias, tracker_cls in TrackerClassesRegistry.get().items():

        settings = cfg['trackers'].get(alias)

        if settings is None:

            if issubclass(tracker_cls, GenericPrivateTracker):
                # No use in registering a private tracker without credentials.
                continue

            # Considered public tracker. Use default settings.

        tracker_cls.spawn_with_settings(settings or {}).register()


def get_registered_torrents() -> dict:
    """Returns hash-indexed dictionary with information on torrents
    registered for updates.

    """
    return config.load()['torrents']


def bootstrap():
    """Bootstraps torrt environment,
    Populates RPC and Trackers registries with objects instantiated with settings from config.

    """
    LOGGER.debug('Bootstrapping torrt environment ...')

    import_classes()
    init_object_registries()


def register_torrent(hash_str: str, torrent_data: TorrentData = None, url: str = None):
    """Registers torrent within torrt. Used to register torrents that already exists
    in torrent clients.

    :param hash_str: torrent identifying hash
    :param torrent_data:
    :param url: fallback url that will be used in case torrent comment doesn't contain url

    """
    LOGGER.debug(f'Registering `{hash_str}` torrent ...')

    if torrent_data is None:
        torrent_data = TorrentData()

    if url:
        torrent_data.url = url

    cfg = {'torrents': {}}
    structure_torrent_data(cfg['torrents'], hash_str, torrent_data)
    config.update(cfg)


def unregister_torrent(hash_str: str):
    """Unregisters torrent from torrt. That doesn't remove torrent
    from torrent clients.

    :param hash_str: torrent identifying hash

    """
    LOGGER.debug(f'Unregistering `{hash_str}` torrent ...')

    config.drop_section('torrents', hash_str)


def add_torrent_from_url(url: str, download_to: str = None):
    """Adds torrent from a given URL to torrt and torrent clients,

    :param url: torrent URL
    :param download_to: path to download files from torrent into (in terms of torrent client filesystem)

    """
    LOGGER.debug(f'Adding torrent from `{url}` ...')

    torrent_data = get_torrent_from_url(url)

    if torrent_data is None:
        LOGGER.error(f'Unable to add torrent from `{url}`')
        return

    for rpc_alias, rpc_object in iter_rpc():
        rpc_object.method_add_torrent(torrent_data, download_to=download_to)
        register_torrent(torrent_data.hash, torrent_data)

        LOGGER.info(f'Torrent from `{url}` is added within `{rpc_alias}`')


def remove_torrent(hash_str: str, with_data: bool = False):
    """Removes torrent by its hash from torrt and torrent clients,

    :param hash_str: torrent identifying hash
    :param with_data: flag to also remove files from torrent

    """
    LOGGER.info(f'Removing torrent `{hash_str}` (with data = {with_data}) ...')

    for _, rpc_object in iter_rpc():
        LOGGER.info(f'Removing torrent using `{rpc_object.alias}` RPC ...')
        rpc_object.method_remove_torrent(hash_str, with_data=with_data)

    unregister_torrent(hash_str)


def set_walk_interval(interval_hours: int):
    """Sets torrent updates checks interval (in hours).

    :param interval_hours: hours interval

    """
    config.update({'walk_interval_hours': int(interval_hours)})


def toggle_rpc(alias: str, enabled: bool = True):
    """Enables or disables a given RPC.

    :param alias: PRC alias
    :param enabled: flag to enable or disable

    """
    rpc = RPCClassesRegistry.get(alias)

    if rpc is not None:
        config.update({'rpc': {alias: {'enabled': enabled}}})

        LOGGER.info(f'RPC `{alias}` enabled = {enabled}')

    else:
        LOGGER.info(f'RPC `{alias}` class is not registered')


def walk(forced: bool = False, silent: bool = False, remove_outdated: bool = True):
    """Performs updates check for the registered torrents.

    :param forced: flag to not to count walk interval setting
    :param silent: flag to suppress possible torrt exceptions
    :param remove_outdated: flag to remove torrents that are superseded by a new ones

    """
    LOGGER.info('Torrent walk is triggered')

    now = int(time())
    cfg = config.load()

    next_time = cfg['time_last_check'] + (cfg['walk_interval_hours'] * 3600)

    if forced or now >= next_time:
        LOGGER.info('Torrent walk is started')

        updated = {}

        try:
            updated = update_torrents(cfg['torrents'], remove_outdated=remove_outdated)

        except TorrtException as e:
            if not silent:
                raise

            LOGGER.error(f'Walk failed. Reason: {e}')

        new_cfg = {
            'time_last_check': now
        }

        if updated:

            for old_hash, new_data in updated.items():

                try:
                    cfg['torrents'].pop(old_hash)

                except KeyError:
                    # May be already deleted by `update_torrents` if `remove_outdated` is used.
                    pass

                cfg['torrents'][new_data['hash']] = new_data

            new_cfg['torrents'] = cfg['torrents']

            for _, notifier in iter_notifiers():
                notifier.send(updated)

        # Save updated torrents data into config.
        config.update(new_cfg)

        LOGGER.info('Torrent walk is finished')

    else:
        LOGGER.info(
            'Torrent walk postponed '
            f'till {get_iso_from_timestamp(next_time)} '
            f'(now {get_iso_from_timestamp(now)})'
        )


def update_torrents(torrents: Dict[str, dict], remove_outdated: bool = True) -> Dict[str, dict]:
    """Performs torrent updates.
    Returns hash-indexed dictionary with information on updated torrents

    :param torrents: torrents data indexed with hashes
    :param remove_outdated: flag to remove outdated torrents from torrent clients

    """
    updated_by_hashes = {}
    download_cache: Dict[str, TorrentData] = {}
    hashes = list(torrents)

    for _, rpc_object in iter_rpc():

        LOGGER.info(f'Getting torrents from `{rpc_object.alias}` ...')
        rpc_torrents = rpc_object.method_get_torrents(hashes)

        if not rpc_torrents:
            LOGGER.info('  No relevant torrents found')

        for rpc_torrent in rpc_torrents:
            LOGGER.info(f"  Processing `{rpc_torrent['name']}`...")

            page_url = get_url_from_string(rpc_torrent['comment'])
            if not page_url:
                page_url = torrents[rpc_torrent['hash']].get('url', None) if torrents else None

            if not page_url:
                LOGGER.warning(f"    Torrent `{rpc_torrent['name']}` has no link in comment. Skipped")
                continue

            if page_url in download_cache:
                tracker_torrent = download_cache[page_url]

            else:
                tracker_torrent = get_torrent_from_url(page_url)
                download_cache[page_url] = tracker_torrent

            if tracker_torrent is None:
                LOGGER.error(f'    Unable to get torrent from `{page_url}`')
                continue

            if rpc_torrent['hash'] == tracker_torrent.hash:
                LOGGER.info('    No updates')
                continue

            LOGGER.debug('    Update is available')

            try:
                rpc_object.method_add_torrent(
                    tracker_torrent,
                    rpc_torrent['download_to'],
                    params=rpc_torrent.get('params', None)
                )
                tracker_torrent.url = page_url

                LOGGER.info('    Torrent is updated')

                structure_torrent_data(updated_by_hashes, rpc_torrent['hash'], tracker_torrent)

            except TorrtRPCException as e:
                LOGGER.error(f'    Unable to replace torrent: {e}')

            else:
                unregister_torrent(rpc_torrent['hash'])

                if remove_outdated:
                    rpc_object.method_remove_torrent(rpc_torrent['hash'])

    return updated_by_hashes


def run_bots(aliases: List[str] = None):
    """Run aliased bots one after another.

    :param aliases:

    """
    aliases = aliases or []

    for alias, bot_object in iter_bots():

        if aliases and alias not in aliases:
            continue

        bot_object.run()
