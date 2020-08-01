from typing import List

from ..base_tracker import GenericPrivateTracker


class KinozalTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://kinozal.tv/ tracker."""

    alias: str = 'kinozal.tv'
    login_url: str = 'https://%(domain)s/takelogin.php'
    auth_cookie_name: str = 'uid'
    mirrors: List[str] = ['kinozal-tv.appspot.com', 'kinozal.me']
    encoding: str = 'cp1251'

    def get_login_form_data(self, login: str, password: str) -> dict:
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password, 'returnto': ''}

    def get_id_from_link(self, url: str) -> str:
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_torrent_page(url)

        expected_link = rf'/download.+\={self.get_id_from_link(url)}'
        download_link = self.find_links(url, page_soup, definite=expected_link)

        return download_link or ''
