# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import six

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)


class CasstudioTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for https://casstudio.tv/ tracker."""

    alias = 'casstudio.tv'
    login_url = 'https://%(domain)s/ucp.php?mode=login'
    auth_cookie_name = 'phpbb3_lawmj_sid'
    auth_qs_param_name = 'mode'

    test_urls = ['https://casstudio.tv/viewtopic.php?t=1222']

    def get_login_form_data(self, login, password):
        index_page = self.get_response(url=(self.login_url % {'domain': self.alias}))
        soup_response = self.make_page_soup(index_page.text)
        sid = soup_response.find(attrs={'name': 'sid'}).get('value')
        self.cookies = index_page.cookies
        self.login_url += '&sid=%s' % sid
        return {'username': login, 'password': password, 'autologin': 'on',
                'redirect': 'index.php', 'sid': sid, 'login': six.u('Вход')}

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        page_soup = self.get_response(
            url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True
        )

        domain = self.extract_domain(url)
        is_anonymous = self.find_links(url, page_soup, r'\./ucp\.php\?mode=login') is not None

        if not self.logged_in or is_anonymous:
            self.logged_in = False
            self.login(domain)
            page_soup = self.get_response(
                url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True
            )
        download_tag = page_soup.find('a', text='Скачать торрент')
        if download_tag:
            return self.expand_link(url, download_tag['href'])


TrackerClassesRegistry.add(CasstudioTracker)
