from torrt.utils import get_torrent_from_url, TrackerObjectsRegistry


def test_trackers():
    tracker_objects = TrackerObjectsRegistry.get()

    assert tracker_objects

    for tracker_alias, tracker_obj in tracker_objects.items():

        urls = tracker_obj.test_urls

        for url in urls:
            torrent_data = get_torrent_from_url(url)
            assert torrent_data, f'{tracker_alias}: Unable to deal with test URL {url}'
