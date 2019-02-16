from torrt.base_tracker import GenericPrivateTracker
from torrt.main import bootstrap, TrackerClassesRegistry
from torrt.utils import get_torrent_from_url, TrackerObjectsRegistry


def test_trackers():
    bootstrap()

    tracker_objects = TrackerObjectsRegistry.get()
    tracker_classes = TrackerClassesRegistry.get()

    assert tracker_classes

    for tracker_alias, tracker_cls in tracker_classes.items():

        settings = {}
        already_registered = tracker_alias in tracker_objects

        if issubclass(tracker_cls, GenericPrivateTracker):

            if not already_registered:
                # No way to acces private tracker without credentials.
                continue

            # Will use local credentials to test private tracker.

        else:
            # Automatically register public tracker using default settings.
            if not already_registered:
                TrackerClassesRegistry.get(tracker_alias).spawn_with_settings(settings).register()

        urls = tracker_cls.test_urls

        for url in urls:
            torrent_data = get_torrent_from_url(url)
            assert torrent_data, '%s: Unable to parse test URL %s' % (tracker_alias, url)
