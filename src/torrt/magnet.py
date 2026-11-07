"""Validate BitTorrent magnet links without fetching their metadata."""

from base64 import b32decode
from dataclasses import dataclass
from re import fullmatch, search
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True, slots=True)
class MagnetData:
    """Keep a magnet link and its normalized BitTorrent v1 identity."""

    magnet: str
    hash: str
    name: str

def parse_magnet(magnet: str) -> MagnetData:
    """Read a v1 info hash and display name without changing the original URI."""

    if (
        not isinstance(magnet, str)
        or any(ord(character) < 32 or ord(character) == 127 for character in magnet)
        or search(r"%(?![0-9a-fA-F]{2})", magnet)
    ):
        raise ValueError("Invalid magnet URI")

    try:
        parsed = urlsplit(magnet)

        if parsed.scheme.lower() != "magnet" or parsed.netloc or parsed.path or parsed.fragment:
            raise ValueError("Invalid magnet URI")

        params = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=1000, errors="strict")

    except ValueError:
        raise ValueError("Invalid magnet URI") from None

    if any(
        ord(character) < 32 or ord(character) == 127
        for values in params.values()
        for value in values
        for character in value
    ):
        raise ValueError("Invalid magnet URI")

    hashes = set()

    for topic in params.get("xt", []):

        if not topic.lower().startswith("urn:btih:"):
            continue

        hash_value = topic[len("urn:btih:"):]

        if fullmatch(r"[0-9a-fA-F]{40}", hash_value):
            hashes.add(hash_value.lower())

        elif fullmatch(r"[a-zA-Z2-7]{32}", hash_value):
            hashes.add(b32decode(hash_value, casefold=True).hex())

        else:
            raise ValueError("Invalid BitTorrent v1 magnet hash")

    if len(hashes) != 1:
        raise ValueError("Magnet URI must identify one BitTorrent v1 torrent")

    name = next((value for candidate in params.get("dn", []) if (value := candidate.strip())), "")
    return MagnetData(magnet=magnet, hash=hashes.pop(), name=name)
