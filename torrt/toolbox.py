import logging
from time import time

from torrt.base_rpc import TorrtRPCException
from torrt.utils import RPCClassesRegistry, TrackerClassesRegistry, TorrtConfig, TorrtException, \
    get_url_from_string, get_iso_from_timestamp, import_classes, structure_torrent_data, get_torrent_from_url, iter_rpc


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
    :return:
    """
    LOGGER.info('Configuring `%s` RPC ...' % rpc_alias)

    rpc_class = RPCClassesRegistry.get(rpc_alias)
    if rpc_class is not None:
        rpc_obj = rpc_class.spawn_with_settings(settings_dict)
        version = rpc_obj.method_get_version()
        if version:
            rpc_obj.enabled = True
            rpc_obj.save_settings()
            LOGGER.info('RPC `%s` is configured' % rpc_alias)
        else:
            LOGGER.error('RPC `%s` configuration failed. Check your settings' % rpc_alias)
    else:
        LOGGER.error('RPC `%s` is unknown' % rpc_alias)


def configure_tracker(tracker_alias, settings_dict):
    """Configures tracker using given settings.
    Saves successful configuration.

    :param tracker_alias: tracker alias
    :param settings_dict: settings dictionary to configure tracker with
    :return:
    """
    LOGGER.info('Configuring `%s` tracker ...' % tracker_alias)

    tracker_class = TrackerClassesRegistry.get(tracker_alias)
    if tracker_class is not None:
        tracker_obj = tracker_class.spawn_with_settings(settings_dict)
        configured = tracker_obj.test_configuration()
        if configured:
            tracker_obj.save_settings()
            LOGGER.info('Tracker `%s` is configured' % tracker_alias)
        else:
            LOGGER.error('Tracker `%s` configuration failed. Check your settings' % tracker_alias)
    else:
        LOGGER.error('Tracker `%s` is unknown' % tracker_alias)


def init_object_registries():
    """Initializes RPC and tracker objects registries with settings
    from configuration file.

    :return:
    """
    LOGGER.debug('Initializing objects registries from configuration file ...')
    cfg = TorrtConfig.load()

    for alias, rpc_settings in cfg['rpc'].items():
        rpc = RPCClassesRegistry.get(alias)
        if rpc is not None:
            obj = rpc.spawn_with_settings(rpc_settings)
            obj.register()

    for domain, tracker_settings in cfg['trackers'].items():
        tracker = TrackerClassesRegistry.get(domain)
        if tracker is not None:
            obj = tracker.spawn_with_settings(tracker_settings)
            obj.register()


def get_registerd_torrents():
    """Returns hash-indexed dictionary with information on torrents
    registered for updates.

    :return: torrents dict
    :rtype: dict
    """
    return TorrtConfig.load()['torrents']


def bootstrap():
    """Bootstraps torrt environment,
    Populates RPC and Trackers registries with objects instantiated with settings from config.

    :return:
    """
    LOGGER.debug('Bootstrapping torrt environment ...')
    import_classes()
    init_object_registries()


def register_torrent(hash, torrent_data=None):
    """Registers torrent within torrt. Used to register torrents that already exists
    in torrent clients.

    :param hash: str - torrent identifying hash
    :param torrent_data: dict
    :return:
    """
    LOGGER.info('Registering `%s` torrent ...' % hash)
    if torrent_data is None:
        torrent_data = {}
    cfg = {'torrents': {}}
    structure_torrent_data(cfg['torrents'], hash, torrent_data)
    TorrtConfig.update(cfg)


def unregister_torrent(hash):
    """Unregisters torrent from torrt. That doesn't remove torrent
    from torrent clients.

    :param hash: str - torrent identifying hash
    :return:
    """
    LOGGER.info('Unregistering `%s` torrent ...' % hash)
    try:
        cfg = TorrtConfig.load()
        del cfg['torrents'][hash]
        TorrtConfig.save(cfg)
    except KeyError:
        pass  # Torrent was not known by torrt


def add_torrent_from_url(url, download_to=None):
    """Adds torrent from a given URL to torrt and torrent clients,

    :param url: str - torrent URL
    :param download_to: str or None - path to download files from torrent into (in terms of torrent client filesystem)
    :return:
    """
    LOGGER.info('Adding torrent from `%s` ...' % url)

    torrent_data = get_torrent_from_url(url)
    if torrent_data is None:
        LOGGER.error('Unable to add torrent from `%s`' % url)
    else:
        for rpc_alias, rpc_object in iter_rpc():
            rpc_object.method_add_torrent(torrent_data['torrent'], download_to=download_to)
            register_torrent(torrent_data['hash'], torrent_data)
            LOGGER.info('Torrent from `%s` is added within `%s`' % (url, rpc_alias))


def remove_torrent(hash, with_data=False):
    """Removes torrent by its hash from torrt and torrent clients,

    :param hash: str - torrent identifying hash
    :param with_data: bool - flag to also remove files from torrent
    :return:
    """
    LOGGER.info('Removing torrent `%s` (with data = %s) ...' % (hash, with_data))

    for rpc_alias, rpc_object in iter_rpc():
        LOGGER.info('Removing torrent using `%s` RPC ...' % rpc_object.alias)
        rpc_object.method_remove_torrent(hash, with_data=with_data)

    unregister_torrent(hash)


def set_walk_interval(interval_hours):
    """Sets torrent updates checks interval (in hours).

    :param interval_hours: int - hours interval
    :return:
    """
    TorrtConfig.update({'walk_interval_hours': int(interval_hours)})


def toggle_rpc(alias, enabled=True):
    """Enables or disables a given RPC.

    :param alias: str - PRC alias
    :param enabled: bool - flag to enable or disable
    :return:
    """
    rpc = RPCClassesRegistry.get(alias)
    if rpc is not None:
        TorrtConfig.update({'rpc': {alias: {'enabled': enabled}}})
        LOGGER.info('RPC `%s` enabled = %s' % (alias, enabled))
    else:
        LOGGER.info('RPC `%s` class is not registered' % alias)


def walk(forced=False, silent=False):
    """Performs updates check for the registered torrents.

    :param forced: bool - flag to not to count walk interval setting
    :param silent: bool - flag to suppress possible exceptions
    :return:
    """
    LOGGER.info('Torrent walk is triggered')
    now = int(time())
    cfg = TorrtConfig.load()
    next_time = cfg['time_last_check'] + (cfg['walk_interval_hours'] * 3600)
    if forced or now >= next_time:
        LOGGER.info('Torrent walk is started')

        updated = {}
        try:
            updated = update_torrents(cfg['torrents'].keys(), remove_outdated=False)
        except TorrtException as e:
            if not silent:
                raise
            else:
                LOGGER.error('Walk failed. Reason: %s' % e.message)

        new_cfg = {
            'time_last_check': now
        }

        if updated:
            for old_hash, new_data in updated.items():
                del cfg['torrents'][old_hash]
                cfg['torrents'][new_data['hash']] = new_data
            new_cfg['torrents'] = cfg['torrents']

        # Save updated torrents data into config.
        TorrtConfig.update(new_cfg)

        LOGGER.info('Torrent walk is finished')
    else:
        LOGGER.info('Torrent walk postponed till %s (now %s)' % (get_iso_from_timestamp(next_time), get_iso_from_timestamp(now)))


def update_torrents(hashes, remove_outdated=True):
    """Performs torrent updates.

    :param hashes: list - torrent identifying hashes
    :param remove_outdated: bool - flag to remove outdated torrents from torrent clients
    :return: hash-indexed dictionary with information on updated torrents
    :rtype: dict
    """
    updated_by_hashes = {}

    for rpc_alias, rpc_object in iter_rpc():
        LOGGER.info('Getting torrents using `%s` RPC ...' % rpc_object.alias)
        torrents = rpc_object.method_get_torrents(hashes)

        if not torrents:
            LOGGER.info('No significant torrents found with `%s` RPC' % rpc_object.alias)

        for existing_torrent in torrents:
            LOGGER.info('Processing `%s` torrent with `%s` RPC ...' % (existing_torrent['name'], rpc_object.alias))

            page_url = get_url_from_string(existing_torrent['comment'])
            new_torrent = get_torrent_from_url(page_url)

            if new_torrent is None:
                LOGGER.error('Unable to get torrent from `%s`' % page_url)
                continue

            if existing_torrent['hash'] == new_torrent['hash']:
                LOGGER.info('Torrent `%s` is up-to-date' % existing_torrent['name'])
                continue

            LOGGER.info('Torrent `%s` update is available' % existing_torrent['name'])
            try:
                rpc_object.method_add_torrent(new_torrent['torrent'], existing_torrent['download_to'])
                LOGGER.info('Torrent `%s` is updated' % existing_torrent['name'])
                structure_torrent_data(updated_by_hashes, existing_torrent['hash'], new_torrent)
            except TorrtRPCException as e:
                LOGGER.error('Unable to replace `%s` torrent: %s' % (existing_torrent['name'], e.message))
            else:
                if remove_outdated:
                    rpc_object.method_remove_torrent(existing_torrent['hash'])

    return updated_by_hashes
