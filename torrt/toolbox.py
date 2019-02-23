import logging
from time import time
from warnings import warn

from torrt.base_rpc import TorrtRPCException
from torrt.base_tracker import GenericPrivateTracker
from torrt.exceptions import TorrtException
from torrt.utils import RPCClassesRegistry, TrackerClassesRegistry, config, get_url_from_string, \
    get_iso_from_timestamp, import_classes, structure_torrent_data, get_torrent_from_url, iter_rpc, \
    NotifierClassesRegistry, iter_notifiers, BotClassesRegistry, iter_bots, configure_entity

if False:  # pragama: nocover
    from torrt.base_rpc import BaseRPC
    from torrt.base_tracker import BaseTracker
    from torrt.base_notifier import BaseNotifier
    from torrt.base_bot import BaseBot

LOGGER = logging.getLogger(__name__)


def configure_logging(log_level=logging.INFO, show_logger_names=False):
    """Performs basic logging configuration.

    :param log_level: logging level, e.g. logging.DEBUG
    :param show_logger_names: bool - flag to show logger names in output
    :return:
    """
    format_str = '%(levelname)s: %(message)s'

    if show_logger_names:
        format_str = '%(name)s\t\t ' + format_str

    logging.basicConfig(format=format_str, level=log_level)
    requests_logger = logging.getLogger('requests')
    requests_logger.setLevel(logging.ERROR)


def configure_rpc(rpc_alias, settings_dict):
    """Configures RPC using given settings.
    Saves successful configuration.

    :param rpc_alias: RPC alias
    :param settings_dict: settings dictionary to configure RPC with
    :rtype: BaseRPC|None
    """
    rpc = configure_entity('RPC', RPCClassesRegistry, rpc_alias, settings_dict)

    if rpc:
        rpc.enabled = True

    return rpc


def configure_tracker(tracker_alias, settings_dict):
    """Configures tracker using given settings.
    Saves successful configuration.

    :param tracker_alias: tracker alias
    :param settings_dict: settings dictionary to configure tracker with
    :rtype: BaseTracker|None
    """
    return configure_entity('Tracker', TrackerClassesRegistry, tracker_alias, settings_dict)


def configure_notifier(notifier_alias, settings_dict):
    """Configures notifier using given settings.
    Saves successful configuration.

    :param notifier_alias: notifier alias
    :param settings_dict: settings dictionary to configure notifier with
    :rtype: BaseNotifier|None
    """
    return configure_entity('Notifier', NotifierClassesRegistry, notifier_alias, settings_dict)


def configure_bot(bot_alias, settings_dict):
    """Configures bot using given settings.
    Saves successful configuration.

    :param bot_alias: bot alias
    :param settings_dict: settings dictionary to configure bot with
    :rtype: BaseBot|None
    """
    return configure_entity('Bot', BotClassesRegistry, bot_alias, settings_dict)


def remove_notifier(alias):
    """Removes notifier by alias

    :param alias: str - Notifier alias to remove.

    :return:
    """
    LOGGER.info('Removing `%s` notifier ...', alias)
    config.drop_section('notifiers', alias)


def remove_bot(alias):
    """Removes bot by alias

    :param alias: str - Bot alias to remove.

    :return:
    """
    LOGGER.info('Removing `%s` bot ...', alias)
    config.drop_section('bots', alias)


def init_object_registries():
    """Initializes RPC and tracker objects registries with settings
    from configuration file.

    :return:
    """
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


def get_registered_torrents():
    """Returns hash-indexed dictionary with information on torrents
    registered for updates.

    :return: torrents dict
    :rtype: dict
    """
    return config.load()['torrents']


def get_registerd_torrents():
    warn('`get_registerd_torrents()` is deprecated and will be removed in 1.0. '
         'Please use `get_registered_torrents()` instead.', DeprecationWarning, stacklevel=2)
    return get_registered_torrents()


def bootstrap():
    """Bootstraps torrt environment,
    Populates RPC and Trackers registries with objects instantiated with settings from config.

    :return:
    """
    LOGGER.debug('Bootstrapping torrt environment ...')
    import_classes()
    init_object_registries()


def register_torrent(hash_str, torrent_data=None, url=None):
    """Registers torrent within torrt. Used to register torrents that already exists
    in torrent clients.

    :param hash_str: str - torrent identifying hash
    :param torrent_data: dict
    :param url: fallback url that will be used in case torrent comment doesn't contain url
    :return:
    """
    LOGGER.debug('Registering `%s` torrent ...', hash_str)

    if torrent_data is None:
        torrent_data = {}

    if url:
        torrent_data['url'] = url

    cfg = {'torrents': {}}
    structure_torrent_data(cfg['torrents'], hash_str, torrent_data)
    config.update(cfg)


def unregister_torrent(hash_str):
    """Unregisters torrent from torrt. That doesn't remove torrent
    from torrent clients.

    :param hash_str: str - torrent identifying hash
    :return:
    """
    LOGGER.debug('Unregistering `%s` torrent ...', hash_str)
    config.drop_section('torrents', hash_str)


