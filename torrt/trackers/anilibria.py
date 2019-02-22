import logging
import re

from torrt.base_tracker import GenericPublicTracker
from torrt.utils import TrackerClassesRegistry

LOGGER = logging.getLogger(__name__)

REGEX_QUALITY = re.compile(r".+\[(.+)\]")
# This regex is used to remove every non-word character or underscore from quality string.
REGEX_NON_WORD = re.compile(r'[\W_]')


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
        page_soup = self.get_response(url, as_soup=True)

        available_qualities = {}
        rows = page_soup.select('#publicTorrentTable tr')
        for row in rows:
            quality_td = row.select('td.torrentcol1')
            quality_str = quality_td[0].text.strip()
            match = REGEX_QUALITY.search(quality_str)
            if match:
                quality = self.sanitize_quality(match.group(1))
                link = self.expand_link(url, row.select('td.torrentcol4 a.torrent-download-link')[0]['href'])
                available_qualities[quality] = link
            else:
                LOGGER.warning('Cannot extract quality from `%s`', quality_str)

        LOGGER.debug('Available in qualities: %s', ', '.join(available_qualities.keys()))

        if available_qualities:
            quality_prefs = {self.sanitize_quality(pref) for pref in self.quality_prefs}
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
