from torrt.utils import WithSettings, BotObjectsRegistry


class BaseBot(WithSettings):
    alias = None
    config_entry_name = 'bots'

    def register(self):
        """Adds this object intoBotObjectsRegistry.

        :return:
        """
        BotObjectsRegistry.add(self)

    def test_configuration(self):
        """This should implement a configuration test, for example check given credentials.

        :return: bool
        """
        return False

    def run(self):
        """
        Run bot to receive incoming commands.

        :return:
        """
        pass
