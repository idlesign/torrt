import logging

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry

LOGGER = logging.getLogger(__name__)


class KinozalTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://kinozal.tv/ tracker."""

    alias = 'kinozal.tv'
    login_url = 'http://%(domain)s/takelogin.php'
    auth_cookie_name = 'uid'
    mirrors = ['kinozal.me']
    encoding = 'cp1251'

    def get_login_form_data(self, login, password):
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password, 'returnto': ''}

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""

        response = self.get_response(url, cookies=self.cookies)

        page_soup = self.make_page_soup(response.text)
        expected_link = '/download.+\=%s' % self.get_id_from_link(url)
        download_link = self.find_links(url, page_soup, definite=expected_link)
        return download_link


TrackerClassesRegistry.add(KinozalTracker)
