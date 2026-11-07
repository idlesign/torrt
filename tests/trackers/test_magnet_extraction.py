from collections.abc import Callable
from datetime import datetime
from html import escape
from pathlib import Path

import pytest

from torrt.base_tracker import BaseTracker, GenericPrivateTracker
from torrt.trackers.eniahd import EniaHDTracker
from torrt.trackers.nnmclub import NNMClubTracker
from torrt.trackers.rutor import RutorTracker
from torrt.trackers.rutracker import RuTrackerTracker
from torrt.utils import TorrtConfig, get_torrent_from_url

INFO_HASH = "0123456789abcdef0123456789abcdef01234567"
MAGNET = f"magnet:?xt=urn:btih:{INFO_HASH}&dn=Review+release&tr=https%3A%2F%2Ftracker.invalid%2Fprivate_review_token"

@pytest.mark.parametrize("tracker_class", [NNMClubTracker, EniaHDTracker, RuTrackerTracker, RutorTracker])
def test_get_magnet_without_torrent_file(response_mock: Callable, tracker_class: type[BaseTracker]) -> None:
    tracker = tracker_class()
    tracker.mirror_picked = tracker.alias
    url = f"https://{tracker.alias}/viewtopic.php?t=123"
    request_url = f"{url}&sid=" if getattr(tracker, "auth_qs_param_name", None) else url
    page = f'<html><title>Page title</title><a href="{escape(MAGNET, quote=True)}">Magnet</a></html>'

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", request_url, body=page)

        torrent = tracker.get_torrent(url, prefer_magnet=True, last_updated=datetime(2099, 1, 1))

        assert torrent.hash == INFO_HASH
        assert torrent.name == "Review release"
        assert torrent.magnet == MAGNET
        assert torrent.url == url
        assert torrent.url_file == ""
        assert torrent.raw == b""
        assert torrent.parsed is None
        assert torrent.page.title == "Page title"
        assert len(mocked.calls) == 1

@pytest.mark.parametrize("prefer_magnet, magnet_href", [
    pytest.param(False, MAGNET, id="disabled"),
    pytest.param(True, "", id="missing"),
    pytest.param(True, "magnet:?xt=invalid&tr=private_review_token", id="invalid"),
])
def test_get_torrent_falls_back_to_file(
    response_mock: Callable, datafix_dir: Path,
    prefer_magnet: bool, magnet_href: str,
) -> None:
    tracker = RutorTracker()
    tracker.mirror_picked = tracker.alias
    url = f"https://{tracker.alias}/torrent/123"
    download_url = f"https://{tracker.alias}/download/123"
    page = f'<html><title>Page title</title><a href="{escape(magnet_href, quote=True)}">Magnet</a>'
    page += '<a href="/download/123">Download</a></html>'
    content = (datafix_dir / "test.torrent").read_bytes()

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", url, body=page)
        mocked.add("GET", download_url, body=content)

        torrent = tracker.get_torrent(url, prefer_magnet=prefer_magnet)

        assert torrent.raw == content
        assert torrent.magnet == ""
        assert torrent.url_file == download_url
        assert len(mocked.calls) == 2

@pytest.mark.parametrize("tracker_class", [NNMClubTracker, EniaHDTracker, RuTrackerTracker])
def test_get_magnet_after_login(response_mock: Callable, tracker_class: type[GenericPrivateTracker]) -> None:
    tracker = tracker_class(username="review_user", password="review_password")
    tracker.mirror_picked = tracker.alias
    url = f"https://{tracker.alias}/viewtopic.php?t=123"
    initial_url = f"{url}&sid=" if tracker.auth_qs_param_name else url
    authorized_url = f"{url}&sid=review_session" if tracker.auth_qs_param_name else url
    login_url = tracker.login_url.replace("%(domain)s", tracker.alias)
    page = f'<html><title>Page title</title><a href="{escape(MAGNET, quote=True)}">Magnet</a></html>'

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", initial_url, body="<html><title>Guest</title></html>")

        if tracker.auth_qs_param_name:
            redirect_url = f"https://{tracker.alias}/index.php?sid=review_session"
            mocked.add("POST", login_url, status=302, headers={"Location": redirect_url})
            mocked.add("GET", redirect_url, body="Logged in")

        else:
            mocked.add("POST", login_url, body="Logged in", headers={
                "Set-Cookie": f"{tracker.auth_cookie_name}=review_session; Path=/",
            })

        mocked.add("GET", authorized_url, body=page)

        torrent = tracker.get_torrent(url, prefer_magnet=True)

        assert torrent.hash == INFO_HASH
        assert torrent.magnet == MAGNET
        assert torrent.page.title == "Page title"
        assert tracker.logged_in
        assert len([call for call in mocked.calls if call.request.method == "POST"]) == 1
        assert len([call for call in mocked.calls if "viewtopic.php" in call.request.url]) == 2

def test_get_magnet_with_failed_login(response_mock: Callable) -> None:
    tracker = EniaHDTracker(username="review_user", password="review_password")
    tracker.mirror_picked = tracker.alias
    url = f"https://{tracker.alias}/viewtopic.php?t=123"

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", url, body="<html><title>Guest</title></html>")
        mocked.add("POST", tracker.login_url.replace("%(domain)s", tracker.alias), body="Login rejected")

        assert tracker.get_torrent(url, prefer_magnet=True) is None
        assert tracker.get_torrent(url, prefer_magnet=True) is None
        assert len(mocked.calls) == 2

def test_get_torrent_uses_global_magnet_preference(response_mock: Callable) -> None:
    tracker = RutorTracker()
    tracker.mirror_picked = tracker.alias
    tracker.register()
    TorrtConfig.update({"prefer_magnet": True})
    url = f"https://{tracker.alias}/torrent/123"
    page = f'<html><title>Page title</title><a href="{escape(MAGNET, quote=True)}">Magnet</a></html>'

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", url, body=page)

        assert get_torrent_from_url(url).magnet == MAGNET
        assert len(mocked.calls) == 1

@pytest.mark.parametrize("tracker_class", [BaseTracker, GenericPrivateTracker])
def test_magnet_extraction_is_opt_in(tracker_class: type[BaseTracker]) -> None:
    tracker = tracker_class()

    assert tracker.get_magnet_link("https://review.invalid/page") == ""

def test_get_torrent_rejects_raw_magnet() -> None:

    assert get_torrent_from_url(MAGNET) is None

def test_get_torrent_overrides_global_preference(response_mock: Callable, datafix_dir: Path) -> None:
    tracker = RutorTracker()
    tracker.mirror_picked = tracker.alias
    tracker.register()
    TorrtConfig.update({"prefer_magnet": True})
    url = f"https://{tracker.alias}/torrent/123"
    page = f'<html><a href="{escape(MAGNET, quote=True)}">Magnet</a><a href="/download/123">Download</a></html>'
    content = (datafix_dir / "test.torrent").read_bytes()

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", url, body=page)
        mocked.add("GET", f"https://{tracker.alias}/download/123", body=content)

        torrent = get_torrent_from_url(url, prefer_magnet=False)

        assert torrent.raw == content
        assert torrent.magnet == ""
        assert len(mocked.calls) == 2

def test_get_torrent_rejects_non_boolean_preference() -> None:
    TorrtConfig.update({"prefer_magnet": "false"})

    with pytest.raises(ValueError, match="Magnet preference must be a boolean"):
        get_torrent_from_url("https://rutor.info/torrent/123")
