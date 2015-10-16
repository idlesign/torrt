import logging

from torrt.utils import WithSettings, NotifierObjectsRegistry

LOGGER = logging.getLogger(__name__)


class BaseNotifier(WithSettings):

    alias = None
    config_entry_name = 'notifiers'

    def register(self):
        """Adds this object into NotificationObjectsRegistry.

        :return:
        """
        NotifierObjectsRegistry.add(self)

    def send_message(self, msg):
        pass

    def make_message(self, torrent_data):
        pass

    def test_configuration(self):
        return False