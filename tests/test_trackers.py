from os import environ

from torrt.main import bootstrap
from torrt.utils import get_torrent_from_url, TrackerObjectsRegistry


def tunnel(use_local=False):
    tunnel_through = environ.get('TUNNEL', 'socks5://127.0.0.1:9150' if use_local else None)

    if tunnel_through:
        # Instruct `requests` http://docs.python-requests.org/en/master/user/advanced/#socks
        environ['HTTP_PROXY'] = tunnel_through
        environ['HTTPS_PROXY'] = tunnel_through


tunnel()


def test_trackers():
    bootstrap()

    tracker_objects = TrackerObjectsRegistry.get()

    assert tracker_objects

    for tracker_alias, tracker_obj in tracker_objects.items():

        urls = tracker_obj.test_urls

        for url in urls:
            torrent_data = get_torrent_from_url(url)
            assert torrent_data, '%s: Unable to parse test URL %s' % (tracker_alias, url)
