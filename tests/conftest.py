import pytest

from torrt.toolbox import bootstrap


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    # Ensure fresh config for every test.
    monkeypatch.setattr('torrt.utils.TorrtConfig.USER_SETTINGS_FILE', tmp_path / 'torrt_conf.json')
    bootstrap()


@pytest.fixture
def mock_config(monkeypatch):
    """Allows an easy access to config."""

    from torrt.utils import TorrtConfig

    settings = {}

    class MockConfig(TorrtConfig):

        @classmethod
        def bootstrap(cls):
            cls.save(cls._basic_settings)

        @classmethod
        def save(cls, settings_dict: dict):
            settings.update(settings_dict)

        @classmethod
        def load(cls) -> dict:
            cls.bootstrap()
            return settings

    monkeypatch.setattr('torrt.toolbox.config', MockConfig)
    monkeypatch.setattr('torrt.utils.config', MockConfig)
    monkeypatch.setattr('torrt.utils.TorrtConfig', MockConfig)

    return settings
