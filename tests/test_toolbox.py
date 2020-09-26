from unittest.mock import MagicMock

from torrt.toolbox import *


def test_register_unregister_torrent(mock_config):

    hashstr = '1234567890'

    register_torrent(hashstr, url='https://exmaple.com/here/')
    assert hashstr in mock_config['torrents']

    unregister_torrent(hashstr)
    assert not mock_config['torrents']


def test_set_walk_interval(mock_config):
    set_walk_interval(16)
    assert mock_config['walk_interval_hours'] == 16


def test_configure_logging():
    configure_logging(show_logger_names=True)


def test_bots(mock_config, monkeypatch):

    monkeypatch.setattr('torrt.bots.telegram_bot.Updater', MagicMock(), raising=False)
    monkeypatch.setattr('torrt.bots.telegram_bot.TelegramBot.test_configuration', lambda *args: True)

    configure_bot('telegram', {'token': 'xxx'})
    assert mock_config['bots']['telegram']

    run_bots(['telegram'])

    remove_bot('telegram')
    assert not mock_config['bots']


def test_notifiers(mock_config, monkeypatch):

    monkeypatch.setattr('torrt.notifiers.telegram.TelegramNotifier.test_configuration', lambda *args: True)

    configure_notifier('telegram', {'token': 'xxx', 'chat_id': 'xxx'})
    assert mock_config['notifiers']['telegram']

    remove_notifier('telegram')
    assert not mock_config['notifiers']
