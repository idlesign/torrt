from base64 import b32encode
from datetime import datetime

import pytest

from torrt.magnet import parse_magnet
from torrt.utils import PageData, TorrentData

INFO_HASH = "0123456789abcdef0123456789abcdef01234567"
BASE32_HASH = b32encode(bytes.fromhex(INFO_HASH)).decode()

@pytest.mark.parametrize("hash_value", [INFO_HASH, INFO_HASH.upper(), BASE32_HASH, BASE32_HASH.lower()])
def test_parse_magnet_preserves_uri(hash_value: str) -> None:
    magnet = f"magnet:?xt=urn:btih:{hash_value}&dn=Review+%D0%B8%D0%BC%D1%8F&tr=https%3A%2F%2Ffirst.invalid"
    magnet += "&tr=udp%3A%2F%2Fsecond.invalid%3A80"

    parsed = parse_magnet(magnet)

    assert parsed.hash == INFO_HASH
    assert parsed.name == "Review имя"
    assert parsed.magnet == magnet

def test_parse_magnet_accepts_repeated_identity() -> None:
    magnet = f"magnet:?xt=urn:btih:{INFO_HASH}&xt=urn:btih:{BASE32_HASH}&xt=urn:btmh:1220{'a' * 64}"

    assert parse_magnet(magnet).hash == INFO_HASH

@pytest.mark.parametrize("magnet", [
    "",
    None,
    f"https://review.invalid/?xt=urn:btih:{INFO_HASH}",
    f"magnet://review.invalid/?xt=urn:btih:{INFO_HASH}",
    f"magnet:path?xt=urn:btih:{INFO_HASH}",
    f"magnet:?xt=urn:btih:{INFO_HASH}#fragment",
    "magnet:?dn=Review",
    "magnet:?xt=urn:btih:invalid&tr=https://tracker.invalid/private_review_token",
    f"magnet:?xt=urn:btih:{'x' * 40}",
    f"magnet:?xt=urn:btih:{'1' * 39}",
    f"magnet:?xt=urn:btih:{INFO_HASH}&xt=urn:btih:{'a' * 40}",
    f"magnet:?xt=urn:btmh:1220{'a' * 64}",
    f"magnet:?xt=urn:btih:{INFO_HASH}\n",
    f"magnet:?xt=urn:btih:{INFO_HASH}&dn=Bad%0Aname",
    f"magnet:?xt=urn:btih:{INFO_HASH}&dn=%ff",
    f"magnet:?xt=urn:btih:{INFO_HASH}&tr=https%XXreview.invalid",
])
def test_parse_magnet_rejects_invalid_input(magnet: str | None) -> None:

    with pytest.raises(ValueError, match=r"[Mm]agnet"):
        parse_magnet(magnet)

@pytest.mark.parametrize("display_name, title, expected", [
    ("Magnet+name", "Page name", "Magnet name"),
    ("", "Page name", "Page name"),
    ("", "", INFO_HASH),
])
def test_torrent_data_uses_available_name(display_name: str, title: str, expected: str) -> None:
    torrent = TorrentData(
        magnet=f"magnet:?xt=urn:btih:{INFO_HASH}&dn={display_name}",
        page=PageData(title=title, cover="", date_updated=None),
    )

    assert torrent.hash == INFO_HASH
    assert torrent.name == expected
    assert torrent.raw == b""
    assert torrent.parsed is None

def test_torrent_data_roundtrip() -> None:
    torrent = TorrentData(
        hash=INFO_HASH.upper(), name="Stored name", magnet=f"magnet:?xt=urn:btih:{INFO_HASH}&dn=Other+name",
        url="https://review.invalid/page", url_file="https://review.invalid/review.torrent",
        page=PageData(title="Page name", cover="https://review.invalid/cover.jpg", date_updated=datetime(2026, 11, 6)),
    )
    torrent.set_params({"category": "Review"})

    restored = TorrentData.from_dict(torrent.to_dict())

    assert restored.to_dict() == torrent.to_dict()
    assert restored.hash == INFO_HASH
    assert restored.name == "Stored name"
    assert restored.page.date_updated == datetime(2026, 11, 6)
    assert restored.raw == b""
    assert restored.parsed is None

def test_torrent_data_rejects_conflicting_magnet_hash() -> None:

    with pytest.raises(ValueError, match="Magnet hash does not match torrent hash"):
        TorrentData.from_dict({"hash": "a" * 40, "magnet": f"magnet:?xt=urn:btih:{INFO_HASH}"})
