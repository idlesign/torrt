from typing import Dict

import pytest
from bs4 import BeautifulSoup

from torrt.trackers.ytsmx import YtsmxTracker


@pytest.fixture()
def tracker():
    return YtsmxTracker()


@pytest.fixture(scope='module')
def stub_links():
    return {
        '720P.WEB': '720p_torrent.link',
        '1080P.WEB': '1080p_torrent.link',
    }


@pytest.mark.parametrize('given,expected', [
    ({'type': 'web', 'quality': '720p'}, '720P.WEB'),
    ({'type': 'web', 'quality': '1080p'}, '1080P.WEB'),
])
def test_quality_from_torrent(given: Dict[str, str], expected: str):
    assert YtsmxTracker._get_quality_from_torrent(given) == expected


@pytest.mark.parametrize('given,expected', [
    ('    720P.web', '720P.WEB'),
    ('1080p.wEb    ', '1080P.WEB'),
])
def test_sanitize_config_quality(given: str, expected: str):
    assert YtsmxTracker._sanitize_quality(given) == expected


def test_extract_movie_id(tracker: YtsmxTracker):
    stub_html = '''
    <!DOCTYPE html><html>
    <head></head>
    <body><div id="movie-info" data-movie-id="123"></body></html>
    '''
    soup = BeautifulSoup(stub_html)

    movie_id = tracker._extract_movie_id(soup)
    assert movie_id == '123'


def test_quality_links(tracker: YtsmxTracker):
    stub_details = {
        'data': {
            'movie': {
                'torrents': [
                    {
                        'quality': '720p',
                        'type': 'web',
                        'url': 'http://example.com/torrent.file'
                    }
                ]
            }
        }
    }
    links = tracker._get_quality_links(stub_details)
    items = list(links.items())
    assert len(items) == 1

    key, link = items[0]
    assert key == '720P.WEB'
    assert link == 'http://example.com/torrent.file'


@pytest.mark.parametrize('preffered, expected', [
    (['1080P.WEB', '720P.WEB'], ('1080P.WEB', '1080p_torrent.link')),
    (['720P.WEB', '1080P.WEB'], ('720P.WEB', '720p_torrent.link')),
    (['8K.HDTV', '4K.WEB', '2K,HDTV'], None),
    ([], None),
])
def test_preffered_quality(preffered, expected, stub_links):
    tracker = YtsmxTracker(quality_prefs=preffered)
    assert tracker._get_preffered_link(stub_links) == expected
