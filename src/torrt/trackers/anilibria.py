import re
from collections import defaultdict
from datetime import datetime
from typing import ClassVar

from ..base_tracker import GenericPublicTracker

REGEX_NON_WORD = re.compile(r'[\W_]')
REGEX_RANGE = re.compile(r"\[(\d+-\d+)]")

HOST: str = 'https://anilibria.top'
API_URL: str = f'{HOST}/api/v1/anime'


class AnilibriaTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for anilibria.top tracker (Aniliberty API v1)."""

    alias: str = 'anilibria.top'
    mirrors: ClassVar[list[str]] = ['anilibria.tv', 'www.anilibria.tv', 'www.anilibria.top']

    test_urls: ClassVar[list[str]] = [
        'https://anilibria.top/anime/releases/release/sword-art-online-alicization',
    ]

    def __init__(self, *, quality_prefs: list[str] | None = None):

        super().__init__()

        if quality_prefs is None:
            quality_prefs = ['HDTVRip 1080p', 'HDTVRip 720p', 'WEBRip 720p']

        self.quality_prefs = quality_prefs
        self._release: dict = {}

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at a release page and return that one."""

        torrent = self._pick_torrent(url)

        if torrent is None:
            return ''

        return f"{API_URL}/torrents/{torrent['hash']}/file"

    def get_magnet_link(self, url: str) -> str:
        """Returns a magnet link for the picked torrent."""

        torrent = self._pick_torrent(url)

        if torrent is None:
            return ''

        return torrent.get('magnet', '')

    def extract_page_date_updated(self) -> datetime | None:
        """Returns the most recent torrent update date from the fetched release data."""

        dates = []

        for torrent in (self._release.get('torrents') or []):

            updated_at = torrent.get('updated_at')

            if updated_at:
                # Stored dates are kept naive.
                dates.append(datetime.fromisoformat(updated_at).replace(tzinfo=None))

        return max(dates) if dates else None

    def _pick_torrent(self, url: str) -> dict | None:
        """Returns a torrent dict for the most preferred available quality."""

        available_torrents = self._find_available_torrents(url)

        self.log_debug(f"Available in qualities: {', '.join(available_torrents)}")

        if not available_torrents:
            return None

        quality_prefs = []

        for pref in self.quality_prefs:
            pref = self.sanitize_quality(pref)

            if pref not in quality_prefs:
                quality_prefs.append(pref)

        preferred_qualities = [quality for quality in quality_prefs if quality in available_torrents]

        if not preferred_qualities:
            self.log_info(f"Torrent is not available in preferred qualities: {', '.join(quality_prefs)}")

            quality, torrent = next(iter(available_torrents.items()))
            self.log_info(f'Fallback to `{quality}` quality ...')

            return torrent

        target_quality = preferred_qualities[0]
        self.log_debug(f'Trying to get torrent in `{target_quality}` quality ...')

        return available_torrents[target_quality]

    def _find_available_torrents(self, url: str) -> dict[str, dict]:
        """Returns available torrents indexed by sanitized quality string.

        :param url: url to a release page

        """
        code = self.extract_release_code(url)

        release = self.api_get_release_by_code(code)

        if not release:
            self.log_error(f'Failed to get release `{code}` from API')
            return {}

        self._release = release

        torrents = release.get('torrents') or []

        series2torrents = defaultdict(list)

        # A release can consist of several torrents: episode ranges (in different qualities),
        # recaps, trailers. We take episode ranges only.
        for torrent in torrents:

            matched = REGEX_RANGE.search(torrent.get('label') or '')

            if matched:
                series2torrents[matched.group(1)].append(torrent)

        if not series2torrents:
            return {}

        # Some releases are broken into several .torrent files, e.g. 1-20 and 21-41 — take the last one.
        latest_series = sorted(series2torrents, key=self.to_tuple, reverse=True)[0]

        available_torrents = {}

        for torrent in series2torrents[latest_series]:
            quality = self.sanitize_quality(f"{torrent['type']['value']} {torrent['quality']['value']}")
            available_torrents[quality] = torrent

        return available_torrents

    def find_available_qualities(self, url: str) -> dict[str, str]:
        """Returns available .torrent download links indexed by quality string.

        :param url: url to a release page

        """
        available_torrents = self._find_available_torrents(url)
        return {
            quality: f"{API_URL}/torrents/{torrent['hash']}/file"
            for quality, torrent in available_torrents.items()
        }

    @staticmethod
    def extract_release_code(url: str) -> str:
        """Extracts a release code (alias) from a release page URL.

        Handles both current and legacy URL formats:

            `https://anilibria.top/anime/releases/release/kabukichou-sherlock` -> 'kabukichou-sherlock'
            `https://www.anilibria.tv/release/kabukichou-sherlock.html` -> 'kabukichou-sherlock'

        :param url: url to a release page

        """
        code = url.rstrip('/').rsplit('/', 1)[-1]
        return code.removesuffix('.html')

    @staticmethod
    def sanitize_quality(quality_str: str | None) -> str:
        """Turn passed quality_str into common format in order to simplify comparison.

        Examples:

            * `sanitize_quality('WEBRip 1080p')` -> 'webrip1080p'
            * `sanitize_quality('WEBRip-1080p')` -> 'webrip1080p'
            * `sanitize_quality('WEBRip_1080p')` -> 'webrip1080p'
            * `sanitize_quality('')` -> ''
            * `sanitize_quality(None)` -> ''

        :param quality_str:

        """
        if quality_str:
            return REGEX_NON_WORD.sub('', quality_str).lower()

        return ''

    @staticmethod
    def to_tuple(range_str: str) -> tuple[int, ...]:
        """Turn passed range_str into tuple of integers.

        Examples:

            * `to_tuple('1-10')` -> (1, 10)

        :param range_str: series range string

        """
        return tuple(map(int, range_str.split('-')))

    def api_get_release_by_code(self, code: str) -> dict:
        """Gets release data by its code from the API.

        :param code: release code

        """
        response = self.get_response(f'{API_URL}/releases/{code}', as_soup=False)

        if not response:
            return {}

        return response.json()
