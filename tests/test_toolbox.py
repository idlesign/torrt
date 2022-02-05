import pytest

from unittest.mock import MagicMock

from torrt.toolbox import *
from torrt.utils import BotObjectsRegistry


@pytest.fixture(scope='function', autouse=True)
def clear_bot_registry():
    '''HACK: clears all registered bots before each test.

    otherwise test order matters
    '''

    BotObjectsRegistry._items.clear()


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
    # mainly mocking everything bot-library-related
    for target in (
        'telegram',
        'ReplyKeyboardMarkup', 'ReplyKeyboardRemove', 'InlineKeyboardMarkup', 'InlineKeyboardButton', 'Bot', 'Update', 'Updater',
        'Filters', 'Updater', 'ConversationHandler', 'CommandHandler', 'MessageHandler', 'RegexHandler', 'CallbackQueryHandler'
    ):
        monkeypatch.setattr(f'torrt.bots.telegram_bot.{target}', MagicMock(), raising=False)

    monkeypatch.setattr('torrt.bots.telegram_bot.TelegramBot.test_configuration', lambda *args: True)

    bot = configure_bot('telegram', {'token': 'xxx'})
    bot.register()

    assert mock_config['bots']['telegram']

    run_bots(['telegram'])

    remove_bot('telegram')
    assert not mock_config['bots']


def test_no_bots_to_run_exists():
    with pytest.raises(SystemExit) as excinfo:
        run_bots(['stub'])

    assert excinfo.value.code == 1


def test_telegram_without_plugin_raises_exception(monkeypatch):
    monkeypatch.setattr(f'torrt.bots.telegram_bot.telegram', None)

    with pytest.raises(BotRegistrationFailed) as excinfo:
        configure_bot('telegram', {'token': 'xxx'})

    assert 'python-telegram-bot' in str(excinfo.value)


def test_notifiers(mock_config, monkeypatch):

    monkeypatch.setattr('torrt.notifiers.telegram.TelegramNotifier.test_configuration', lambda *args: True)

    configure_notifier('telegram', {'token': 'xxx', 'chat_id': 'xxx'})
    assert mock_config['notifiers']['telegram']

    remove_notifier('telegram')
    assert not mock_config['notifiers']
