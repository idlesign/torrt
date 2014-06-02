import logging

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)


class RuTrackerTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://rutracker.org tracker."""

    alias = 'rutracker.org'
    login_url = 'http://login.rutracker.org/forum/login.php'
    auth_cookie_name = 'bb_data'

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def get_login_form_data(self, username, password):
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'login_username': username, 'login_password': password, 'login': 'pushed'}

    def before_download(self, url):
        """Used to perform some required actions right before .torrent download."""
        self.cookies['bb_dl'] = self.get_id_from_link(url)  # A check that user himself have visited torrent's page ;)

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        page_soup = self.get_response(url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True)
        page_links = self.find_links(url, page_soup)
        download_link = None
        for page_link in page_links:
            if 'dl.rutracker.org' in page_link:
                download_link = page_link
                if 'guest' in download_link:
                    download_link = None
                    LOGGER.info('Login is required to download torrent file')
                    if self.login():
                        download_link = self.get_download_link(url)
                break
        return download_link


# With that one we tell torrt to handle links to `rutracker.org` domain with RutrackerHandler class.
TrackerClassesRegistry.add(RuTrackerTracker)
