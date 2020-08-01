from .utils import WithSettings, BotObjectsRegistry, BotClassesRegistry


class BaseBot(WithSettings):

    config_entry_name: str = 'bots'

    def __init_subclass__(cls, **kwargs):
        if cls.alias:
            BotClassesRegistry.add(cls)

    def register(self):
        """Adds this object intoBotObjectsRegistry."""

        BotObjectsRegistry.add(self)

    def test_configuration(self) -> bool:
        """This should implement a configuration test, for example check given credentials."""
        return False

    def run(self):
        """Run bot to receive incoming commands."""
