import logging

from torrt.base_bot import BaseBot
from torrt.toolbox import add_torrent_from_url
from torrt.utils import TorrtConfig, BotClassesRegistry, get_torrent_from_url, RPCObjectsRegistry

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
            entry_points=[CommandHandler('start', self.start, **self.handler_kwargs)],

            states={
                self.ASKING_URL: [MessageHandler(Filters.text, self.asking_url_handler)],
                self.URL: [RegexHandler('http[s]?://', self.url_handler, pass_user_data=True)],
                self.PATH: [RegexHandler('/', self.path_handler, pass_user_data=True)],
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        self.dispatcher.add_handler(conv_handler)
        self.dispatcher.add_handler(CommandHandler('add', self.add_torrent, **self.handler_kwargs))

    def asking_url_handler(self, bot, update):
        update.message.reply_text(text="Give me an URL and I'll do the rest.")
        return self.URL

    def url_handler(self, bot, update, user_data):
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
                    map(download_dirs.add, [t['download_to'] for t in torrents])
            choices = [download_dirs]
            if choices:
                update.message.reply_text('Where to store data?',
                                          reply_markup=ReplyKeyboardMarkup(choices, one_time_keyboard=True))
            return self.PATH

    def path_handler(self, bot, update, user_data):
        try:
            torrent_url = user_data['url']
            if not torrent_url:
                update.message.reply_text('Something wrong. Try again')
        except KeyError:
            update.message.reply_text('Something wrong. Try again')
        else:
            torrents_count = len(TorrtConfig.load()['torrents'])
            add_torrent_from_url(torrent_url, download_to=update.message.text)
            if len(TorrtConfig.load()['torrents']) > torrents_count:
                update.message.reply_text('Torrent from `%s` was added' % torrent_url)
            else:
                update.message.reply_text('Torrent was not added.')
        return ConversationHandler.END

    def cancel(self, bot, update):
        update.message.reply_text('Bye! I hope to see tou again.',
                                  reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def start(self, bot, update):
        keyboard = [["Add new torrent"]]

        update.message.reply_text('Do you want to add new torrents?',
                                  reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

        return self.ASKING_URL

    def add_torrent(self, bot, update):
        """Stand-alone handler to add torrent"""
        torrent_url = update.message.text.lstrip('/add ')
        torrents_count = len(TorrtConfig.load()['torrents'])
        add_torrent_from_url(torrent_url)
        if len(TorrtConfig.load()['torrents']) > torrents_count:
            bot.send_message(chat_id=update.message.chat_id, text='Torrent from `%s` was added' % torrent_url)
        else:
            bot.send_message(chat_id=update.message.chat_id, text='Torrent was not added.')


BotClassesRegistry.add(TelegramBot)
