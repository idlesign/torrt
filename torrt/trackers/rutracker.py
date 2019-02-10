import logging

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)


class RuTrackerTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://rutracker.org tracker."""

    alias = 'rutracker.org'
    login_url = 'https://%(domain)s/forum/login.php'
    auth_cookie_name = 'bb_session'
    mirrors = ['rutracker.org', 'rutracker.net', 'maintracker.org']
    encoding = 'cp1251'

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def get_login_form_data(self, username, password):
        """Returns a dictionary with data to be pushed to authorization form."""
        return {'login_username': username, 'login_password': password, 'login': 'pushed', 'redirect': 'index.php'}

    def before_download(self, url):
        """Used to perform some required actions right before .torrent download."""
        self.cookies['bb_dl'] = self.get_id_from_link(url)  # A check that user himself have visited torrent's page ;)

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        page_soup = self.get_response(
            url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True
        )

        domain = self.extract_domain(url)

        is_anonymous = self.find_links(url, page_soup, 'register') is not None
        if is_anonymous:
            self.login(domain)
            page_soup = self.get_response(
                url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True
            )
        download_link = self.find_links(url, page_soup, 'dl\.php')
        self.form_token = self.get_form_token(page_soup)
        return download_link

    def get_form_token(self, page_soup):
        form_token_lines = [line for line in page_soup.text.split('\n\t') if line.startswith('form_token')]
        try:
            return form_token_lines[0].split(':')[1][2:-2]
        except IndexError:
            return

    def download_torrent(self, url, referer=None):
        LOGGER.debug('Downloading torrent file from %s ...', url)
        self.before_download(url)
        # rutracker require POST action to download torrent file
        if self.form_token:
            form_data = {'form_token': self.form_token}
        else:
            form_data = None
        response = self.get_response(
            url, form_data=form_data, cookies=self.cookies, query_string=self.get_auth_query_string(), referer=referer
        )
        if response is None:
            return None
        return response.content

# With that one we tell torrt to handle links to `rutracker.org` domain with RutrackerHandler class.
TrackerClassesRegistry.add(RuTrackerTracker)
