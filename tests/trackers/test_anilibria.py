import pytest

from torrt.trackers.anilibria import AnilibriaTracker


@pytest.mark.parametrize("test_input,expected", [
    ('https://www.anilibria.tv/release/kabukichou-sherlock.html', 'kabukichou-sherlock'),
    ('https://anilibria.top/anime/releases/release/mairimashita-iruma-kun', 'mairimashita-iruma-kun'),
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
def test_sanitize_quality(test_input, expected):
    assert AnilibriaTracker.sanitize_quality(test_input) == expected


@pytest.mark.parametrize("test_input,expected", [
    ('1-9', (1, 9)),
    ('1-10', (1, 10)),
    ('21-39', (21, 39)),
])
def test_to_tuple(test_input, expected):
    assert AnilibriaTracker.to_tuple(test_input) == expected


def make_torrent(hash_, type_, quality, label, magnet=None, updated_at="2024-01-01T00:00:00+00:00"):
    return {
        "hash": hash_,
        "type": {"value": type_},
        "quality": {"value": quality},
        "label": label,
        "magnet": magnet or f"magnet:?xt=urn:btih:{hash_}",
        "updated_at": updated_at,
    }


def test_get_download_link_preserve_priorities(monkeypatch):
    """Test that `get_download_link` returns link according user-defined quality priorities."""

    testable = AnilibriaTracker(quality_prefs=['webrip720p', 'webrip1080p'])
    expected_hash = 'cb88332e8a1bb5bd0eb8e831b93e72fa0edb8b7a'

    monkeypatch.setattr(testable, "_find_available_torrents", lambda url: {
        "webrip1080p": make_torrent('a' * 40, 'WEBRip', '1080p', 'R [WEBRip 1080p][1-10]'),
        "webrip720p": make_torrent(expected_hash, 'WEBRip', '720p', 'R [WEBRip 720p][1-10]'),
    })

    actual = testable.get_download_link('https://anilibria.top/anime/releases/release/dummy_release')

    assert actual.endswith(f'/torrents/{expected_hash}/file')


def test_find_available_qualities(monkeypatch):
    """Test that `find_available_qualities` picks the latest episode range and skips recaps."""

    testable = AnilibriaTracker()

    monkeypatch.setattr(testable, "api_get_release_by_code", lambda code: {
        "torrents": [
            make_torrent('a' * 40, 'HDTVRip', '1080p', 'R [HDTVRip 1080p][1-12]'),
            make_torrent('b' * 40, 'HDTVRip', '1080p', 'R [HDTVRip 1080p][13-24]'),
            make_torrent('c' * 40, 'HDTVRip', '720p', 'R [HDTVRip 720p][13-24]'),
            make_torrent('d' * 40, 'HDTVRip', '1080p', 'R [HDTVRip 1080p][Рекап]'),
        ]
    })

    actual = testable.find_available_qualities('https://anilibria.top/anime/releases/release/dummy_release')

    assert set(actual) == {'hdtvrip1080p', 'hdtvrip720p'}
    assert actual['hdtvrip1080p'].endswith(f"/torrents/{'b' * 40}/file")


def test_get_magnet_link(monkeypatch):

    testable = AnilibriaTracker()
    expected = f"magnet:?xt=urn:btih:{'e' * 40}"

    monkeypatch.setattr(testable, "_find_available_torrents", lambda url: {
        "hdtvrip1080p": make_torrent('e' * 40, 'HDTVRip', '1080p', 'R [HDTVRip 1080p][1-10]', magnet=expected),
    })

    assert testable.get_magnet_link('https://anilibria.top/anime/releases/release/dummy_release') == expected


def test_extract_page_date_updated(monkeypatch):

    testable = AnilibriaTracker()

    monkeypatch.setattr(testable, "api_get_release_by_code", lambda code: {
        "torrents": [
            make_torrent('a' * 40, 'HDTVRip', '1080p', 'R [HDTVRip 1080p][1-10]', updated_at="2024-01-01T00:00:00+00:00"),
            make_torrent('b' * 40, 'HDTVRip', '720p', 'R [HDTVRip 720p][1-10]', updated_at="2024-02-02T00:00:00+00:00"),
        ]
    })

    testable.find_available_qualities('https://anilibria.top/anime/releases/release/dummy_release')

    assert testable.extract_page_date_updated().isoformat() == '2024-02-02T00:00:00'
