import socket
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPAuthenticationError
from typing import Union

from ..base_notifier import BaseNotifier


class EmailNotifier(BaseNotifier):

    alias: str = 'email'

    def __init__(
            self,
            email: str,
            host: str = 'localhost',
            port: Union[str, int] = 25,
            user: str = None,
            password: str = None,
            use_tls: Union[str, bool] = False,
            sender: str = None
    ):

        self.email = email
        self.sender = sender

        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.use_tls = str(use_tls) == 'True'

        self.connection = self.get_connection()

        super().__init__()

    def get_connection(self):

        try:
            connection = SMTP(self.host, self.port)
            connection.ehlo()

        except socket.error as e:
            self.log_error(f'Could not connect to SMTP server: {e}')
            return

        if self.use_tls:

            try:
                connection.starttls()
                connection.ehlo()

            except Exception as e:

                self.log_error(f'{e}')
                return

        if self.user and self.password:

            try:
                connection.login(self.user, self.password)

            except SMTPAuthenticationError as e:
                self.log_error(f'{e}')
                return

        return connection

    def send_message(self, msg: str):
        self.connection.sendmail(self.sender, [self.email], msg)

    def test_configuration(self) -> bool:
        return bool(self.connection)

    def make_message(self, torrent_data: dict) -> str:

        text = (
            'The following torrents were updated:\n'
            '%s\n\n'
            'Best regards,\n'
            'torrt.' %
            '\n'.join(map(lambda torrent: torrent['name'], torrent_data.values()))
        )

        msg = MIMEText(text)

        msg['Subject'] = 'New torrents were added to download queue.'
        msg['From'] = self.sender
        msg['To'] = self.email

        self.log_info(f'Notification message was sent to user {self.email}')

        return msg.as_string()
