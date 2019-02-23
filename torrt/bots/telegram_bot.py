import logging

from torrt.base_bot import BaseBot
from torrt.toolbox import add_torrent_from_url, config
from torrt.utils import BotClassesRegistry, get_torrent_from_url, RPCObjectsRegistry

try:
    import telegram
    from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import Filters, Updater, ConversationHandler, CommandHandler, MessageHandler, RegexHandler

except ImportError:
    telegram = None

LOGGER = logging.getLogger(__name__)


class TelegramBot(BaseBot):
    START, ASKING_URL, URL, PATH = 1, 2, 3, 4

    alias = 'telegram'
    url = 'https://api.telegram.org/bot'

    def __init__(self, token, allowed_users=None):
        """
        :param token: str - Telegram's bot token
        :param allowed_users: str - comma-joined list of users allowed to add new torrents.
        """
        if not telegram:
            LOGGER.error('You have not installed python-telegram-bot library.')
            return

        self.token = token
        allowed_users = allowed_users or ''
        self.handler_kwargs = {}
        self.updater = Updater(token=self.token)
        self.dispatcher = self.updater.dispatcher
        if allowed_users:
            self.handler_kwargs = {'filters': Filters.user(username=allowed_users.split(','))}

    def test_configuration(self):
        return telegram and bool(self.updater)

    def run(self):
        if self.test_configuration():
            self.add_handlers()
            self.updater.start_polling()
            self.updater.idle()

    def add_handlers(self):

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.command_start, **self.handler_kwargs)],

            states={
                self.ASKING_URL: [MessageHandler(Filters.text, self.handle_ask_url)],
                self.URL: [RegexHandler('http[s]?://', self.handle_process_url, pass_user_data=True)],
                self.PATH: [RegexHandler(r'^/.+|\.', self.handle_ask_download_path, pass_user_data=True)],
            },

            fallbacks=[CommandHandler('cancel', self.cancel_handler)]
        )

        self.dispatcher.add_handler(conv_handler)
        self.dispatcher.add_handler(CommandHandler('add', self.command_add_torrent, **self.handler_kwargs))

    def handle_ask_url(self, bot, update):
        update.message.reply_text(text="Give me an URL and I'll do the rest.")
        return self.URL

    def handle_process_url(self, bot, update, user_data):
        torrent_url = update.message.text
        torrent_data = get_torrent_from_url(torrent_url)
        if torrent_data is None:
            update.message.reply_text('Unable to add torrent from `%s`' % torrent_url)
            return ConversationHandler.END
        else:
            user_data['url'] = torrent_url
            download_dirs = set()
            for rpc_alias, rpc in RPCObjectsRegistry.get().items():
                if rpc.enabled:
                    torrents = rpc.method_get_torrents()
                    for torrent in torrents:
                        download_dirs.add(torrent['download_to'])
            choices = [download_dirs]
            update.message.reply_text('Where to download data? Send absolute path or "."',
                                      reply_markup=ReplyKeyboardMarkup(choices, one_time_keyboard=True))
            return self.PATH

    def handle_ask_download_path(self, bot, update, user_data):
        try:
            torrent_url = user_data['url']
            if not torrent_url:
                update.message.reply_text('Something wrong. Try again')
        except KeyError:
            update.message.reply_text('Something wrong. Try again')
        else:
            path = update.message.text
            if path == '.':
                path = None

            torrents_count = len(config.load()['torrents'])
            add_torrent_from_url(torrent_url, download_to=path)
            if len(config.load()['torrents']) > torrents_count:
                update.message.reply_text('Torrent from `%s` was added' % torrent_url)
            else:
                update.message.reply_text('Torrent was not added.')
        return ConversationHandler.END

    def cancel_handler(self, bot, update):
        update.message.reply_text('Bye! I hope to see tou again.',
                                  reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def command_start(self, bot, update):
        """Start dialog handler"""
        keyboard = [["Add new torrent"]]

        update.message.reply_text('Do you want to add new torrents?',
                                  reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

        return self.ASKING_URL

    def command_add_torrent(self, bot, update):
        """Stand-alone handler to add torrent"""
        torrent_url = update.message.text.lstrip('/add ')
        if not torrent_url:
            update.message.reply_text('Please provide link to the tracker page. '
                                      'For example: \n/add https://rutracker.org/forum/viewtopic.php?t=1')
            return
        torrents_count = len(config.load()['torrents'])
        add_torrent_from_url(torrent_url)
        if len(config.load()['torrents']) > torrents_count:
            bot.send_message(chat_id=update.message.chat_id, text='Torrent from `%s` was added' % torrent_url)
        else:
            bot.send_message(chat_id=update.message.chat_id, text='Torrent was not added.')


BotClassesRegistry.add(TelegramBot)
