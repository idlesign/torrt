from datetime import datetime
from typing import List, Optional

from ..base_tracker import GenericPrivateTracker


class EniaHDTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for https://eniahd.com tracker."""

    alias: str = 'eniahd.com'
    login_url: str = 'https://%(domain)s/login.php'
    auth_cookie_name: str = 'bb_data'
    mirrors: List[str] = ['eniahd.com', 'eniatv.com']

    test_urls: List[str] = [
        'https://eniatv.com/viewtopic.php?t=1558',
    ]

    def get_login_form_data(self, login: str, password: str) -> dict:
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'login_username': login, 'login_password': password, 'autologin': 1, 'redirect': '', 'login': 'Вход'}

    def extract_page_cover(self) -> str:
        attrs = getattr(self._torrent_page.select_one('var.postImg'), 'attrs', {})
        title = attrs.get('title')

        if not title:
            return super().extract_page_cover()

        return title

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_torrent_page(url)

        download_link = self.find_links(url, page_soup, definite=r'dl\.php')

        if download_link is None:

            self.log_debug('Login is required to download torrent file')
            domain = self.extract_domain(url)

            if self.login(domain):
                download_link = self.get_download_link(url)

        return download_link or ''
