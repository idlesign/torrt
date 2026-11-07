import logging
import sys
from datetime import datetime
from time import time
from typing import TYPE_CHECKING, Optional

from .base_bot import BotRegistrationFailed
from .base_tracker import GenericPrivateTracker
from .exceptions import TorrtException, TorrtRPCException
from .incomplete import IncompleteOps
from .utils import (
    DATETIME_FORMAT,
    BotClassesRegistry,
    NotifierClassesRegistry,
    RPCClassesRegistry,
    TorrentData,
    TrackerClassesRegistry,
    TrackerObjectsRegistry,
    config,
    configure_entity,
    get_iso_from_timestamp,
    get_torrent_from_url,
    get_url_from_string,
    import_classes,
    iter_bots,
    iter_notifiers,
    iter_rpc,
    structure_torrent_data,
)

try:
    from envbox import get_environment
    # Allow env vars from .env files.
    environ = get_environment()

except ImportError:
    from os import environ

if TYPE_CHECKING:
    from .base_bot import BaseBot
    from .base_notifier import BaseNotifier
    from .base_rpc import BaseRPC
    from .base_tracker import BaseTracker

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


def configure_logging(log_level: int = logging.INFO, *, show_logger_names: bool = False):
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
    }

    for settings_entry, registry_cls in settings_to_registry_map.items():

        for alias, settings in cfg[settings_entry].items():
            registry_obj = registry_cls.get(alias)
            registry_obj and registry_obj.spawn_with_settings(settings).register()

    # Special treatment for bots, as they may require additional dependencies
    for alias, settings in cfg['bots'].items():
        registry_obj = BotClassesRegistry.get(alias)

        try:
            bot_obj = registry_obj.spawn_with_settings(settings)

        except BotRegistrationFailed as e:
            LOGGER.warning(f'`{alias}` bot is configured, but failed to register: {e}')

        else:
            bot_obj.register()

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


def register_torrent(hash_str: str, *, torrent_data: TorrentData = None, url: str = '', params: dict | None = None):
    """Registers torrent within torrt. Used to register torrents that already exists
    in torrent clients.

    :param hash_str: torrent identifying hash
    :param torrent_data:
    :param url: fallback url that will be used in case torrent comment doesn't contain url
    :param params: optional parameters to pass to RPC

    """
    LOGGER.debug(f'Registering `{hash_str}` torrent ...')

    if torrent_data is None:
        torrent_data = TorrentData()

    if url:
        torrent_data.url = url

    if not torrent_data.params:
        torrent_data.set_params(params)

    cfg = {'torrents': {}}
    structure_torrent_data(cfg['torrents'], hash_str, torrent_data)
    config.update(cfg)


def unregister_torrent(hash_str: str):
    """Unregisters torrent from torrt. That doesn't remove torrent
    from torrent clients.

    :param hash_str: torrent identifying hash

    """
    LOGGER.debug(f'Unregistering `{hash_str}` torrent ...')

    IncompleteOps(config).cancel(hash_str)


def add_torrent_from_url(url: str, *, download_to: str = '', params: dict | None = None):
    """Adds torrent from a given URL to torrt and torrent clients,

    :param url: torrent URL
    :param download_to: path to download files from torrent into (in terms of torrent client filesystem)
    :param params: optional parameters to pass to RPC

    """
    LOGGER.debug("Adding torrent from `%s` ...", url)

    torrent_data = get_torrent_from_url(url)

    if torrent_data is None:
        LOGGER.error("Unable to add torrent from `%s`", url)
        return

    torrent_data.set_params(params)

    if torrent_data.magnet:
        clients = {
            alias: {"download_to": download_to, "params": params}
            for alias, _ in iter_rpc()
        }

        if clients:
            IncompleteOps(config).queue(torrent_data, clients)
            check_incomplete_ops()

        return

    for rpc_alias, rpc_object in iter_rpc():
        rpc_object.method_add_torrent(torrent_data, download_to=download_to, params=params)
        register_torrent(torrent_data.hash, torrent_data=torrent_data, params=params)

        LOGGER.info(f'Torrent from `{url}` is added within `{rpc_alias}`')


def remove_torrent(hash_str: str, *, with_data: bool = False):
    """Removes torrent by its hash from torrt and torrent clients,

    :param hash_str: torrent identifying hash
    :param with_data: flag to also remove files from torrent

    """
    LOGGER.info(f'Removing torrent `{hash_str}` (with data = {with_data}) ...')
    pending = IncompleteOps(config)

    if pending.request_removal(hash_str, with_data=with_data):
        pending.process(dict(iter_rpc()))
        return

    for _, rpc_object in iter_rpc():
        LOGGER.info(f'Removing torrent using `{rpc_object.alias}` RPC ...')
        rpc_object.method_remove_torrent(hash_str, with_data=with_data)

    unregister_torrent(hash_str)


def set_walk_interval(interval_hours: int):
    """Sets torrent updates checks interval (in hours).

    :param interval_hours: hours interval

    """
    config.update({'walk_interval_hours': int(interval_hours)})

def set_prefer_magnet(*, enabled: bool) -> None:
    """Prefer extracted magnet links for the CLI, bots and automatic updates."""

    if not isinstance(enabled, bool):
        raise ValueError("Magnet preference must be a boolean")

    config.update({"prefer_magnet": enabled})

def check_incomplete_ops(*, notify: bool = True) -> dict[str, dict]:
    """Check unfinished magnet operations without scraping pages or waiting for peers."""

    if not config.load()["incomplete"]:
        return {}

    clients = dict(iter_rpc())
    updated = IncompleteOps(config).process(clients)

    if notify and updated:

        for _, notifier in iter_notifiers():
            notifier.send(updated)

    return updated


