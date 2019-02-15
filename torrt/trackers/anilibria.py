import logging
import re

from torrt.base_tracker import GenericPublicTracker
from torrt.utils import TrackerClassesRegistry

LOGGER = logging.getLogger(__name__)

REGEX_QUALITY = re.compile(r".+\[(.+)\]")


class AnilibriaTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for https://www.anilibria.tv tracker."""

    alias = 'anilibria.tv'

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
                quality = match.group(1)
                link = self.expand_link(url, row.select('td.torrentcol4 a.torrent-download-link')[0]['href'])
                available_qualities[quality] = link
            else:
                LOGGER.warning('Cannot extract quality from `%s`', quality_str)

        LOGGER.debug('Available in qualities: %s', ', '.join(available_qualities.keys()))

        if available_qualities:
            preferred_qualities = [quality for quality in self.quality_prefs if quality in available_qualities]
            if not preferred_qualities:
                LOGGER.info('Torrent is not available in preferred qualities: %s', ', '.join(self.quality_prefs))
                quality, link = next(iter(available_qualities.items()))
                LOGGER.info('Fallback to `%s` quality ...', quality)
                return link
            else:
                target_quality = preferred_qualities[0]
                LOGGER.debug('Trying to get torrent in `%s` quality ...', target_quality)

                return available_qualities[target_quality]

        return None


TrackerClassesRegistry.add(AnilibriaTracker)
