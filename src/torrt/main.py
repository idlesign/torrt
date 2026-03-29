import argparse
import logging
import sys
from pathlib import Path

from torrt import VERSION
from torrt.toolbox import (
    add_torrent_from_url,
    bootstrap,
    configure_bot,
    configure_logging,
    configure_notifier,
    configure_rpc,
    configure_tracker,
    get_registered_torrents,
    register_torrent,
    remove_notifier,
    remove_torrent,
    run_bots,
    set_walk_interval,
    toggle_rpc,
    unregister_torrent,
    walk,
)
from torrt.utils import (
    LOGGER,
    GlobalParam,
    NotifierClassesRegistry,
    NotifierObjectsRegistry,
    RPCClassesRegistry,
    RPCObjectsRegistry,
    TrackerClassesRegistry,
)


def process_commands(arguments: list[str] | None = None) -> None:

    arguments = arguments or sys.argv[1:]

    def settings_dict_from_list(value: list[str] | str):
        settings_dict = {}

        if isinstance(value, str):
            value = value.split(' ')

        for setting in value:
            try:
                key, val = setting.split('=')

            except ValueError:
                # no = delimiter founds
                continue

            settings_dict[key] = val

        return settings_dict

    arg_parser = argparse.ArgumentParser('torrt', description='Automates torrent updates for you.')
    arg_parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

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

    parser_configure_bot = subp_main.add_parser(
        'configure_bot', help='Sets Bot settings (token, etc.)',
        description='E.g.: configure_bot telegram token=YourBotSuperToken')
    parser_configure_bot.add_argument(
        'bot_alias', help='Bot alias to apply settings to')
    parser_configure_bot.add_argument(
        'settings',
        help='Settings string, format: setting1=val1 setting2=val2. '
             'Supported settings for telegram bot: token.',
        nargs='*')

    parser_walk = subp_main.add_parser(
        'walk', help='Walks through registered torrents and performs automatic updates')
    parser_walk.add_argument(
        '-f', help='Forces walk. Forced walks do not respect walk interval settings', dest='forced',
        action='store_true')
    parser_walk.add_argument(
        '--dump', help='Dump web pages scraped by torrt into current or a given directory', dest='dump')

    parser_run_bots = subp_main.add_parser(
        'run_bots', help='Run registered bots')
    parser_run_bots.add_argument(
        'aliases', help='Bots to run aliases',
        nargs='*')

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
    parser_add_torrent.add_argument(
        '--params',
        help="Parameters to pass to torrent client. E.g. -p='param1=val1 param2=val2'",
        dest='params', default='')
    parser_add_torrent.add_argument(
        '--dump', help='Dump web pages scraped by torrt into current or a given directory', dest='dump')

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
    parser_register_torrent.add_argument(
        '-u', dest='url', default=None, help='URL to download torrent from')
    parser_register_torrent.add_argument(
        '--params',
        help="Parameters to pass to a torrent client. E.g. -p='param1=val1 param2=val2'",
        dest='params', default='')

    parser_unregister_torrent = subp_main.add_parser(
        'unregister_torrent', help='Unregisters torrent from torrt by its hash')
    parser_unregister_torrent.add_argument(
        'hash', help='Torrent identifying hash')

    parser_remove_notifier = subp_main.add_parser(
        'remove_notifier', help='Remove configured notifier by its alias')
    parser_remove_notifier.add_argument('alias', help='Alias of notifier to remove')

    for parser in subp_main.choices.values():
        parser.add_argument('--verbose', help='Switch to show debug messages', dest='verbose', action='store_true')

    args = arg_parser.parse_args(arguments)
    args = vars(args)

    configure_logging(logging.DEBUG if args.get('verbose') else logging.INFO)

    bootstrap()

    dump_into = args.get('dump')

    if dump_into:
        GlobalParam.set('dump_into', Path(dump_into).resolve())

    if args['command'] == 'enable_rpc':
        toggle_rpc(args['alias'], enabled=True)

    elif args['command'] == 'disable_rpc':
        toggle_rpc(args['alias'], enabled=False)

    elif args['command'] == 'list_trackers':

        for tracker_alias in TrackerClassesRegistry.get().keys():
            LOGGER.info(tracker_alias)

    elif args['command'] == 'list_rpc':
        rpc_statuses = {}

        for rpc_alias in RPCClassesRegistry.get().keys():
            rpc_statuses[rpc_alias] = 'unconfigured'

        for rpc_alias, rpc in RPCObjectsRegistry.get().items():
            rpc_statuses[rpc_alias] = 'enabled' if rpc.enabled else 'disabled'

        for rpc_alias, rpc_status in rpc_statuses.items():
            LOGGER.info(f'{rpc_alias}\t status={rpc_status}')

    elif args['command'] == 'list_torrents':
        for torrent_hash, torrent_data in get_registered_torrents().items():
            LOGGER.info(f"{torrent_hash}\t{torrent_data['name']}")

    elif args['command'] == 'list_notifiers':
        notifiers = {}
        for notifier_alias in NotifierClassesRegistry.get().keys():
            notifiers[notifier_alias] = 'unconfigured'

        for notifier_alias in NotifierObjectsRegistry.get().keys():
            notifiers[notifier_alias] = 'enabled'

        for notifier_alias, notifier_status in notifiers.items():
            LOGGER.info(f"{notifier_alias}\t status={notifier_status}")

    elif args['command'] == 'walk':
        walk(forced=args['forced'], silent=True)

    elif args['command'] == 'set_walk_interval':
        set_walk_interval(args['walk_interval'])

    elif args['command'] == 'add_torrent':
        add_torrent_from_url(
            args['url'],
            download_to=args['download_to'],
            params=settings_dict_from_list(args['params']),
        )

    elif args['command'] == 'remove_torrent':
        remove_torrent(args['hash'], with_data=args['delete_data'])

    elif args['command'] == 'register_torrent':
        register_torrent(
            args['hash'],
            url=args['url'],
            params=settings_dict_from_list(args['params']),
        )

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

    elif args['command'] == 'configure_bot':
        configure_bot(args['bot_alias'], settings_dict_from_list(args['settings']))

    elif args['command'] == 'run_bots':
        run_bots(args['aliases'])


if __name__ == '__main__':
    process_commands()
