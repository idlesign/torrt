import json
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call

import pytest

from torrt import toolbox
from torrt.toolbox import (
    BotRegistrationFailed,
    configure_bot,
    configure_logging,
    configure_notifier,
    init_object_registries,
    register_torrent,
    remove_bot,
    remove_notifier,
    run_bots,
    set_walk_interval,
    unregister_torrent,
    walk,
)
from torrt.utils import NotifierObjectsRegistry, RPCObjectsRegistry, TorrentData, TorrtConfig, TrackerObjectsRegistry


def test_register_unregister_torrent(mock_config):

    hashstr = '1234567890'

    register_torrent(hashstr, url='https://exmaple.com/here/')
    assert hashstr in mock_config['torrents']

    unregister_torrent(hashstr)
    assert not mock_config['torrents']


def test_set_walk_interval(mock_config):
    set_walk_interval(16)
    assert mock_config['walk_interval_hours'] == 16


def test_configure_logging():
    configure_logging(show_logger_names=True)


def test_bots(mock_config, monkeypatch, mock_telegram_plugin):
    monkeypatch.setattr('torrt.bots.telegram_bot.TelegramBot.test_configuration', lambda *args: True)

    bot = configure_bot('telegram', {'token': 'xxx'})
    bot.register()

    assert mock_config['bots']['telegram']

    run_bots(['telegram'])

    remove_bot('telegram')
    assert not mock_config['bots']


def test_no_bots_to_run_exists():
    with pytest.raises(SystemExit) as excinfo:
        run_bots(['stub'])

    assert excinfo.value.code == 1


def test_telegram_without_plugin_raises_exception(monkeypatch):
    monkeypatch.setattr('torrt.bots.telegram_bot.telegram', None)

    with pytest.raises(BotRegistrationFailed) as excinfo:
        configure_bot('telegram', {'token': 'xxx'})

    assert 'python-telegram-bot' in str(excinfo.value)


def test_bot_configured_but_unregistered(monkeypatch, mock_telegram_plugin):
    # configuring 'mocked' bot just to get its configuration
    monkeypatch.setattr('torrt.bots.telegram_bot.TelegramBot.test_configuration', lambda *args: True)
    configure_bot('telegram', {'token': 'xxx'})

    # making bot unspawnable, by forcebly removing required plugin mock
    monkeypatch.setattr('torrt.bots.telegram_bot.telegram', None)

    # check that user gets warning about configured, but unregistered bot
    mocked_logger = MagicMock()
    with monkeypatch.context() as m:
        m.setattr('torrt.toolbox.LOGGER', mocked_logger)
        init_object_registries()

    mocked_logger.warning.assert_called_once()
    assert 'bot is configured, but failed to register' in mocked_logger.warning.call_args[0][0]


def test_notifiers(mock_config, monkeypatch):

    monkeypatch.setattr('torrt.notifiers.telegram.TelegramNotifier.test_configuration', lambda *args: True)

    configure_notifier('telegram', {'token': 'xxx', 'chat_id': 'xxx'})
    assert mock_config['notifiers']['telegram']

    remove_notifier('telegram')
    assert not mock_config['notifiers']

@pytest.fixture
def walk_environment(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], SimpleNamespace]:
    now = 1_700_000_000
    monkeypatch.setattr(toolbox, "time", Mock(return_value=now))

    def prepare_walk(torrent_count: int) -> SimpleNamespace:
        TorrtConfig.update({"walk_interval_hours": 6, "custom": {"keep": ["unchanged"]}})
        rpc_torrents = []
        replacements = []

        for idx in range(torrent_count):
            url = f"https://review.invalid/{idx}"
            register_torrent(f"old_{idx}", url=url)
            rpc_torrents.append({
                "hash": f"old_{idx}", "name": f"Old {idx}", "comment": "", "download_to": "/review downloads",
            })
            replacements.append(TorrentData(hash=f"new_{idx}", name=f"New {idx}", raw=b"review torrent"))

        rpc = SimpleNamespace(
            alias="review", enabled=True, method_get_torrents=Mock(return_value=rpc_torrents),
            method_add_torrent=Mock(), method_remove_torrent=Mock(),
        )
        tracker = SimpleNamespace(alias="review.invalid", get_torrent=Mock(side_effect=replacements))
        first_notifier = SimpleNamespace(alias="first", send=Mock())
        second_notifier = SimpleNamespace(alias="second", send=Mock())
        RPCObjectsRegistry.add(rpc)
        TrackerObjectsRegistry.add(tracker)
        NotifierObjectsRegistry.add(first_notifier)
        NotifierObjectsRegistry.add(second_notifier)
        return SimpleNamespace(
            rpc=rpc, replacements=replacements, first=first_notifier, second=second_notifier,
            initial=TorrtConfig.load(), now=now,
        )

    return prepare_walk

@pytest.mark.parametrize("torrent_count", [1, 2])
@pytest.mark.parametrize("notifier_fails", [False, True])
def test_walk_saves_before_notifications(
    walk_environment: Callable[[int], SimpleNamespace], torrent_count: int, notifier_fails: bool,
) -> None:
    environment = walk_environment(torrent_count)
    saved_when_notified = []

    def send_notification(updated_data: dict[str, dict]) -> None:
        saved_when_notified.append(json.loads(TorrtConfig.USER_SETTINGS_FILE.read_text(encoding="utf-8")))

        if notifier_fails:
            raise RuntimeError("Review notification failed")

    environment.first.send.side_effect = send_notification

    if notifier_fails:

        with pytest.raises(RuntimeError, match="Review notification failed"):
            walk(forced=True)

    else:
        walk(forced=True)

    saved = json.loads(TorrtConfig.USER_SETTINGS_FILE.read_text(encoding="utf-8"))
    assert set(saved["torrents"]) == {f"new_{idx}" for idx in range(torrent_count)}
    assert saved["time_last_check"] == environment.now
    assert saved_when_notified == [saved]
    assert {key: value for key, value in saved.items() if key not in ("torrents", "time_last_check")} == {
        key: value for key, value in environment.initial.items() if key not in ("torrents", "time_last_check")
    }
    updated = {f"old_{idx}": torrent.to_dict() for idx, torrent in enumerate(environment.replacements)}
    environment.first.send.assert_called_once_with(updated)

    if notifier_fails:
        environment.second.send.assert_not_called()

    else:
        environment.second.send.assert_called_once_with(updated)

    assert environment.rpc.method_add_torrent.call_count == torrent_count
    assert environment.rpc.method_remove_torrent.call_args_list == [call(f"old_{idx}") for idx in range(torrent_count)]

def test_walk_does_not_notify_when_save_fails(
    walk_environment: Callable[[int], SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = walk_environment(2)
    save_settings = TorrtConfig.save
    failed_saves = []

    def save_or_fail(config_class: type[TorrtConfig], settings: dict) -> None:

        if "new_0" in settings["torrents"]:
            failed_saves.append(settings)
            raise OSError("Review storage failure")

        save_settings(settings)

    monkeypatch.setattr(TorrtConfig, "save", classmethod(save_or_fail))

    with pytest.raises(OSError, match="Review storage failure"):
        walk(forced=True)

    assert len(failed_saves) == 1
    assert set(failed_saves[0]["torrents"]) == {"old_0", "old_1", "new_0"}
    environment.first.send.assert_not_called()
    environment.second.send.assert_not_called()
    environment.rpc.method_add_torrent.assert_called_once()
    environment.rpc.method_remove_torrent.assert_not_called()
    assert TorrtConfig.load()["torrents"] == environment.initial["torrents"]
