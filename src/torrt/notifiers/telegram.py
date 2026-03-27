from ..base_notifier import BaseNotifier
from ..utils import HttpClient


class TelegramNotifier(BaseNotifier):
    """Telegram bot notifier. See instructions how to create bot at https://core.telegram.org/bots/api"""

    alias: str = 'telegram'
    url: str = 'https://api.telegram.org/bot'

    def __init__(self, token: str, chat_id: str):
        """
        :param token: Telegram's bot token
        :param chat_id: Telegram's chat ID

        """
        self.token = token
        self.chat_id = chat_id
        self.client = HttpClient(
            silence_exceptions=True,
            dump_fname_tpl=f'%(ts)s_{self.__class__.__name__}.json',
            json=True,
        )
        super().__init__()

    def make_message(self, torrent_data: dict) -> str:
        return (
            'The following torrents were updated:\n%s' %
            '\n'.join(map(lambda t: t['name'], torrent_data.values())))

    def test_configuration(self) -> bool:
        response = self.client.request(f'{self.url}{self.token}/getMe')
        return response.get('ok', False)

    def send_message(self, msg: str):

        url = f'{self.url}{self.token}/sendMessage'

        client = self.client
        json_data = client.request(url, data={'chat_id': self.chat_id, 'text': msg})

        if json_data is None:
            self.log_error(f'Failed to send Telegram message: {client.last_error}')
            return

        response = client.last_response

        if response.ok:

            if json_data['ok']:
                self.log_debug(f'Telegram message was sent to user {self.chat_id}')

            else:
                self.log_error(f"Telegram notification not send: {json_data['description']}")

            return

        self.log_error(
            'Telegram notification not sent. '
            f'Response code: {response.status_code} ({response.reason})')
