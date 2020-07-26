import logging
from typing import List

from ..base_tracker import GenericPrivateTracker
from ..utils import TrackerClassesRegistry

LOGGER = logging.getLogger(__name__)


class NNMClubTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://nnm-club.me tracker."""

    alias: str = 'nnm-club.me'
    login_url: str = 'https://%(domain)s/forum/login.php'
    auth_qs_param_name: str = 'sid'
    mirrors: List[str] = ['nnm-club.name', 'nnmclub.to']

    test_urls: List[str] = [
        'http://nnm-club.me/forum/viewtopic.php?t=786946',
    ]

    def get_login_form_data(self, login: str, password: str) -> dict:
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password, 'autologin': 1, 'redirect': '', 'login': 'pushed'}

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_response(
            url, referer=url, cookies=self.cookies, query_string=self.get_auth_query_string(), as_soup=True
        )

        download_link = self.find_links(url, page_soup, definite=r'download\.php')

        if download_link is None:

            LOGGER.debug('Login is required to download torrent file')
            domain = self.extract_domain(url)

            if self.login(domain):
                download_link = self.get_download_link(url)

        return download_link or ''


# With that one we tell torrt to handle links to `nnm-club.me` domain with NNMClubTracker class.
TrackerClassesRegistry.add(NNMClubTracker)
