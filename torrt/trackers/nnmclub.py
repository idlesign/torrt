import logging

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)


class NNMClubTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://nnm-club.me tracker."""

    alias = 'nnm-club.me'
    login_url = 'http://nnm-club.me/forum/login.php'
    auth_qs_param_name = 'sid'

    def get_login_form_data(self, login, password):
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password, 'autologin': 1, 'redirect': '', 'login': 'pushed'}

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        page_soup = self.get_response(url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True)
        page_links = self.find_links(url, page_soup)
        download_link = None

        register_links = 0

        for page_link in page_links:

            if 'profile.php?mode=register' in page_link:
                register_links += 1

                if register_links > 1:
                    download_link = None
                    LOGGER.info('Login is required to download torrent file')
                    if self.login():
                        download_link = self.get_download_link(url)
                        break

            elif 'download.php' in page_link:
                download_link = page_link
                break

        return download_link


# With that one we tell torrt to handle links to `nnm-club.me` domain with NnmclubHandler class.
TrackerClassesRegistry.add(NNMClubTracker)
