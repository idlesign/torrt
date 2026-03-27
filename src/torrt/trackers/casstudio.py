from typing import List

from ..base_tracker import GenericPrivateTracker


class CasstudioTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for https://casstudio.tv/ tracker."""

    alias: str = 'casstudio.tv'
    login_url: str = 'https://%(domain)s/ucp.php?mode=login'
    auth_cookie_name: str = 'phpbb3_lawmj_sid'
    auth_qs_param_name: str = 'mode'
    mirrors = ['casstudio.tk']

    test_urls: List[str] = ['https://casstudio.tv/viewtopic.php?t=1222']

    def get_login_form_data(self, login: str, password: str) -> dict:

        index_page = self.get_response(url=(self.login_url % {'domain': self.alias}))

        soup_response = self.make_page_soup(index_page.text)
        sid = soup_response.find(attrs={'name': 'sid'}).get('value')

        self.cookies = index_page.cookies
        self.login_url += f'&sid={sid}'

        result = {
            'username': login,
            'password': password,
            'autologin': 'on',
            'redirect': 'index.php',
            'sid': sid,
            'login': 'Вход',
        }

        return result

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        page_soup = self.get_torrent_page(url)

        domain = self.extract_domain(url)
        is_anonymous = self.find_links(url, page_soup, r'\./ucp\.php\?mode=login') is not None

        if not self.logged_in or is_anonymous:

            self.logged_in = False
            self.login(domain)

            page_soup = self.get_torrent_page(url, drop_cache=True)

        download_tag = page_soup.find('a', text='Скачать торрент')

        if download_tag:
            return self.expand_link(url, download_tag['href'])

        return ''
