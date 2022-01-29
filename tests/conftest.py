from importlib import import_module

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


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "skip_no_module(module, reason): mark test to run only with this module installed"
    )

@pytest.fixture(autouse=True)
def skip_without_module(request):
    """global fixture, that automatically skips tests marked with

    `@pytest.mark.skip_no_module(module: str, reason: Optional[str] = '')`

    if the requested `module` is unable to be imported

    """

    marker = request.node.get_closest_marker('skip_no_module')
    if marker:
        modulename = marker.args[0]
        reason = marker.args[1] if len(marker.args) > 1 else ''

        try:
            import_module(modulename)
        except ImportError:
            pytest.skip(f"skipped without module: {modulename} {reason}")
