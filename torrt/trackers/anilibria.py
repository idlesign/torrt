import logging
import re
from collections import defaultdict

from torrt.base_tracker import GenericPublicTracker
from torrt.utils import TrackerClassesRegistry

LOGGER = logging.getLogger(__name__)

REGEX_QUALITY = re.compile(r".+\[(.+)\]")
# This regex is used to remove every non-word character or underscore from quality string.
REGEX_NON_WORD = re.compile(r'[\W_]')
REGEX_RANGE = re.compile(r'\d+-\d+')

HOST = 'https://www.anilibria.tv'
API_URL = HOST + '/public/api/index.php'


class AnilibriaTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for https://www.anilibria.tv tracker."""

    alias = 'anilibria.tv'

    test_urls = [
        'https://www.anilibria.tv/release/sword-art-online-alicization.html',
    ]

    def __init__(self, quality_prefs=None):
        super(AnilibriaTracker, self).__init__()
        if quality_prefs is None:
            quality_prefs = ['HDTVRip 1080p', 'HDTVRip 720p', 'WEBRip 720p']
        self.quality_prefs = quality_prefs

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        available_qualities = self.find_available_qualities(url)

        LOGGER.debug('Available in qualities: %s', ', '.join(available_qualities.keys()))

        if available_qualities:
            quality_prefs = []
            for pref in self.quality_prefs:
                pref = self.sanitize_quality(pref)
                if pref not in quality_prefs:
                    quality_prefs.append(pref)

            preferred_qualities = [quality for quality in quality_prefs if quality in available_qualities]
            if not preferred_qualities:
                LOGGER.info('Torrent is not available in preferred qualities: %s', ', '.join(quality_prefs))
                quality, link = next(iter(available_qualities.items()))
                LOGGER.info('Fallback to `%s` quality ...', quality)
                return link
            else:
                target_quality = preferred_qualities[0]
                LOGGER.debug('Trying to get torrent in `%s` quality ...', target_quality)

                return available_qualities[target_quality]

        return None

    def find_available_qualities(self, url):
        """
        Tries to find .torrent download links in `Release` model
        :param url: str - url to forum thread page
        :return: dict where key is quality and value is .torrent download link
        """
        code = self.extract_release_code(url)
        response = self.get_response(API_URL, {'query': 'release', 'code': code}, as_soup=False)
        json = response.json()

        if not json.get('status', False):
            LOGGER.error('Failed to get release `%s` from API', code)
            return {}

        available_qualities = {}
        torrents = json['data']['torrents']
        series2torrents = defaultdict(list)
        for torrent in torrents:
            if REGEX_RANGE.match(torrent['series']):  # filter out single-file torrents like trailers,...
                series2torrents[torrent['series']].append(torrent)

        # some releases can be broken into several .torrent files, e.g. 1-20 and 21-41 - take the last one
        sorted_series = sorted(series2torrents.keys(), reverse=True)
        for torrent in series2torrents[sorted_series[0]]:
            quality = self.sanitize_quality(torrent['quality'])
            available_qualities[quality] = HOST + torrent['url']

        return available_qualities

    @staticmethod
    def extract_release_code(url):
        """
        Extracts anilibria release code from forum thread page
        Example:

        `extract_release_code('https://www.anilibria.tv/release/kabukichou-sherlock.html')` -> 'kabukichou-sherlock'

        :param url: str - url to forum thread page
        :rtype: str
        :return: release code
        """
        return url.replace(HOST + '/release/', '').replace('.html', '')

    @staticmethod
    def sanitize_quality(quality_str):
        """
        Turn passed quality_str into common format in order to simplify comparison.
        Examples:

        * `sanitize_quality('WEBRip 1080p')` -> 'webrip1080p'
        * `sanitize_quality('WEBRip-1080p')` -> 'webrip1080p'
        * `sanitize_quality('WEBRip_1080p')` -> 'webrip1080p'
        * `sanitize_quality('')` -> ''
        * `sanitize_quality(None)` -> ''

        :type quality_str: Optional[str]
        :param quality_str: originally extracted quality string with non-word characters
        :return: quality string without non-word characters in lower-case
        """
        if quality_str:
            return REGEX_NON_WORD.sub('', quality_str).lower()
        return ''


TrackerClassesRegistry.add(AnilibriaTracker)
