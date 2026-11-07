import socket
from collections.abc import Callable, Generator
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from torrt import utils
from torrt.base_rpc import TorrentStatus
from torrt.incomplete import IncompleteOps
from torrt.toolbox import bootstrap, register_torrent
from torrt.utils import GlobalParam, RPCObjectsRegistry, TorrentData, TorrtConfig


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

@pytest.fixture
def pending_environment() -> Callable[..., SimpleNamespace]:

    def prepare_pending(
        *, client_count: int = 1, replacing: bool = True, exclusions: bool = False,
        remove_outdated: bool = True, queue: bool = True,
    ) -> SimpleNamespace:
        old_hash = "a" * 40 if replacing else ""
        torrent = TorrentData(
            magnet=f"magnet:?xt=urn:btih:{'b' * 40}&dn=New+release",
            url="https://review.invalid/topic/1",
        )

        if replacing:
            register_torrent(old_hash, url=torrent.url)

        clients = {}
        options = {}

        def make_client(alias: str) -> SimpleNamespace:
            states = {old_hash: {"hash": old_hash, "metadata_ready": True}} if old_hash else {}

            def get_torrent_status(hash_str: str) -> TorrentStatus | None:

                if (status := states.get(hash_str)) is None:
                    return None

                return TorrentStatus(**status)

            def add_torrent(added: TorrentData, **kwargs: Any) -> None:
                states[added.hash] = {"hash": added.hash, "metadata_ready": False}

            def remove_torrent(hash_str: str, **kwargs: Any) -> None:
                states.pop(hash_str, None)

            return SimpleNamespace(
                alias=alias, enabled=True, states=states,
                method_get_torrent_status=Mock(side_effect=get_torrent_status),
                method_add_torrent=Mock(side_effect=add_torrent),
                method_remove_torrent=Mock(side_effect=remove_torrent),
                method_apply_file_exclusions=Mock(), method_get_torrents=Mock(return_value=[]),
            )

        for idx in range(client_count):
            alias = f"client_{idx}"
            client = make_client(alias)
            clients[alias] = client
            RPCObjectsRegistry.add(client)
            options[alias] = {
                "download_to": f"/downloads/{alias}",
                "params": {"files": {"Release/skip.txt": {"exclude": True}}} if exclusions else None,
            }

        pending = IncompleteOps(TorrtConfig)
        key = old_hash or f"add:{torrent.hash}"

        if queue:
            pending.queue(torrent, options, old_hash=old_hash, remove_outdated=remove_outdated)

        return SimpleNamespace(
            pending=pending, key=key, torrent=torrent, old_hash=old_hash,
            clients=clients, client=clients["client_0"], options=options,
        )

    return prepare_pending
