from .utils import WithSettings, BotObjectsRegistry


class BaseBot(WithSettings):

    config_entry_name: str = 'bots'

    def register(self):
        """Adds this object intoBotObjectsRegistry."""

        BotObjectsRegistry.add(self)

    def test_configuration(self) -> bool:
        """This should implement a configuration test, for example check given credentials."""
        return False

    def run(self):
        """Run bot to receive incoming commands."""
