import pytest

from torrt.trackers.anilibria import AnilibriaTracker


@pytest.mark.parametrize("test_input,expected", [
    ('https://www.anilibria.tv/release/kabukichou-sherlock.html', 'kabukichou-sherlock'),
    ('https://www.anilibria.tv/release/mairimashita-iruma-kun.html', 'mairimashita-iruma-kun'),
])
def test_extract_release_code(test_input, expected):
    assert AnilibriaTracker.extract_release_code(test_input) == expected


@pytest.mark.parametrize("test_input,expected", [
    ('WEBRip 1080p', 'webrip1080p'),
    ('WEBRip-1080p', 'webrip1080p'),
    ('WEBRip_1080p', 'webrip1080p'),
    ('', ''),
    (None, ''),
])
def test_sanitize_quantity(test_input, expected):
    assert AnilibriaTracker.sanitize_quality(test_input) == expected


def test_get_download_link_preserve_priorities(monkeypatch):
    """
    Test that `get_download_link` returns link according user-defined quality priorities
    """

    # given
    testable = AnilibriaTracker(quality_prefs=['webrip720p', 'webrip1080p'])
    expected = 'https://www.anilibria.tv/upload/torrents/webrip720p.torrent'

    def mockreturn(url):
        return {
            'webrip1080p': 'https://www.anilibria.tv/upload/torrents/webrip1080p.torrent',
            'webrip720p': expected,
        }

    monkeypatch.setattr(testable, "find_available_qualities", mockreturn)
    # when
    actual = testable.get_download_link('https://anilibria.tv/release/dummy_release.html')
    # then
    assert actual == expected
