from torrt.trackers.rutor import RutorTracker

def test_get_id_from_link():
    tracker = RutorTracker()
    tracker.raise_on_error_response = True

    idUrls = {
        '41': 'http://rutor.info/torrent/41/polnyj-oblom_big-nothing-2006-dvdrip',
        '472': 'http://rutor.info/torrent/472',
        '795039': 'http://rutor.info/torrent/795039/vanda/vizhn_wandavision-01h01-03-iz-09-2021-web-dl-720p-lostfilm'
    }

    for expect_id in idUrls:
        url = idUrls[expect_id]
        id = tracker.get_id_from_link(url)
        assert id == expect_id
