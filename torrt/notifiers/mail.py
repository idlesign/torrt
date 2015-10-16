import logging
from email.mime.text import MIMEText
from smtplib import SMTP

from torrt.base_notifier import BaseNotifier
from torrt.utils import NotifierClassesRegistry

LOGGER = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):

    alias = 'email'

    def __init__(self, email, host='localhost', port=25, user=None, password=None, use_tls=False, sender=None):

        self.email = email
        self.sender = sender

        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.use_tls = str(use_tls) == 'True'

        self.connection = self.get_connection()

    def get_connection(self):
        connection = SMTP(self.host, self.port)
        connection.ehlo()
        if self.use_tls:
            connection.starttls()
            connection.ehlo()
        if self.user and self.password:
            connection.login(self.user, self.password)
        return connection

    def send_message(self, msg):
        self.connection.sendmail(self.sender, [self.email], msg)

    def test_configuration(self):
        return bool(self.connection)

    def make_message(self, torrent_data):

        msg = MIMEText('New torrent was added to download queue.')
        msg['Subject'] = 'New torrent'
        msg['From'] = self.sender
        msg['To'] = self.email

        return msg.as_string()


NotifierClassesRegistry.add(EmailNotifier)
