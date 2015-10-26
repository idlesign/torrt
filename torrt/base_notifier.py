import logging

from torrt.utils import WithSettings, NotifierObjectsRegistry

LOGGER = logging.getLogger(__name__)


class BaseNotifier(WithSettings):
    """Base Notifier class. All Notifier classes should inherit from this."""

    alias = None
    config_entry_name = 'notifiers'

    def register(self):
        """Adds this object into NotificationObjectsRegistry.

        :return:
        """
        NotifierObjectsRegistry.add(self)

    def send_message(self, msg):
        """Send prepared message

        :param msg: str - Prepared by notifier backend message

        :return:
        """
        raise NotImplementedError('`%s` class must implement `send_message()` method.' % self.__class__.__name__)

    def make_message(self, torrent_data):
        """Creates message in format suitable for notifier backend

        :param: torrent_data: dict - dictionary with updated torrents data during the walk operation

        :return:
        """
        raise NotImplementedError('`%s` class must implement `make_message()` method.' % self.__class__.__name__)

    def test_configuration(self):
        """This should implement a configuration test, for example check given credentials.

        :return: bool
        """
        return False

    def send(self, updated_data):
        """Send message to user

        :param: updated_data: dict - dictionary with updated torrents data during the walk operation

        :return:
        """

        msg = self.make_message(updated_data)
        self.send_message(msg)