def toggle_rpc(alias: str, *, enabled: bool = True):
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


def walk(*, forced: bool = False, silent: bool = False, remove_outdated: bool = True) -> None:
    """Performs updates check for the registered torrents.

    :param forced: flag not to count walk interval setting
    :param silent: flag to suppress possible torrt exceptions
    :param remove_outdated: flag to remove torrents that are superseded by a new ones

    """
    LOGGER.info('Torrent walk is triggered')

    now = int(time())
    updated = {}

    try:
        updated = check_incomplete_ops(notify=False)

    except TorrtException as error:

        if not silent:
            raise

        LOGGER.error("Incomplete operations check failed: %s", error)

    cfg = config.load()

    next_time = cfg['time_last_check'] + (cfg['walk_interval_hours'] * 3600)

    if forced or now >= next_time:
        LOGGER.info('Torrent walk is started')

        for tracker in TrackerObjectsRegistry.get().values():
            tracker._torrent_page = None
            tracker._torrent_page_url = ""

        try:
            updated.update(update_torrents(cfg['torrents'], remove_outdated=remove_outdated))

        except TorrtException as e:
            if not silent:
                raise

            LOGGER.error(f'Walk failed. Reason: {e}')

        config.update({"time_last_check": now})

        LOGGER.info('Torrent walk is finished')

    else:
        LOGGER.info(
            'Torrent walk postponed '
            f'till {get_iso_from_timestamp(next_time)} '
            f'(now {get_iso_from_timestamp(now)})'
        )

    if updated:

        for _, notifier in iter_notifiers():
            notifier.send(updated)


def update_torrents(torrents: dict[str, dict], *, remove_outdated: bool = True) -> dict[str, dict]:
    """Performs torrent updates.
    Returns hash-indexed dictionary with information on updated torrents

    :param torrents: torrents data indexed with hashes
    :param remove_outdated: flag to remove outdated torrents from torrent clients

    """
    updated_by_hashes = {}
    download_cache: dict[str, TorrentData | None] = {}
    hashes = list(torrents)
    pending = IncompleteOps(config)
    pending_hashes = pending.get_hashes()
    clients = dict(iter_rpc())
    torrents_by_hash: dict[str, dict[str, dict]] = {}
    queued_keys: set[str] = set()

    # Discover every target before saving an operation spanning multiple clients.
    for alias, rpc_object in clients.items():

        LOGGER.info(f'Getting torrents from `{rpc_object.alias}` ...')
        rpc_torrents = rpc_object.method_get_torrents(hashes)

        if not rpc_torrents:
            LOGGER.info('  No relevant torrents found')

        for rpc_torrent in rpc_torrents:

            if rpc_torrent["hash"] in torrents and rpc_torrent["hash"] not in pending_hashes:
                torrents_by_hash.setdefault(rpc_torrent["hash"], {})[alias] = rpc_torrent

    for old_hash, targets in torrents_by_hash.items():
        source_torrent = next(iter(targets.values()))
        LOGGER.info("  Processing `%s`...", source_torrent["name"])

        page_url = get_url_from_string(source_torrent["comment"])

        if not page_url:
            page_url = torrents[old_hash].get("url")

        if not page_url:
            LOGGER.warning("    Torrent %s has no tracker page URL. Skipped", old_hash)
            continue

        if page_url in download_cache:
            tracker_torrent = download_cache[page_url]

        else:
            raw_last_updated = torrents[old_hash].get("page", {}).get("date_updated")
            # Keep stored tracker dates naive, just like dates extracted from pages.
            last_updated = (
                datetime.strptime(raw_last_updated, DATETIME_FORMAT) if raw_last_updated else None  # noqa: DTZ007
            )
            tracker_torrent = get_torrent_from_url(page_url, last_updated)
            download_cache[page_url] = tracker_torrent

        if tracker_torrent is None:
            LOGGER.error("    Unable to get torrent from `%s`", page_url)
            continue

        if old_hash == tracker_torrent.hash:
            LOGGER.info("    No updates")
            continue

        tracker_torrent.url = page_url

        if tracker_torrent.magnet:
            key = pending.queue(
                tracker_torrent,
                {
                    alias: {"download_to": target["download_to"], "params": target.get("params")}
                    for alias, target in targets.items()
                },
                old_hash=old_hash, remove_outdated=remove_outdated,
            )
            queued_keys.add(key)
            continue

        complete = True

        for alias, target in targets.items():
            rpc_object = clients[alias]

            try:
                rpc_object.method_add_torrent(
                    tracker_torrent,
                    download_to=target["download_to"],
                    params=target.get("params"),
                )
                register_torrent(tracker_torrent.hash, torrent_data=tracker_torrent)

                if remove_outdated:
                    rpc_object.method_remove_torrent(old_hash)

            except TorrtRPCException as e:
                complete = False
                LOGGER.error(f'    Unable to replace torrent: {e}')

        if complete:
            settings = config.load()
            settings["torrents"].pop(old_hash, None)
            config.save(settings)
            structure_torrent_data(updated_by_hashes, old_hash, tracker_torrent)

    # Existing operations were already checked at the start of the walk.
    updated_by_hashes.update(pending.process(clients, keys=queued_keys))

    return updated_by_hashes


def run_bots(aliases: list[str] | None = None):
    """Run aliased bots one after another.

    :param aliases:

    """
    aliases = aliases or []
    bot_hit = False

    for alias, bot_object in iter_bots():
        bot_hit = True

        if aliases and alias not in aliases:
            continue

        bot_object.run()

    if not bot_hit:
        # if there is no bots to run - just exit
        sys.exit(1)
