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
        divs = page_soup.select('div.download-torrent')
        for div in divs:
            quality_span = div.select('div.torrent-first-col > span')
            quality_str = quality_span[0].text.strip()
            match = REGEX_QUALITY.search(quality_str)
            if match:
                quality = match.group(1)
                link = self.expand_link(url, div.select('div.torrent-fourth-col a.torrent-download-link')[0]['href'])
                available_qualities[quality] = link
            else:
                LOGGER.warning('Cannot extract quality from `%s`', quality_str)

        LOGGER.debug('Available in qualities: %s', ', '.join(available_qualities.keys()))

        if available_qualities:
            preferred_qualities = [quality for quality in self.quality_prefs if quality in available_qualities]
            if not preferred_qualities:
                LOGGER.debug('Torrent is not available in preferred qualities: %s', ', '.join(self.quality_prefs))
            else:
                target_quality = preferred_qualities[0]
                LOGGER.debug('Trying to get torrent in `%s` quality ...', target_quality)

                return available_qualities[target_quality]

        return None


TrackerClassesRegistry.add(AnilibriaTracker)
