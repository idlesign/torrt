from datetime import datetime
from typing import ClassVar

import dateparser

from ..base_tracker import GenericPrivateTracker


class KinozalTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for kinozal.tv tracker."""

    alias: str = 'kinozal.tv'
    login_url: str = 'https://%(domain)s/takelogin.php'
    auth_cookie_name: str = 'uid'
    mirrors: ClassVar[list[str]] = ['kinozal-tv.appspot.com', 'kinozal.me']
    encoding: str = 'cp1251'

    def get_login_form_data(self, login: str, password: str) -> dict:
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password, 'returnto': ''}

    def get_id_from_link(self, url: str) -> str:
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def extract_page_date_updated(self) -> datetime | None:
        def refresh_in_text(tag):
            return tag.name == 'li' and tag.get_text().startswith('Обновлен')

        dt_val = getattr(self._torrent_page.find(refresh_in_text).find('span'), 'text', '').strip()
        return dateparser.parse(dt_val, languages=['ru'])

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_torrent_page(url)

        expected_link = rf'/download.+\={self.get_id_from_link(url)}'
        download_link = self.find_links(url, page_soup, definite=expected_link)

        return download_link or ''
