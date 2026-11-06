import json
import logging
from collections.abc import Callable
from urllib.parse import quote

import pytest
from requests import ConnectionError

from torrt.notifiers.telegram import TelegramNotifier


def test_send_message_redacts_network_error(response_mock: Callable, caplog: pytest.LogCaptureFixture) -> None:
    token = "123456:review_secret"
    notifier = TelegramNotifier(token=token, chat_id="review_chat")
    url = f"{notifier.url}{token}/sendMessage"
    encoded_token = quote(token, safe="")
    error = ConnectionError(f"Connection failed for {url}; token={encoded_token}")
    caplog.set_level(logging.DEBUG, logger="torrt")

    with response_mock([], bypass=False) as mocked:
        mocked.add("POST", url, body=error)
        notifier.send_message("Review message")

        assert mocked.calls[0].request.url == url

    assert token not in caplog.text
    assert quote(token, safe="") not in caplog.text
    assert "Failed to send Telegram message: Connection failed" in caplog.text
    assert "[REDACTED]" in caplog.text

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

    assert token not in caplog.text
    assert "Telegram message was sent to user review_chat" in caplog.text
    assert not [record for record in caplog.records if record.levelno >= logging.WARNING]
