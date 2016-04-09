import logging

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)


class NNMClubTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://nnm-club.me tracker."""

    alias = 'nnm-club.me'
    login_url = 'http://%(domain)s/forum/login.php'
    auth_qs_param_name = 'sid'
    mirrors = ['nnmclub.to']

    def get_login_form_data(self, login, password):
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password, 'autologin': 1, 'redirect': '', 'login': 'pushed'}

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        page_soup = self.get_response(
            url, referer=url, cookies=self.cookies, query_string=self.get_auth_query_string(), as_soup=True
        )
        download_link = self.find_links(url, page_soup, definite='download\.php')

        if download_link is None:
            LOGGER.debug('Login is required to download torrent file')
            domain = self.extract_domain(url)
            if self.login(domain):
                download_link = self.get_download_link(url)

        return download_link


# With that one we tell torrt to handle links to `nnm-club.me` domain with NNMClubTracker class.
TrackerClassesRegistry.add(NNMClubTracker)
