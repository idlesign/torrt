import pytest

from torrt.trackers.anilibria import AnilibriaTracker


@pytest.mark.parametrize("test_input,expected", [
    ('WEBRip 1080p', 'webrip1080p'),
    ('WEBRip-1080p', 'webrip1080p'),
    ('WEBRip_1080p', 'webrip1080p'),
    ('', ''),
    (None, ''),
])
def test_sanitize_quantity(test_input, expected):
    assert AnilibriaTracker.sanitize_quality(test_input) == expected
