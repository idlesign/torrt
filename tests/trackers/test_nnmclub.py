from torrt.trackers.nnmclub import NNMClubTracker


def test_get_torrent(response_mock, datafix_read, datafix_dir):

    tracker = NNMClubTracker()
    tracker.raise_on_error_response = True

    test_torrent = (datafix_dir / 'test.torrent').read_bytes()

    with response_mock([
        f"GET https://nnmclub.to/forum/viewtopic.php?t=889443&sid=None -> 200: {datafix_read('nnmclub.html')}",
        b"GET https://nnmclub.to/forum/download.php?id=762672&sid=None -> 200:" + test_torrent,

    ]) as _:
        torr = tracker.get_torrent('https://nnmclub.to/forum/viewtopic.php?t=889443')
        assert torr.hash == 'c815be93f20bf8b12fed14bee35c14b19b1d1984'
        assert torr.url == 'https://nnmclub.to/forum/viewtopic.php?t=889443'
        assert torr.url_file == 'https://nnmclub.to/forum/download.php?id=762672'
        assert torr.parsed.comment == 'примечание'
        assert torr.page.cover == 'http://funkyimg.com/i/VZL6.jpg'
        assert torr.page.date_updated == '2015-04-17 17:50:51'
        assert torr.page.title == 'Реймонд Хеттинджер | Super — это супер! (2015) HDTV :: NNM-Club'
