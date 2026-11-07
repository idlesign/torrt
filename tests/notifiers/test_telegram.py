import json
import logging
from collections.abc import Callable

import pytest
from requests import ConnectionError

from torrt.notifiers.telegram import TelegramNotifier


def test_send_message_network_error(response_mock: Callable, caplog: pytest.LogCaptureFixture) -> None:
    token = "123456:review_secret"
    notifier = TelegramNotifier(token=token, chat_id="review_chat")
    url = f"{notifier.url}{token}/sendMessage"
    error = ConnectionError("Review network failure")
    caplog.set_level(logging.DEBUG, logger="torrt")

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", url, body=error)
        notifier.send_message("Review message")

        assert mocked.calls[0].request.url == url

    assert "Failed to send Telegram message: Review network failure" in caplog.text

def test_send_message(response_mock: Callable, caplog: pytest.LogCaptureFixture) -> None:
    token = "123456:review_secret"
    notifier = TelegramNotifier(token=token, chat_id="review_chat")
    url = f"{notifier.url}{token}/sendMessage"
    caplog.set_level(logging.DEBUG, logger="torrt")

    with response_mock(f"POST {url} -> 200:{{\"ok\": true, \"result\": {{}}}}", bypass=False) as mocked:
        notifier.send_message("Review message")

        request = mocked.calls[0].request
        assert request.url == url
        assert json.loads(request.body) == {"chat_id": "review_chat", "text": "Review message"}

    assert "Telegram message was sent to user review_chat" in caplog.text
    assert not [record for record in caplog.records if record.levelno >= logging.WARNING]
