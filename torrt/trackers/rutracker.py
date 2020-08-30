from typing import List, Optional

from ..base_tracker import GenericPrivateTracker, BeautifulSoup


class RuTrackerTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://rutracker.org tracker."""

    alias: str = 'rutracker.org'
    login_url: str = 'https://%(domain)s/forum/login.php'
    auth_cookie_name: str = 'bb_session'
    mirrors: List[str] = ['rutracker.org', 'rutracker.net', 'maintracker.org']
    encoding: str = 'cp1251'

    test_urls: List[str] = [
        'https://rutracker.org/forum/viewtopic.php?t=4430338',
    ]

    def get_id_from_link(self, url: str) -> str:
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def get_login_form_data(self, login: str, password: str) -> dict:
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'login_username': login, 'login_password': password, 'login': 'pushed', 'redirect': 'index.php'}

    def before_download(self, url: str):
        """Used to perform some required actions right before .torrent download."""
        self.cookies['bb_dl'] = self.get_id_from_link(url)  # A check that user himself have visited torrent's page ;)

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_torrent_page(url)

        domain = self.extract_domain(url)

        is_anonymous = self.find_links(url, page_soup, 'register') is not None

        if is_anonymous:
            self.login(domain)

            page_soup = self.get_torrent_page(url, drop_cache=True)

        download_link = self.find_links(url, page_soup, r'dl\.php')

        self.form_token = self.get_form_token(page_soup)

        return download_link or ''

    def get_form_token(self, page_soup: BeautifulSoup) -> Optional[str]:

        form_token_lines = [line for line in page_soup.text.split('\n\t') if line.startswith('form_token')]

        try:
            return form_token_lines[0].split(':')[1][2:-2]

        except IndexError:
            return

    def download_torrent(self, url: str, referer: str = None) -> Optional[bytes]:

        self.log_debug(f'Downloading torrent file from {url} ...')

        self.before_download(url)

        # rutracker requires POST action to download torrent file
        if self.form_token:
            form_data = {'form_token': self.form_token}

        else:
            form_data = None

        response = self.get_response(
            url,
            form_data=form_data,
            cookies=self.cookies,
            query_string=self.get_query_string(),
            referer=referer,
        )

        if response is None:
            return None

        return response.content
