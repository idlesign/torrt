import re
import logging

from torrt.base_tracker import GenericPublicTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)

RE_DDOS_GRUARD_COOKIES_STR = re.compile("document.cookie='([^;]+)", re.I | re.U)


class RutorTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for http://rutor.org tracker."""

    alias = 'rutor.org'
    test_url = 'http://rutor.org/'
    mirrors = ['new-rutor.org']

    def __init__(self, cookies=None):
        if cookies is None:
            cookies = {}
        self.cookies = cookies

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL."""
        splitted = url.split('/')
        result = splitted[-1]
        if result.isalnum:  # URL contains SEO name in the last chunk
            result = splitted[-2]
        return result

    def break_ddos_guard(self, html):
        match = RE_DDOS_GRUARD_COOKIES_STR.search(html)
        if match:
            LOGGER.debug('DDoS protection detected')
            ddn_cookie = match.group(1).split('=')
            self.cookies[ddn_cookie[0]] = ddn_cookie[1]
            self.save_settings()
            return True
        return False

    def test_configuration(self):
        response = self.get_response(self.test_url)
        return self.break_ddos_guard(response.text)

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        response = self.get_response(url, cookies=self.cookies)
        if self.break_ddos_guard(response.text):
            response = self.get_response(url, cookies=self.cookies)

        page_soup = self.make_page_soup(response.text)
        expected_link = 'd.rutor.org/download/%s' % self.get_id_from_link(url)
        download_link = self.find_links(url, page_soup, definite=expected_link)

        return download_link


TrackerClassesRegistry.add(RutorTracker)
