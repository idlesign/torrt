from datetime import datetime
from torrt.trackers.kinozal import KinozalTracker


def test_get_torrent(response_mock, datafix_read, datafix_dir):

    tracker = KinozalTracker()
    tracker.raise_on_error_response = True

    test_torrent = (datafix_dir / 'test.torrent').read_bytes()

    with response_mock([
        f"GET https://kinozal.me/details.php?id=557593 -> 200: {datafix_read('kinozal.html', encoding='windows-1251')}",
        b"GET https://kinozal.me/download.php?id=557593 -> 200:" + test_torrent,

    ]) as _:
        torr = tracker.get_torrent('https://kinozal.me/details.php?id=557593', datetime(2015, 4, 16))
        assert torr.hash == 'c815be93f20bf8b12fed14bee35c14b19b1d1984'
        assert torr.url == 'https://kinozal.me/details.php?id=557593'
        assert torr.url_file == 'https://dl.kinozal.me/download.php?id=557593'
        assert torr.parsed.comment == 'примечание'
        assert torr.page.date_updated == datetime(2015, 5, 16, 18, 0)
        assert torr.page.title == 'Властелин колец (Трилогия) (Смешной перевод Гоблина) / The Lord of the Rings. Trilogy / 2001-2003 / АП (Пучков) / DVDRip :: Кинозал.МЕ'
