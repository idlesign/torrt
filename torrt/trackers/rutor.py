import logging
from typing import List

from ..base_tracker import GenericPublicTracker
from ..utils import TrackerClassesRegistry

LOGGER = logging.getLogger(__name__)


class RutorTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for http://rutor.info tracker."""

    alias: str = 'rutor.org'
    mirrors: List[str] = ['rutor.is', 'rutor.info', 'new-rutor.org']

    def __init__(self, cookies: dict = None):

        super(RutorTracker, self).__init__()

        if cookies is None:
            cookies = {}

        self.cookies = cookies

    def get_id_from_link(self, url: str) -> str:
        """Returns forum thread identifier from full thread URL."""
        splitted = url.rstrip('/').split('/')

        result = splitted[-1]

        if not result.isdigit():  # URL contains SEO name in the last chunk
            result = splitted[-2]

        return result

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        response = self.get_response(url, cookies=self.cookies)

        page_soup = self.make_page_soup(response.text)
        expected_link = f'/download/{self.get_id_from_link(url)}'
        download_link = self.find_links(url, page_soup, definite=expected_link)

        return download_link or ''


TrackerClassesRegistry.add(RutorTracker)
