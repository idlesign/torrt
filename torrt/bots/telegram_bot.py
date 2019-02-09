import logging

from torrt.base_bot import BaseBot
from torrt.toolbox import add_torrent_from_url
from torrt.utils import TorrtConfig, BotClassesRegistry

LOGGER = logging.getLogger(__name__)


class TelegramBot(BaseBot):

    alias = 'telegram'
    url = 'https://api.telegram.org/bot'

    def __init__(self, token):
        """
        :param token: str - Telegram's bot token
        """

        self.token = token
        try:
            from telegram.ext import Updater
            self.updater = Updater(token=self.token)
            self.dispatcher = self.updater.dispatcher
        except ImportError:
            LOGGER.error('You have not installed python-telegram-bot library.')
            self.updater = None
            self.dispatcher = None

    def test_configuration(self):
        return bool(self.updater)

    def run(self):
        self.add_handlers()
        self.updater.start_polling()
        self.updater.idle()

    def add_handlers(self):
        from telegram.ext import CommandHandler
        start_handler = CommandHandler('start', start)
        add_handler = CommandHandler('add', add_torrent)
        self.dispatcher.add_handler(start_handler)
        self.dispatcher.add_handler(add_handler)


def add_torrent(bot, update):

    torrent_url = update.message.text.lstrip('/add ')
    torrents_count = len(TorrtConfig.load()['torrents'])
    add_torrent_from_url(torrent_url)
    if len(TorrtConfig.load()['torrents']) > torrents_count:
        bot.send_message(chat_id=update.message.chat_id, text='Torrent from `%s` was added' % torrent_url)
    else:
        bot.send_message(chat_id=update.message.chat_id, text='Torrent was not added.')


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


BotClassesRegistry.add(TelegramBot)
