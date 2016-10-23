import argparse
import logging

from torrt import VERSION
from torrt.utils import RPCClassesRegistry, RPCObjectsRegistry, TrackerClassesRegistry, NotifierClassesRegistry, \
    NotifierObjectsRegistry
from torrt.toolbox import add_torrent_from_url, remove_torrent, \
    register_torrent, unregister_torrent, get_registered_torrents, \
    walk, set_walk_interval, toggle_rpc, configure_logging, bootstrap, \
    configure_rpc, configure_tracker, configure_notifier, remove_notifier


LOGGER = logging.getLogger(__name__)

# todo cipher passwords


def process_commands():

    def settings_dict_from_list(lst):
        settings_dict = {}
        for s in lst:
            splitted = s.split('=')
            settings_dict[splitted[0]] = splitted[1]
        return settings_dict

    arg_parser = argparse.ArgumentParser('torrt', description='Automates torrent updates for you.')
    arg_parser.add_argument('--version', action='version', version='%(prog)s ' + '.'.join(map(str, VERSION)))

    subp_main = arg_parser.add_subparsers(title='Supported commands', dest='command')

    subp_main.add_parser('list_rpc', help='Shows known RPCs aliases')
    subp_main.add_parser('list_trackers', help='Shows known trackers aliases')
    subp_main.add_parser('list_torrents', help='Shows torrents registered for updates')
    subp_main.add_parser('list_notifiers', help='Shows configured notifiers')

    parser_configure_tracker = subp_main.add_parser(
        'configure_tracker', help='Sets torrent tracker settings (login credentials, etc.)',
        description='E.g.: configure_tracker rutracker.org username=idle password=pSW0rt')
    parser_configure_tracker.add_argument(
        'tracker_alias', help='Tracker alias (usually domain) to apply settings to')
    parser_configure_tracker.add_argument(
        'settings',
        help='Settings string, format: setting1=val1 setting2=val2. '
             'Supported settings (any of): username, password',
        nargs='*')

    parser_configure_rpc = subp_main.add_parser(
        'configure_rpc', help='Sets RPCs settings (login credentials, etc.)',
        description='E.g.: configure_rpc transmission user=idle password=pSW0rt')
    parser_configure_rpc.add_argument(
        'rpc_alias', help='RPC alias to apply settings to')
    parser_configure_rpc.add_argument(
        'settings',
        help='Settings string, format: setting1=val1 setting2=val2. '
             'Supported settings (any of): url, host, port, user, password',
        nargs='*')

    parser_configure_notifier = subp_main.add_parser(
        'configure_notifier', help='Sets Notifiers settings (smtp credentials, etc.)',
        description='E.g.: configure_notifier email email=your@email.com user=idle password=pSW0rt')
    parser_configure_notifier.add_argument(
        'notifier_alias', help='Notifier alias to apply settings to')
    parser_configure_notifier.add_argument(
        'settings',
        help='Settings string, format: setting1=val1 setting2=val2. '
             'Supported settings for email notifier (any of): email, host, port, use_tls, user, password.'
             'Supported settings for telegram notifier: token, chat_id.',
        nargs='*')

    parser_walk = subp_main.add_parser(
        'walk', help='Walks through registered torrents and performs automatic updates')
    parser_walk.add_argument(
        '-f', help='Forces walk. Forced walks do not respect walk interval settings', dest='forced',
        action='store_true')

    parser_set_interval = subp_main.add_parser(
        'set_walk_interval', help='Sets an interval *in hours* between consecutive torrent updates checks')
    parser_set_interval.add_argument(
        'walk_interval', help='Interval *in hours* between consecutive torrent updates checks')

    parser_enable_rpc = subp_main.add_parser('enable_rpc', help='Enables RPC by its alias')
    parser_enable_rpc.add_argument('alias', help='Alias of RPC to enable')

    parser_disable_rpc = subp_main.add_parser('disable_rpc', help='Disables RPC by its alias')
    parser_disable_rpc.add_argument('alias', help='Alias of RPC to disable')

    parser_add_torrent = subp_main.add_parser(
        'add_torrent', help='Adds torrent from an URL both to torrt and torrent clients')
    parser_add_torrent.add_argument(
        'url', help='URL to download torrent from')
    parser_add_torrent.add_argument(
        '-d',
        help='Destination path to download torrent contents into (in filesystem where torrent client daemon works)',
        dest='download_to', default=None)

    parser_remove_torrent = subp_main.add_parser(
        'remove_torrent', help='Removes torrent by its hash both from torrt and torrent clients')
    parser_remove_torrent.add_argument(
        'hash', help='Torrent identifying hash')
    parser_remove_torrent.add_argument(
        '-d', help='If set data downloaded for torrent will also be removed',
        dest='delete_data', action='store_true')

    parser_register_torrent = subp_main.add_parser(
        'register_torrent',
        help='Registers torrent within torrt by its hash (for torrents already existing at torrent clients)')
    parser_register_torrent.add_argument(
        'hash', help='Torrent identifying hash')

    parser_unregister_torrent = subp_main.add_parser(
        'unregister_torrent', help='Unregisters torrent from torrt by its hash')
    parser_unregister_torrent.add_argument(
        'hash', help='Torrent identifying hash')

    parser_remove_notifier = subp_main.add_parser(
        'remove_notifier', help='Remove configured notifier by its alias')
    parser_remove_notifier.add_argument('alias', help='Alias of notifier to remove')

    for parser in subp_main.choices.values():
        parser.add_argument('--verbose', help='Switch to show debug messages', dest='verbose', action='store_true')

    args = arg_parser.parse_args()
    args = vars(args)

    loggin_level = logging.INFO
    if args['verbose']:
        loggin_level = logging.DEBUG

    configure_logging(loggin_level)
    bootstrap()

    if args['command'] == 'enable_rpc':
        toggle_rpc(args['alias'], True)

    elif args['command'] == 'disable_rpc':
        toggle_rpc(args['alias'], False)

    elif args['command'] == 'list_trackers':

        for tracker_alias, _ in TrackerClassesRegistry.get().items():
            LOGGER.info(tracker_alias)

    elif args['command'] == 'list_rpc':
        rpc_statuses = {}

        for rpc_alias, rpc in RPCClassesRegistry.get().items():
            rpc_statuses[rpc_alias] = 'unconfigured'

        for rpc_alias, rpc in RPCObjectsRegistry.get().items():
            rpc_statuses[rpc_alias] = 'enabled' if rpc.enabled else 'disabled'

        for rpc_alias, rpc_status in rpc_statuses.items():
            LOGGER.info('%s\t status=%s', rpc_alias, rpc_status)

    elif args['command'] == 'list_torrents':
        for torrent_hash, torrent_data in get_registered_torrents().items():
            LOGGER.info('%s\t%s', torrent_hash, torrent_data['name'])

    elif args['command'] == 'list_notifiers':
        notifiers = {}
        for notifier_alias in NotifierClassesRegistry.get().keys():
            notifiers[notifier_alias] = 'unconfigured'

        for notifier_alias in NotifierObjectsRegistry.get().keys():
            notifiers[notifier_alias] = 'enabled'

        for notifier_alias, notifier_status in notifiers.items():
            LOGGER.info('%s\t status=%s', notifier_alias, notifier_status)

    elif args['command'] == 'walk':
        walk(forced=args['forced'], silent=True)

    elif args['command'] == 'set_walk_interval':
        set_walk_interval(args['walk_interval'])

    elif args['command'] == 'add_torrent':
        add_torrent_from_url(args['url'], args['download_to'])

    elif args['command'] == 'remove_torrent':
        remove_torrent(args['hash'], args['delete_data'])

    elif args['command'] == 'register_torrent':
        register_torrent(args['hash'])

    elif args['command'] == 'unregister_torrent':
        unregister_torrent(args['hash'])

    elif args['command'] == 'configure_rpc':
        configure_rpc(args['rpc_alias'], settings_dict_from_list(args['settings']))

    elif args['command'] == 'configure_tracker':
        configure_tracker(args['tracker_alias'], settings_dict_from_list(args['settings']))

    elif args['command'] == 'configure_notifier':
        configure_notifier(args['notifier_alias'], settings_dict_from_list(args['settings']))

    elif args['command'] == 'remove_notifier':
        remove_notifier(args['alias'])


if __name__ == '__main__':
    process_commands()
