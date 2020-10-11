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


@pytest.mark.parametrize("test_input,expected", [
    ('1-9', (1, 9)),
    ('1-10', (1, 10)),
    ('21-39', (21, 39)),
])
def test_to_tuple(test_input, expected):
    assert AnilibriaTracker.to_tuple(test_input) == expected


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


def test_find_available_qualities_handle_first_episode_available(monkeypatch):
    """
    Test that `find_available_qualities` returns single-episode torrent if only the first episode is available.
    """

    # given
    testable = AnilibriaTracker()

    def mockreturn(url):
        return {
            "status": True,
            "data": {
                "id": 1000,
                "code": "dummy_release",
                "series": "1",
                "torrents": [
                    {
                        "id": 10001,
                        "hash": "cb88332e8a1bb5bd0eb8e831b93e72fa0edb8b7a",
                        "leechers": 1,
                        "seeders": 86,
                        "completed": 612,
                        "quality": "WEBRip 1080p",
                        "series": "1",
                        "size": 1537651272,
                        "url": "/upload/torrents/11113.torrent",
                        "ctime": 1594909216
                    }
                ]
            },
            "error": None
        }

    monkeypatch.setattr(testable, "api_get_release_by_code", mockreturn)
    # when
    actual = testable.find_available_qualities('https://anilibria.tv/release/dummy_release.html')
    # then
    assert actual == {"webrip1080p": "https://www.anilibria.tv/upload/torrents/11113.torrent"}
