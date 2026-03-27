from .utils import WithSettings, NotifierObjectsRegistry, NotifierClassesRegistry


class BaseNotifier(WithSettings):
    """Base Notifier class. All Notifier classes should inherit from this."""

    config_entry_name: str = 'notifiers'

    def __init_subclass__(cls, **kwargs):
        if cls.alias:
            NotifierClassesRegistry.add(cls)

    def register(self):
        """Adds this object into NotificationObjectsRegistry."""

        NotifierObjectsRegistry.add(self)

    def send_message(self, msg: str):  # pragma: nocover
        """Send prepared message

        :param msg: Prepared by notifier backend message

        """
        raise NotImplementedError

    def make_message(self, torrent_data: dict) -> str:  # pragma: nocover
        """Creates message in format suitable for notifier backend

        :param: torrent_data: dictionary with updated torrents data during the walk operation

        """
        raise NotImplementedError

    def test_configuration(self) -> bool:
        """This should implement a configuration test, for example check given credentials."""

        return False

    def send(self, updated_data):
        """Send message to user

        :param: updated_data: dict - dictionary with updated torrents data during the walk operation

        """
        msg = self.make_message(updated_data)
        self.send_message(msg)
