import re
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from ..base_tracker import GenericPublicTracker

REGEX_QUALITY = re.compile(r".+\[(.+)\]")
# This regex is used to remove every non-word character or underscore from quality string.
REGEX_NON_WORD = re.compile(r'[\W_]')
REGEX_RANGE = re.compile(r'\d+-\d+')

HOST: str = 'https://www.anilibria.tv'
API_URL: str = HOST + '/public/api/index.php'


class AnilibriaTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for https://www.anilibria.tv tracker."""

    alias: str = 'anilibria.tv'

    test_urls: List[str] = [
        'https://www.anilibria.tv/release/sword-art-online-alicization.html',
    ]

    def __init__(self, quality_prefs: List[str] = None):

        super(AnilibriaTracker, self).__init__()

        if quality_prefs is None:
            quality_prefs = ['HDTVRip 1080p', 'HDTVRip 720p', 'WEBRip 720p']

        self.quality_prefs = quality_prefs

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        available_qualities = self.find_available_qualities(url)

        self.log_debug(f"Available in qualities: {', '.join(available_qualities)}")

        if available_qualities:

            quality_prefs = []

            for pref in self.quality_prefs:
                pref = self.sanitize_quality(pref)

                if pref not in quality_prefs:
                    quality_prefs.append(pref)

            preferred_qualities = [quality for quality in quality_prefs if quality in available_qualities]

            if not preferred_qualities:
                self.log_info(
                    'Torrent is not available in preferred qualities: '
                    f"{', '.join(quality_prefs)}")

                quality, link = next(iter(available_qualities.items()))

                self.log_info(f'Fallback to `{quality}` quality ...')

                return link

            else:
                target_quality = preferred_qualities[0]
                self.log_debug(f'Trying to get torrent in `{target_quality}` quality ...')

                return available_qualities[target_quality]

        return ''

    def find_available_qualities(self, url: str) -> Dict[str, str]:
        """Tries to find .torrent download links in `Release` model
        Returns a dict where key is quality and value is .torrent download link.

        :param url: url to forum thread page

        """
        code = self.extract_release_code(url)

        json = self.api_get_release_by_code(code)

        if not json.get('status', False):
            self.log_error(f'Failed to get release `{code}` from API')
            return {}

        available_qualities = {}
        torrents = json['data']['torrents']
        series2torrents = defaultdict(list)
        # a release can consist of several torrents:
        #   1. episode ranges (different qualities),
        #   2. single episodes (different qualities) - a release is just aired,
        #   3. trailers,
        #   4. OVAs
        # we are trying to recognize `1` and `2`.
        for torrent in torrents:
            if REGEX_RANGE.match(torrent['series']) or torrent['series'] == json['data']['series']:
                series2torrents[torrent['series']].append(torrent)

        # some releases can be broken into several .torrent files, e.g. 1-20 and 21-41 - take the last one
        sorted_series = sorted(series2torrents.keys(), key=self.to_tuple, reverse=True)

        if not sorted_series:
            return {}

        for torrent in series2torrents[sorted_series[0]]:
            quality = self.sanitize_quality(torrent['quality'])
            available_qualities[quality] = HOST + torrent['url']

        return available_qualities

    @staticmethod
    def extract_release_code(url: str) -> str:
        """Extracts anilibria release code from forum thread page.

        Example:

        `extract_release_code('https://www.anilibria.tv/release/kabukichou-sherlock.html')` -> 'kabukichou-sherlock'

        :param url: url to forum thread page

        """
        return url.replace(HOST + '/release/', '').replace('.html', '')

    @staticmethod
    def sanitize_quality(quality_str: Optional[str]) -> str:
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
    def to_tuple(range_str: str) -> Tuple[int, ...]:
        """ Turn passed range_str into tuple of integers.

        Examples:

            * `to_tuple('1-10')` -> (1, 10)

        :param range_str: series range string

        """
        return tuple(map(int, range_str.split('-')))

    def api_get_release_by_code(self, code: str) -> dict:
        """
        Get release json by passed `code` from Anilibria API.

        :param code: release code

        """
        response = self.get_response(API_URL, {'query': 'release', 'code': code}, as_soup=False)

        if not response:
            return {}

        return response.json()