def add_torrent_from_url(url, download_to=None):
    """Adds torrent from a given URL to torrt and torrent clients,

    :param url: str - torrent URL
    :param download_to: str or None - path to download files from torrent into (in terms of torrent client filesystem)
    :return:
    """
    LOGGER.debug('Adding torrent from `%s` ...', url)

    torrent_data = get_torrent_from_url(url)

    if torrent_data is None:
        LOGGER.error('Unable to add torrent from `%s`', url)

    else:
        for rpc_alias, rpc_object in iter_rpc():
            rpc_object.method_add_torrent(torrent_data['torrent'], download_to=download_to)
            register_torrent(torrent_data['hash'], torrent_data, url)
            LOGGER.info('Torrent from `%s` is added within `%s`', url, rpc_alias)


def remove_torrent(hash_str, with_data=False):
    """Removes torrent by its hash from torrt and torrent clients,

    :param hash_str: str - torrent identifying hash
    :param with_data: bool - flag to also remove files from torrent
    :return:
    """
    LOGGER.info('Removing torrent `%s` (with data = %s) ...', hash_str, with_data)

    for _, rpc_object in iter_rpc():
        LOGGER.info('Removing torrent using `%s` RPC ...', rpc_object.alias)
        rpc_object.method_remove_torrent(hash_str, with_data=with_data)

    unregister_torrent(hash_str)


def set_walk_interval(interval_hours):
    """Sets torrent updates checks interval (in hours).

    :param interval_hours: int - hours interval
    :return:
    """
    config.update({'walk_interval_hours': int(interval_hours)})


def toggle_rpc(alias, enabled=True):
    """Enables or disables a given RPC.

    :param alias: str - PRC alias
    :param enabled: bool - flag to enable or disable
    :return:
    """
    rpc = RPCClassesRegistry.get(alias)

    if rpc is not None:
        config.update({'rpc': {alias: {'enabled': enabled}}})
        LOGGER.info('RPC `%s` enabled = %s', alias, enabled)

    else:
        LOGGER.info('RPC `%s` class is not registered', alias)


def walk(forced=False, silent=False, remove_outdated=True):
    """Performs updates check for the registered torrents.

    :param forced: bool - flag to not to count walk interval setting
    :param silent: bool - flag to suppress possible exceptions
    :param remove_outdated: bool - flag to remove torrents that are superseded by a new ones
    :return:
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

            LOGGER.error('Walk failed. Reason: %s', e)

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
            'Torrent walk postponed till %s (now %s)',
            get_iso_from_timestamp(next_time),
            get_iso_from_timestamp(now)
        )


def update_torrents(hashes, remove_outdated=True):
    """Performs torrent updates.

    :param hashes: list - torrent identifying hashes
    :param remove_outdated: bool - flag to remove outdated torrents from torrent clients
    :return: hash-indexed dictionary with information on updated torrents
    :rtype: dict
    """
    updated_by_hashes = {}
    download_cache = {}

    to_check = None

    if isinstance(hashes, list):
        warn('`hashes` argument of list type is deprecated and will be removed in 1.0. '
             'Please pass the argument of Dict[hash, torrent] type instead.', DeprecationWarning, stacklevel=2)

    else:
        to_check = hashes
        hashes = list(to_check.keys())

    for _, rpc_object in iter_rpc():

        LOGGER.info('Getting torrents from `%s` ...', rpc_object.alias)
        torrents = rpc_object.method_get_torrents(hashes)

        if not torrents:
            LOGGER.info('  No significant torrents found')

        for existing_torrent in torrents:
            LOGGER.info('  Processing `%s`...', existing_torrent['name'])

            page_url = get_url_from_string(existing_torrent['comment'])
            if not page_url:
                page_url = to_check[existing_torrent['hash']].get('url', None) if to_check else None

            if not page_url:
                LOGGER.warning('    Torrent `%s` has no link in comment. Skipped', existing_torrent['name'])
                continue

            if page_url in download_cache:
                new_torrent = download_cache[page_url]

            else:
                new_torrent = get_torrent_from_url(page_url)
                download_cache[page_url] = new_torrent

            if new_torrent is None:
                LOGGER.error('    Unable to get torrent from `%s`', page_url)
                continue

            if existing_torrent['hash'] == new_torrent['hash']:
                LOGGER.info('    No updates')
                continue

            LOGGER.debug('    Update is available')

            try:
                rpc_object.method_add_torrent(new_torrent['torrent'], existing_torrent['download_to'])
                new_torrent['url'] = page_url
                LOGGER.info('    Torrent is updated')
                structure_torrent_data(updated_by_hashes, existing_torrent['hash'], new_torrent)

            except TorrtRPCException as e:
                LOGGER.error('    Unable to replace torrent: %s', e.message)

            else:
                unregister_torrent(existing_torrent['hash'])

                if remove_outdated:
                    rpc_object.method_remove_torrent(existing_torrent['hash'])

    return updated_by_hashes


def run_bots(aliases=None):

    aliases = aliases or []

    for alias, bot_object in iter_bots():
        if aliases and alias not in aliases:
            continue

        bot_object.run()
