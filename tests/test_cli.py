import logging

import pytest

from torrt.main import process_commands


@pytest.mark.parametrize('command,expected', [
    (['list_rpc'], ['utorrent\t status=unconfigured']),
    (['list_trackers'], ['rutracker.org']),
    (['list_torrents'], ['Loading configuration']),
    (['list_notifiers'], ['email\t status=unconfigured']),
    (['configure_tracker', 'some', 'username=a', 'password=b'], ['Tracker `some` is unknown']),
    (['configure_rpc', 'other', 'host=a', 'password=b'], ['RPC `other` is unknown']),
    (['configure_notifier', 'else', 'token=a', 'chat_id=b'], ['Notifier `else` is unknown']),
    (['configure_bot', 'boooot', 'token=a'], ['Bot `boooot` is unknown']),
    (['walk', '-f', '--dump', '/tmp/'], ['Torrent walk is finished']),
    (['set_walk_interval', '1'], ['Saving configuration file']),
    (['enable_rpc', 'a'], ['RPC `a` class is not registered']),
    (['disable_rpc', 'a'], ['RPC `a` class is not registered']),
    (['add_torrent', 'https://google.com/dummy', '--params', 'a=b d=c'], ['Unable to add torrent from']),
    (['add_torrent', 'https://google.com/dummy', '-d "/downloads/"'], ['Unable to add torrent from']),
    (['remove_torrent', '123', '-d'], ['Unregistering `123` torrent']),
    (['register_torrent', '123', '--params', 'a=b d=c'], ['Registering `123` torrent']),
    (['unregister_torrent', '123'], ['Unregistering `123` torrent']),
    (['remove_notifier', 'else'], ['Removing `else` notifier']),
])
def test_smoke(caplog, command, expected):
    caplog.set_level(logging.DEBUG, logger='torrt')
    process_commands(command)

    messages = caplog.text
    for expected_chunk in expected:
        assert expected_chunk in messages, f'NOT FOUND {expected_chunk} in {messages}'
