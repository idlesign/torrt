import re
import logging
from urlparse import urlparse, urljoin, parse_qs

import requests
from bs4 import BeautifulSoup

from torrt.utils import parse_torrent, WithSettings, TrackerObjectsRegistry, TorrtException


LOGGER = logging.getLogger(__name__)


class BaseTracker(WithSettings):
    """Base torrent tracker handler class offering helper methods for its ancestors."""

    alias = None
    config_entry_name = 'trackers'

    def register(self):
        TrackerObjectsRegistry.add(self)

    @classmethod
    def get_response(cls, url, form_data=None, allow_redirects=True, referer=None, cookies=None, query_string=None, as_soup=False):
        """Returns an HTTP resource data from given URL.
        If a dictionary is passed in `form_data` POST HTTP method
        would be used to pass data to resource (even if that dictionary is empty).

        """
        if query_string is not None:
            delim = '?'
            if '?' in url:
                delim = '&'
            url = '%s%s%s' % (url, delim, query_string)

        LOGGER.debug('Fetching %s ...' % url)

        headers = {'User-agent': 'Mozilla/5.0 (Ubuntu; X11; Linux i686; rv:8.0) Gecko/20100'}

        if referer is not None:
            headers['Referer'] = referer

        r_kwargs = {
            'allow_redirects': allow_redirects,
            'headers': headers
        }

        if cookies is not None:
            r_kwargs['cookies'] = cookies

        if form_data is not None:
            method = lambda: requests.post(url, data=form_data, **r_kwargs)
        else:
            method = lambda: requests.get(url, **r_kwargs)

        try:
            result = method()
            if as_soup:
                result = cls.make_page_soup(result.text)
            return result
        except requests.exceptions.RequestException as e:
            LOGGER.error('Failed to get resource from `%s`: %s' % (url, e.message))
            return None

    @classmethod
    def make_page_soup(cls, html):
        return BeautifulSoup(html)

    @classmethod
    def find_links(cls, url, page_soup, definite=None):
        """Returns a list with hyperlinks found in supplied html."""
        if definite is not None:
            link = page_soup.find(href=re.compile(definite))
            if link:
                return link.get('href')
            return link
        else:
            links = []
            for link in page_soup.find_all('a'):
                l = link.get('href')
                if l:
                    links.append(cls.expand_link(url, l))
            return links

    @classmethod
    def expand_link(cls, page_url, link):
        if not link.startswith('http'):
            link = urljoin(page_url, link)
        return link

    def test_configuration(self):
        return True

    def get_torrent(self, url):
        """This method should be implemented in torrent tracker handler class
        and must return .torrent file contents.

        ."""
        raise NotImplementedError('`%s` class should implement `get_torrent_file()` method' % self.__class__.__name__)


class GenericTracker(BaseTracker):
    """Generic torrent tracker handler class implementing most common tracker handling methods."""

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL."""
        return url.split('=')[1]

    def get_torrent(self, url):
        """This is the main method which returns torrent file contents."""
        torrent_data = None
        download_link = self.get_download_link(url)
        if download_link is None:
            LOGGER.error('Cannot find torrent file download link at %s' % url)
        else:
            LOGGER.debug('Torrent download link found: %s' % download_link)
            torrent_data = self.download_torrent(download_link, referer=url)
            if torrent_data is None:
                LOGGER.debug('Torrent download from `%s` has failed' % download_link)
            else:
                torrent_data = parse_torrent(torrent_data)
        return torrent_data

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        raise NotImplementedError('`%s` class should implement `get_download_link()` method' % self.__class__.__name__)

    def download_torrent(self, url, referer=None):
        """Returns .torrent file contents from the given URL."""
        raise NotImplementedError('`%s` class should implement `download_torrent()` method' % self.__class__.__name__)


class GenericPublicTracker(GenericTracker):
    """Generic torrent tracker handler class implementing most common handling methods for public trackers."""

    login_required = False

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL."""
        return url.split('/')[-1]

    def download_torrent(self, url, referer=None):
        """Returns .torrent file contents from the given URL."""
        LOGGER.debug('Downloading torrent file from %s ...' % url)
        # That was a check that user himself visited torrent's page ;)
        response = self.get_response(url, referer=referer)
        if response is None:
            return None
        return response.content


class GenericPrivateTracker(GenericPublicTracker):
    """Generic torrent tracker handler class implementing most common handling methods
    for private trackers (that require registration).

    """

    login_required = True
    login_url = None

    # Cookie name to verify that a log in was successful.
    auth_cookie_name = None
    # HTTP GET (query string) parameter name to verify that a log in was successful. Probably session ID.
    auth_qs_param_name = None

    def __init__(self, username=None, password=None, cookies=None, query_string=None):
        self.logged_in = False
        # Stores a number of login attempts to prevent recursion.
        self.login_counter = 0
        self.username = username
        self.password = password
        if cookies is None:
            cookies = {}
        self.cookies = cookies
        self.query_string = query_string

    def get_login_form_data(self, login, password):
        """Should return a dictionary with data to be pushed to authorization form."""
        return {'username': login, 'password': password}

    def test_configuration(self):
        return self.login()

    def login(self):
        """Implements tracker login procedure."""
        LOGGER.info('Trying to login at %s ...' % self.login_url)

        if self.logged_in:
            raise TorrtTrackerException('Consecutive login attempt detected at `%s`' % self.__class__.__name__)

        if not self.username or self.password is None:
            return False

        self.login_counter += 1

        # No recursion wanted.
        if self.login_counter > 1:
            return False

        allow_redirects = False  # Not to loose cookies on the redirect.
        if self.auth_qs_param_name:
            allow_redirects = True  # To be able to get Session ID from query string.

        response = self.get_response(self.login_url, self.get_login_form_data(self.username, self.password), allow_redirects=allow_redirects, cookies=self.cookies)

        # Login success checks.
        parsed_qs = parse_qs(urlparse(response.url).query)
        if self.auth_cookie_name in response.cookies or self.auth_qs_param_name in parsed_qs:
            self.logged_in = True

            if parsed_qs:
                self.query_string = parsed_qs[self.auth_qs_param_name][0]
            self.cookies = response.cookies

            # Save auth info to config.
            self.save_settings()
            LOGGER.info('Login is successful')
        else:
            LOGGER.warning('Login with given credentials failed')

        return self.logged_in

    def before_download(self, url):
        """Used to perform some required actions right before .torrent download.
        E.g.: to set a sentinel cookie that allows the download.

        """
        return True

    def download_torrent(self, url, referer=None):
        """Returns .torrent file contents from the given URL."""
        LOGGER.debug('Downloading torrent file from %s ...' % url)
        self.before_download(url)
        query_string = None
        if self.auth_qs_param_name:
            query_string = '%s=%s' % (self.auth_qs_param_name, self.query_string)
        response = self.get_response(url, cookies=self.cookies, query_string=query_string, referer=referer)
        if response is None:
            return None
        return response.content


class TorrtTrackerException(TorrtException):
    """"""

