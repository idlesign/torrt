from torrt.trackers.eniahd import EniaHDTracker


def test_get_torrent(response_mock, datafix_read, datafix_dir):

    tracker = EniaHDTracker()
    tracker.raise_on_error_response = True

    test_torrent = (datafix_dir / 'test.torrent').read_bytes()

    with response_mock([
        f"GET https://eniatv.com/viewtopic.php?t=1558 -> 200: {datafix_read('eniahd.html')}",
        b"GET https://eniatv.com/dl.php?id=5669 -> 200:" + test_torrent,

    ]) as _:
        torr = tracker.get_torrent('https://eniatv.com/viewtopic.php?t=1558')
        assert torr.hash == 'c815be93f20bf8b12fed14bee35c14b19b1d1984'
        assert torr.url == 'https://eniatv.com/viewtopic.php?t=1558'
        assert torr.url_file == 'https://eniatv.com/dl.php?id=5669'
        assert torr.parsed.comment == 'примечание'
        assert torr.page.cover == 'https://a.radikal.ru/a01/2012/9b/d9ef857b2246.jpg'
        assert torr.page.title == 'Пространство / Экспансия / The Expanse / Сезон: 5 / Серии: 1-9 из 10 (Брек Эйснер) [2020, Канада, США, фантастика, триллер, драма, детектив, WEB-DL 720p] MVO (LostFilm) + Original + Sub (Rus, Eng) :: eniahd.com'
