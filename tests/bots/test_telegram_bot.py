from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from torrt.bots import telegram_bot
from torrt.bots.telegram_bot import TelegramBot


@pytest.fixture
def bot(mock_telegram_plugin: None) -> TelegramBot:
    return TelegramBot(token="review_token", allowed_users="owner")

@pytest.fixture
def torrent_actions(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    actions = {}

    for name in ("get_registered_torrents", "get_torrent_from_url", "add_torrent_from_url", "remove_torrent"):
        actions[name] = Mock()
        monkeypatch.setattr(telegram_bot, name, actions[name])

    actions["rpc"] = Mock()
    monkeypatch.setattr(telegram_bot, "RPCObjectsRegistry", SimpleNamespace(get=actions["rpc"]))
    return SimpleNamespace(**actions)

@pytest.fixture(params=["message", "callback"])
def update(request: pytest.FixtureRequest) -> SimpleNamespace:
    owner = SimpleNamespace(username="owner")
    message = Mock(chat_id=17, from_user=owner)
    callback = SimpleNamespace(message=message, from_user=owner) if request.param == "callback" else None
    return SimpleNamespace(
        effective_user=owner,
        effective_message=message,
        message=None if callback else message,
        callback_query=callback,
    )

@pytest.mark.parametrize("allowed_users, user, expected", [
    pytest.param("owner,second", SimpleNamespace(username="owner"), True, id="owner"),
    pytest.param("owner,second", SimpleNamespace(username="second"), True, id="second"),
    pytest.param(" @OWNER , second ", SimpleNamespace(username="Owner"), True, id="normalized"),
    pytest.param("owner", SimpleNamespace(username="intruder"), False, id="intruder"),
    pytest.param("owner", SimpleNamespace(username=None), False, id="no-username"),
    pytest.param("owner", None, False, id="no-user"),
    pytest.param("", SimpleNamespace(username="intruder"), True, id="open"),
    pytest.param(" ", SimpleNamespace(username="intruder"), False, id="empty-entries"),
])
def test_allowed_user(
        mock_telegram_plugin: None, allowed_users: str, user: SimpleNamespace | None, expected: bool
) -> None:
    configured = TelegramBot(token="review_token", allowed_users=allowed_users)

    assert configured.is_allowed_user(SimpleNamespace(effective_user=user)) is expected

@pytest.mark.parametrize("data", [
    "add_torrent", "list_torrents", "delete_torrent", "hash:review_hash", "hash:review_hash:0", "hash:review_hash:1",
])
def test_group_callbacks_reject_intruder(bot: TelegramBot, torrent_actions: SimpleNamespace, data: str) -> None:
    owner = SimpleNamespace(username="owner")
    intruder = SimpleNamespace(username="intruder")
    message = Mock(from_user=owner)
    callback = Mock(data=data, from_user=intruder, message=message)
    update = SimpleNamespace(callback_query=callback, effective_user=intruder)
    context = SimpleNamespace(user_data={}, bot=Mock())

    bot.handle_callbacks(update, context)

    for action in vars(torrent_actions).values():
        action.assert_not_called()

    callback.answer.assert_called_once_with("Access denied.", show_alert=True)
    message.reply_text.assert_not_called()
    assert context.user_data == {}

@pytest.mark.parametrize("handler", [
    "handle_ask_url", "handle_process_url", "handle_ask_download_path", "handle_remove_torrents",
    "command_add_torrent", "command_list_torrents", "command_remove_torrents",
])
def test_restricted_handlers_reject_intruder(bot: TelegramBot, torrent_actions: SimpleNamespace, handler: str) -> None:
    update = SimpleNamespace(effective_user=SimpleNamespace(username="intruder"))
    context = SimpleNamespace(user_data={"url": "unchanged"})

    getattr(bot, handler)(update, context)

    for action in vars(torrent_actions).values():
        action.assert_not_called()

    assert context.user_data == {"url": "unchanged"}

@pytest.mark.parametrize("allowed_users, username", [("owner", "owner"), ("", "intruder")])
@pytest.mark.parametrize("with_data", [False, True])
def test_remove_callback(
    mock_telegram_plugin: None, torrent_actions: SimpleNamespace, allowed_users: str, username: str, with_data: bool,
) -> None:
    configured = TelegramBot(token="review_token", allowed_users=allowed_users)
    torrent_actions.get_registered_torrents.return_value = {"review_hash": {"name": "Review torrent"}}
    message = Mock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(username=username),
        callback_query=Mock(data=f"hash:review_hash:{int(with_data)}", message=message),
    )

    configured.handle_callbacks(update, SimpleNamespace())

    torrent_actions.remove_torrent.assert_called_once_with("review_hash", with_data=with_data)
    message.reply_text.assert_called_once_with("Torrent `Review torrent` was removed")

def test_list_command(bot: TelegramBot, torrent_actions: SimpleNamespace, update: SimpleNamespace) -> None:
    torrent_actions.get_registered_torrents.return_value = {
        "first": {"name": "First", "url": "https://review.invalid/1"},
        "second": {"name": "Second"},
    }

    bot.command_list_torrents(update, SimpleNamespace())

    update.effective_message.reply_text.assert_called_once_with("1. First\nhttps://review.invalid/1\n\n2. Second")

@pytest.mark.parametrize("command", ["command_list_torrents", "command_remove_torrents"])
def test_empty_commands(
        bot: TelegramBot, torrent_actions: SimpleNamespace, update: SimpleNamespace, command: str
) -> None:
    torrent_actions.get_registered_torrents.return_value = {}
    context = SimpleNamespace(bot=Mock())

    getattr(bot, command)(update, context)

    update.effective_message.reply_text.assert_called_once_with("No torrents yet.")
    context.bot.send_message.assert_not_called()

def test_remove_command_keyboard(bot: TelegramBot, torrent_actions: SimpleNamespace, update: SimpleNamespace) -> None:
    torrent_actions.get_registered_torrents.return_value = {"review_hash": {"hash": "review_hash", "name": "Review"}}
    context = SimpleNamespace(bot=Mock())

    bot.command_remove_torrents(update, context)

    telegram_bot.InlineKeyboardButton.assert_has_calls([call(text="Review", callback_data="hash:review_hash")])
    context.bot.send_message.assert_called_once_with(
        17, text="Which torrent do you want to remove?", reply_markup=telegram_bot.InlineKeyboardMarkup.return_value,
    )

@pytest.mark.parametrize("command", ["command_list_torrents", "command_remove_torrents"])
def test_commands_without_message(bot: TelegramBot, torrent_actions: SimpleNamespace, command: str) -> None:
    update = SimpleNamespace(effective_user=SimpleNamespace(username="owner"), effective_message=None)

    getattr(bot, command)(update, SimpleNamespace())

    torrent_actions.get_registered_torrents.assert_not_called()
