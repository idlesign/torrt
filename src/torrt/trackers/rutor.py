from typing import List

from ..base_tracker import GenericPublicTracker


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
            for result in splitted:
                if result.isdigit():
                    break
        return result

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_torrent_page(url)

        expected_link = f'/download/{self.get_id_from_link(url)}'
        download_link = self.find_links(url, page_soup, definite=expected_link)

        return download_link or ''
