from typing import Optional

from ..base_bot import BaseBot
from ..toolbox import add_torrent_from_url, get_registered_torrents, remove_torrent
from ..utils import get_torrent_from_url, RPCObjectsRegistry

try:
    import telegram
    from telegram import (
        ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, Bot, Update
    )
    from telegram.ext import (
        Filters, Updater, ConversationHandler, CommandHandler, MessageHandler, RegexHandler, CallbackQueryHandler
    )

except ImportError:
    telegram = None


class TelegramBot(BaseBot):

    START, URL, PATH = 1, 2, 3

    alias: str = 'telegram'
    url: str = 'https://api.telegram.org/bot'

    def __init__(self, token: str, allowed_users: str = None):
        """
        :param token: str Telegram's bot token
        :param allowed_users: comma-joined list of users allowed to add new torrents.

        """
        self.token = token
        self.allowed_users = allowed_users or ''

        if not telegram:
            self.log_error('You have not installed python-telegram-bot library.')
            return

        self.handler_kwargs = {}
        self.updater = Updater(token=self.token)
        self.dispatcher = self.updater.dispatcher

        if self.allowed_users:
            self.handler_kwargs = {'filters': Filters.user(username=self.allowed_users.split(','))}

        super().__init__()

    def test_configuration(self) -> bool:
        return telegram and bool(self.updater)

    def run(self):
        if self.test_configuration():
            self.add_handlers()
            self.updater.start_polling()
            self.updater.idle()

    def add_handlers(self):
        path_handler_regex = r'^/(?!(cancel|start|add|list|remove|help)(?!/)).+|\.'

        kwargs = self.handler_kwargs

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.command_start, **kwargs)],

            states={
                self.URL: [RegexHandler('http[s]?://', self.handle_process_url, pass_user_data=True)],
                self.PATH: [RegexHandler(path_handler_regex, self.handle_ask_download_path, pass_user_data=True)],
            },

            fallbacks=[CommandHandler('cancel', self.cancel_handler)],
            allow_reentry=True
        )

        add_handler = self.dispatcher.add_handler

        add_handler(conv_handler)
        add_handler(CallbackQueryHandler(self.handle_callbacks))
        add_handler(CommandHandler('add', self.command_add_torrent, **kwargs))
        add_handler(CommandHandler('list', self.command_list_torrents, **kwargs))
        add_handler(CommandHandler('remove', self.command_remove_torrents, **kwargs))
        add_handler(CommandHandler('help', self.command_help, **kwargs))

    def handle_callbacks(self, bot: 'Bot', update: 'Update'):
        """Handler to process all callbacks from buttons"""

        handlers = {
            'add_torrent': self.handle_ask_url,
            'list_torrents': self.command_list_torrents,
            'delete_torrent': self.command_remove_torrents
        }
        handler = handlers.get(update.callback_query.data)

        if handler:
            handler(bot, update.callback_query)

        elif update.callback_query.data.startswith('hash:'):
            self.handle_remove_torrents(bot, update)

    def handle_ask_url(self, bot: 'Bot', update: 'Update'):

        update.message.reply_text(
            text="Give me a URL and I'll do the rest.",
            reply_markup=ReplyKeyboardRemove()
        )
        return self.URL

    def handle_process_url(self, bot: 'Bot', update: 'Update', user_data: Optional[dict]):

        torrent_url = update.message.text
        torrent_data = get_torrent_from_url(torrent_url)

        if torrent_data is None:
            update.message.reply_text(
                f'Unable to add torrent from `{torrent_url}`',
                reply_markup=ReplyKeyboardRemove())

            return ConversationHandler.END

        else:

            user_data['url'] = torrent_url
            download_dirs = set()

            for rpc_alias, rpc in RPCObjectsRegistry.get().items():

                if not rpc.enabled:
                    continue

                torrents = rpc.method_get_torrents()

                for torrent in torrents:
                    download_dirs.add(torrent['download_to'])

            choices = [[directory] for directory in download_dirs]

            update.message.reply_text(
                'Where to download data? Send absolute path or "."',
                reply_markup=ReplyKeyboardMarkup(choices, one_time_keyboard=True))

            return self.PATH

    def handle_ask_download_path(self, bot: 'Bot', update: 'Update', user_data: Optional[dict]):

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

            torrents_count = len(get_registered_torrents())

            try:
                add_torrent_from_url(torrent_url, download_to=path)

            except Exception as e:

                self.log_error(f'Unable to add torrent: {e}')

                update.message.reply_text(
                    'Error was occurred during registering torrent.',
                    reply_markup=ReplyKeyboardRemove())

            if len(get_registered_torrents()) > torrents_count:

                update.message.reply_text(
                    f'Torrent from `{torrent_url}` was added',
                    reply_markup=ReplyKeyboardRemove())

            else:
                update.message.reply_text(
                    'Unable to add torrent.',
                    reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def cancel_handler(self, bot: 'Bot', update: 'Update'):

        update.message.reply_text(
            'Bye! I hope to see you again.',
            reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def handle_remove_torrents(self, bot: 'Bot', update: 'Update'):
        """
        Handler for torrent remove action.
        data is colon-joined string which is contains:
        1. keyword `hash` - command prefix
        2. torrent HASH from configured RPC
        3. 0|1 - optional attribute (with_data) responsible for data removal from RPC
        For example 'hash:1234567890' or 'hash:1234567890:0'
        """
        data = update.callback_query.data
        split_data = data.split(':')[1:]
        torrent_hash = split_data.pop(0)

        if not split_data:
            # with_data attribute was not set yet, ask user

            update.callback_query.message.reply_text(
                'Do you want to delete data?',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(text='Yes', callback_data=data + ':1'),
                    InlineKeyboardButton(text='No', callback_data=data + ':0'),
                ]])
            )

        else:

            torrent_data = get_registered_torrents().get(torrent_hash)

            if torrent_data:
                remove_torrent(torrent_hash, with_data=bool(int(split_data[0])))
                update.callback_query.message.reply_text(
                    f"Torrent `{torrent_data['name']}` was removed")

            else:
                update.callback_query.message.reply_text(
                    'Torrent not found. Try one more time with /remove')

        return

    def command_start(self, bot: 'Bot', update: 'Update'):
        """Start dialog handler"""

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(text='Add torrent', callback_data='add_torrent'),
            InlineKeyboardButton(text='List torrents', callback_data='list_torrents'),
            InlineKeyboardButton(text='Delete torrent', callback_data='delete_torrent'),
        ]])
        bot.send_message(update.message.chat_id, 'What do you want to do?', reply_markup=kb)

        return self.URL

    def command_add_torrent(self, bot: 'Bot', update: 'Update'):
        """Stand-alone handler to add torrent"""

        torrent_url = update.message.text.lstrip('/add ')

        if not torrent_url:

            update.message.reply_text(
                'Please provide link to the tracker page. '
                'For example: \n/add https://rutracker.org/forum/viewtopic.php?t=1')

            return

        torrents_count = len(get_registered_torrents())
        chat_id = update.message.chat_id

        try:
            add_torrent_from_url(torrent_url)

        except Exception as e:

            self.log_error(f'Unable to register the torrent: {e}')
            bot.send_message(chat_id, text='Unable to register the torrent due to an error.')

        if len(get_registered_torrents()) > torrents_count:
            bot.send_message(chat_id, text='The torrent is successfully registered.')

        else:
            bot.send_message(chat_id, text='Unable to register the torrent.')

    def command_list_torrents(self, bot: 'Bot', update: 'Update'):
        """Command to list all monitored torrents"""

        torrents = []

        for idx, torrent in enumerate(get_registered_torrents().values(), 1):
            if torrent.get('url'):
                torrents.append(f"{idx}. {torrent['name']}\n{torrent['url']}")

            else:
                torrents.append(f"{idx}. {torrent['name']}")

        if torrents:
            update.message.reply_text('\n\n'.join(torrents))

        else:
            update.message.reply_text('No torrents yet.')

    def command_remove_torrents(self, bot: 'Bot', update: 'Update'):
        """Command to remove torrent"""

        buttons = []

        for torrent in get_registered_torrents().values():
            buttons.append([
                InlineKeyboardButton(
                    text=torrent['name'],
                    callback_data=f"hash:{torrent['hash']}"
                )
            ])

        bot.send_message(
            update.message.chat_id,
            text='Which torrent do you want to remove?',
            reply_markup=InlineKeyboardMarkup(buttons))

    def command_help(self, bot: 'Bot', update: 'Update'):
        """Command for help"""

        helptext = (
            'Available commands:\n'
            '/start: Interactive wizard for torrent management.\n'
            '/add <URL>: Quick way to add a new torrent.\n'
            '/list: Display all registered torrents.\n'
            '/remove: Remove torrent.\n'
            '/cancel: Cancel current operation.'
        )

        update.message.reply_text(helptext)
