import logging

from torrt.base_bot import BaseBot
from torrt.toolbox import add_torrent_from_url
from torrt.utils import TorrtConfig, BotClassesRegistry, get_torrent_from_url, RPCObjectsRegistry

LOGGER = logging.getLogger(__name__)


START, ASKING_URL, URL, PATH = 1, 2, 3, 4


class TelegramBot(BaseBot):

    alias = 'telegram'
    url = 'https://api.telegram.org/bot'

    def __init__(self, token, allowed_users=None):
        """
        :param token: str - Telegram's bot token
        :param allowed_users: str - comma-joined list of users allowed to add new torrents.
        """

        self.token = token
        allowed_users = allowed_users or ''
        self.handler_kwargs = {}
        try:
            from telegram.ext import Updater, Filters
            self.updater = Updater(token=self.token)
            self.dispatcher = self.updater.dispatcher
            if allowed_users:
                self.handler_kwargs = {'filters': Filters.user(username=allowed_users.split(','))}

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
        from telegram.ext import CommandHandler, ConversationHandler, RegexHandler, Filters, MessageHandler

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start, **self.handler_kwargs)],

            states={
                ASKING_URL: [MessageHandler(Filters.text, asking_url_handler)],
                URL: [RegexHandler('http[s]?://', url_handler, pass_user_data=True)],
                PATH: [RegexHandler('/', path_handler, pass_user_data=True)],
            },

            fallbacks=[CommandHandler('cancel', cancel)]
        )

        self.dispatcher.add_handler(conv_handler)
        self.dispatcher.add_handler(CommandHandler('add', add_torrent, **self.handler_kwargs))


def asking_url_handler(bot, update):
    update.message.reply_text(text="Give me an URL and I'll do the rest.")
    return URL


def url_handler(bot, update, user_data):
    from telegram.ext import ConversationHandler
    from telegram import ReplyKeyboardMarkup
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
        return PATH


def path_handler(bot, update, user_data):
    from telegram.ext import ConversationHandler
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


def cancel(bot, update):
    from telegram.ext import ConversationHandler
    from telegram import ReplyKeyboardRemove

    update.message.reply_text('Bye! I hope to see tou again.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def start(bot, update):
    from telegram import ReplyKeyboardMarkup
    keyboard = [["Add new torrent"]]

    update.message.reply_text('Do you want to add new torrents?',
                              reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

    return ASKING_URL


def add_torrent(bot, update):
    """Stand-alone handler to add torrent"""
    torrent_url = update.message.text.lstrip('/add ')
    torrents_count = len(TorrtConfig.load()['torrents'])
    add_torrent_from_url(torrent_url)
    if len(TorrtConfig.load()['torrents']) > torrents_count:
        bot.send_message(chat_id=update.message.chat_id, text='Torrent from `%s` was added' % torrent_url)
    else:
        bot.send_message(chat_id=update.message.chat_id, text='Torrent was not added.')


BotClassesRegistry.add(TelegramBot)
