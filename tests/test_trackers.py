import pytest

from torrt.utils import TrackerObjectsRegistry, get_torrent_from_url

NEED_SKIP = True

@pytest.mark.skipif(NEED_SKIP, reason='Temporary skip')
def test_trackers():
    tracker_objects = TrackerObjectsRegistry.get()

    assert tracker_objects

    for tracker_alias, tracker_obj in tracker_objects.items():

        if not tracker_obj.active:
            continue

        urls = tracker_obj.test_urls

        for url in urls:
            torrent_data = get_torrent_from_url(url)
            assert torrent_data, f'{tracker_alias}: Unable to deal with test URL {url}'
