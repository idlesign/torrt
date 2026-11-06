from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
from responses import RequestsMock

from torrt.base_tracker import GenericPrivateTracker
from torrt.trackers.anidub import AniDUBTracker
from torrt.trackers.eniahd import EniaHDTracker
from torrt.trackers.nnmclub import NNMClubTracker
from torrt.trackers.rutracker import RuTrackerTracker
from torrt.utils import TorrtConfig, get_torrent_from_url


@pytest.mark.parametrize("url, expected", [
    pytest.param("https://rutracker.org/forum/viewtopic.php?t=1", True, id="primary"),
    pytest.param("http://rutracker.net/forum/viewtopic.php?t=1", True, id="mirror"),
    pytest.param("https://www.rutracker.org/forum/viewtopic.php?t=1", True, id="www"),
    pytest.param("https://RuTracker.ORG/forum/viewtopic.php?t=1", True, id="case"),
    pytest.param("https://attacker.invalid/rutracker.org/", False, id="path"),
    pytest.param("https://attacker.invalid/?tracker=rutracker.org", False, id="query"),
    pytest.param("https://attacker.invalid/#rutracker.org", False, id="fragment"),
    pytest.param("https://rutracker.org.attacker.invalid/", False, id="suffix"),
    pytest.param("https://unexpected.rutracker.org/", False, id="subdomain"),
    pytest.param("https://rutracker.org@attacker.invalid/", False, id="host-in-username"),
    pytest.param("https://review:password@rutracker.org/", False, id="credentials"),
    pytest.param("ftp://rutracker.org/", False, id="scheme"),
    pytest.param("https:///rutracker.org", False, id="missing-host"),
    pytest.param("https://rutracker.org:invalid/", False, id="invalid-port"),
    pytest.param("https://rutracker.org:99999/", False, id="out-of-range-port"),
    pytest.param("https://[rutracker.org/", False, id="invalid-address"),
    pytest.param("rutracker.org", False, id="not-url"),
    pytest.param("", False, id="empty"),
    pytest.param(None, False, id="none"),
])
def test_can_handle_tracker_url(url: str | None, expected: bool) -> None:
    assert RuTrackerTracker.can_handle(url) is expected

