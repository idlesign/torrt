import logging
import requests
from requests import RequestException

from torrt.base_notifier import BaseNotifier
from torrt.utils import NotifierClassesRegistry

LOGGER = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Telegram bot notifier. See instructions how to create bot at https://core.telegram.org/bots/api"""
    alias = 'telegram'
    url = 'https://api.telegram.org/bot'

    def __init__(self, token, chat_id):
        """
        :param token: str - Telegram's bot token
        :param chat_id: str - Telegram's chat ID
        """

        self.token = token
        self.chat_id = chat_id

    def make_message(self, torrent_data):
        return '''The following torrents were updated:\n%s''' \
               % '\n'.join(map(lambda t: t['name'], torrent_data.values()))

    def test_configuration(self):
        url = '%s%s/getMe' % (self.url, self.token)
        r = requests.get(url)
        return r.json().get('ok', False)

    def send_message(self, msg):
        url = '%s%s/sendMessage' % (self.url, self.token)
        try:
            response = requests.post(url, data={'chat_id': self.chat_id, 'text': msg})
        except RequestException as e:
            LOGGER.error('Failed to send Telegram message: %s', e)
        else:
            if response.ok:
                json_data = response.json()
                if json_data['ok']:
                    LOGGER.debug('Telegram message was sent to user %s', self.chat_id)
                else:
                    LOGGER.error('Telegram notification not send: %s', json_data['description'])
            else:
                LOGGER.error('Telegram notification not send. Response code: %s (%s)',
                             response.status_code, response.reason)


NotifierClassesRegistry.add(TelegramNotifier)
