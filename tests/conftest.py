import socket
from collections.abc import Generator
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from torrt import utils
from torrt.toolbox import bootstrap
from torrt.utils import GlobalParam, TorrtConfig


@pytest.fixture(autouse=True)
def no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:

    if request.node.get_closest_marker("live_trackers"):
        return

    def reject_connection(*args: Any, **kwargs: Any) -> None:
        raise OSError("Network access is disabled in unit tests")

    monkeypatch.setattr(socket, "getaddrinfo", reject_connection)
    monkeypatch.setattr(socket.socket, "connect", reject_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_connection)

@pytest.fixture(autouse=True)
def tmp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_network: None) -> Generator[None, None, None]:
    monkeypatch.setattr(TorrtConfig, "USER_DATA_PATH", tmp_path)
    monkeypatch.setattr(TorrtConfig, "USER_SETTINGS_FILE", tmp_path / "torrt_conf.json")
    monkeypatch.setattr(TorrtConfig, "_basic_settings", deepcopy(TorrtConfig._basic_settings))

    for registry in (
        utils.RPCObjectsRegistry, utils.TrackerObjectsRegistry, utils.NotifierObjectsRegistry, utils.BotObjectsRegistry,
    ):
        monkeypatch.setattr(registry, "_items", {})

    previous_dump = GlobalParam.get("dump_into")
    GlobalParam.set("dump_into", None)

    try:
        bootstrap()
        yield

    finally:
        GlobalParam.set("dump_into", previous_dump)

@pytest.fixture
def mock_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Keep independent in-memory settings for a single test."""
    settings = deepcopy(TorrtConfig._basic_settings)

    class MockConfig(TorrtConfig):

        @classmethod
        def save(cls, settings_dict: dict) -> None:
            saved_settings = deepcopy(settings_dict)
            settings.clear()
            settings.update(saved_settings)

        @classmethod
        def load(cls) -> dict[str, Any]:
            return deepcopy(settings)

    monkeypatch.setattr("torrt.toolbox.config", MockConfig)
    monkeypatch.setattr("torrt.utils.config", MockConfig)
    monkeypatch.setattr("torrt.utils.TorrtConfig", MockConfig)

    return settings

@pytest.fixture
def mock_telegram_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the optional Telegram transport without contacting Telegram."""

    for target in (
        "telegram", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "InlineKeyboardMarkup", "InlineKeyboardButton",
        "Update", "Filters", "Updater", "ConversationHandler", "CommandHandler", "MessageHandler", "CallbackContext",
        "CallbackQueryHandler",
    ):
        monkeypatch.setattr(f"torrt.bots.telegram_bot.{target}", MagicMock(), raising=False)