def test_reject_foreign_tracker_before_request(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = AniDUBTracker(username="review_user", password="review_password", cookies={"session": "review_session"})
    tracker.register()
    request = Mock()
    monkeypatch.setattr(tracker.client, "request", request)
    url = "https://attacker.invalid/tr.anidub.com/"

    assert get_torrent_from_url(url) is None
    assert tracker.get_torrent(url) is None
    assert tracker.login("attacker.invalid") is False
    request.assert_not_called()

@pytest.fixture
def datafix_dir() -> Path:
    return Path(__file__).parent / "trackers" / "datafixtures"

@pytest.fixture(params=[
    pytest.param((AniDUBTracker, "/review", "", "/review.torrent"), id="anidub"),
    pytest.param(
        (NNMClubTracker, "/forum/viewtopic.php?t=889443", "nnmclub.html", "/forum/download.php?id=762672"),
        id="nnmclub"
    ),
    pytest.param((EniaHDTracker, "/viewtopic.php?t=1558", "eniahd.html", "/dl.php?id=5669"), id="eniahd"),
])
def tracker_case(request: pytest.FixtureRequest, datafix_read: Callable, datafix_dir: Path) -> SimpleNamespace:
    tracker_class, page_path, page_fixture, download_path = request.param
    tracker = tracker_class(username="review_user", password="review_password")
    page_url = f"https://{tracker.alias}{page_path}"
    download_url = f"https://{tracker.alias}{download_path}"

    if page_fixture:
        page_html = datafix_read(page_fixture, encoding="utf-8")

    else:
        page_html = """<html><title>Review release</title>
            <div class="torrent"><div class="torrent_c"><div id="bd720">
                <div class="torrent_h"><a href="/review.torrent">Download</a></div>
            </div></div></div></html>"""

    return SimpleNamespace(
        tracker=tracker, page_url=page_url, download_url=download_url, page_html=page_html,
        anonymous_html="<html><title>Anonymous</title><form><input name=login></form></html>",
        torrent=(datafix_dir / "test.torrent").read_bytes(),
        initial_page_url=f"{page_url}&sid=" if tracker.auth_qs_param_name else page_url,
        authorized_page_url=f"{page_url}&sid=review_session" if tracker.auth_qs_param_name else page_url,
        authorized_download_url=f"{download_url}&sid=review_session" if tracker.auth_qs_param_name else download_url,
        login_url=tracker.login_url.replace("%(domain)s", tracker.alias),
    )

def add_mirror_responses(mocked: RequestsMock, tracker: GenericPrivateTracker) -> None:

    for domain in tracker.mirrors:
        mocked.add("GET", f"https://{domain}/", status=503, body="Mirror unavailable")

def test_get_torrent_after_login(
    response_mock: Callable, tracker_case: SimpleNamespace, caplog: pytest.LogCaptureFixture,
) -> None:
    tracker = tracker_case.tracker

    with response_mock([], bypass=False) as mocked:
        add_mirror_responses(mocked, tracker)
        mocked.add("GET", tracker_case.initial_page_url, body=tracker_case.anonymous_html)

        if tracker.auth_qs_param_name:
            redirect_url = f"https://{tracker.alias}/forum/index.php?sid=review_session"
            mocked.add("POST", tracker_case.login_url, status=302, headers={"Location": redirect_url})
            mocked.add("GET", redirect_url, body="Logged in")

        else:
            mocked.add("POST", tracker_case.login_url, body="Logged in", headers={
                "Set-Cookie": f"{tracker.auth_cookie_name}=review_session; Path=/",
            })

        mocked.add("GET", tracker_case.authorized_page_url, body=tracker_case.page_html)
        mocked.add("GET", tracker_case.authorized_download_url, body=tracker_case.torrent)

        result = tracker.get_torrent(tracker_case.page_url)

        assert result.hash == "c815be93f20bf8b12fed14bee35c14b19b1d1984"
        assert result.raw == tracker_case.torrent
        assert result.url == tracker_case.page_url
        assert result.url_file == tracker_case.download_url
        assert tracker.logged_in
        assert tracker.login_counter == 1
        login_requests = [request.request for request in mocked.calls if request.request.method == "POST"]
        assert len(login_requests) == 1
        page_requests = [
            request.request for request in mocked.calls
            if urlparse(request.request.url).path == urlparse(tracker_case.page_url).path
        ]
        assert len(page_requests) == 2

        if tracker.auth_qs_param_name:
            assert parse_qs(urlparse(page_requests[0].url).query, keep_blank_values=True)["sid"] == [""]
            assert parse_qs(urlparse(page_requests[1].url).query)["sid"] == ["review_session"]

        else:
            assert f"{tracker.auth_cookie_name}=review_session" in page_requests[1].headers["Cookie"]

    assert "Consecutive login attempt" not in caplog.text
    assert TorrtConfig.load()["trackers"][tracker.alias]["username"] == "review_user"

def test_get_torrent_with_failed_login(response_mock: Callable, tracker_case: SimpleNamespace) -> None:
    tracker = tracker_case.tracker

    with response_mock([], bypass=False) as mocked:
        add_mirror_responses(mocked, tracker)
        mocked.add("GET", tracker_case.initial_page_url, body=tracker_case.anonymous_html)
        mocked.add("POST", tracker_case.login_url, body="Login rejected")

        assert tracker.get_torrent(tracker_case.page_url) is None
        assert not tracker.logged_in
        assert tracker.login_counter == 1
        assert tracker.get_torrent(tracker_case.page_url) is None
        assert len([request for request in mocked.calls if request.request.method == "POST"]) == 1
        assert len(mocked.calls) == len(tracker.mirrors) + 2

def test_get_torrent_with_existing_session(response_mock: Callable, tracker_case: SimpleNamespace) -> None:
    tracker = tracker_case.tracker

    if tracker.auth_qs_param_name:
        tracker.query_string = "review_session"

    else:
        tracker.cookies = {tracker.auth_cookie_name: "review_session"}

    with response_mock([], bypass=False) as mocked:
        add_mirror_responses(mocked, tracker)
        mocked.add("GET", tracker_case.authorized_page_url, body=tracker_case.page_html)
        mocked.add("GET", tracker_case.authorized_download_url, body=tracker_case.torrent)

        result = tracker.get_torrent(tracker_case.page_url)

        assert result.hash == "c815be93f20bf8b12fed14bee35c14b19b1d1984"
        assert tracker.login_counter == 0
        assert all(request.request.method == "GET" for request in mocked.calls)
        assert len(mocked.calls) == len(tracker.mirrors) + 2
