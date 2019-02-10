import logging
import re
from datetime import datetime
from functools import partial
from itertools import chain

import requests
from six.moves.urllib.parse import urlparse, urljoin, parse_qs

from torrt.exceptions import TorrtException
from torrt.utils import parse_torrent, make_soup, encode_value, WithSettings, TrackerObjectsRegistry, dump_contents

LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
REQUEST_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')


class BaseTracker(WithSettings):
    """Base torrent tracker handler class offering helper methods for its ancestors."""

    config_entry_name = 'trackers'

    alias = None
    """Tracker alias. Usually main tracker domain. See also `mirrors` attribute."""

    mirrors = []
    """List of mirror domain names."""

    encoding = None
    """Tracker html page encoding (cp1251 or other)."""

    def __init__(self):
        self.mirror_picked = None

    def encode_value(self, value):
        """Encodes a value.

        :param str|unicode value:
        :param str|unicode encoding: Encoding charset.
        :rtype: bytes

        """
        return encode_value(value, self.encoding)

    def pick_mirror(self, url):
        """Probes mirrors (domains) one by one and chooses one whick is available to use.

        :param str url:
        :rtype: str
        """
        mirror_picked = self.mirror_picked

        if mirror_picked is None:
            LOGGER.debug('Picking a mirror ...')

            original_domain = self.extract_domain(url)
            mirror_picked = original_domain

            for mirror_domain in self.mirrors:
                mirror_url = '%s://%s' % (self.extract_scheme(url), mirror_domain)

                LOGGER.debug('Probing mirror: `%s` ...', mirror_url)

                try:
                    response = requests.get(mirror_url)

                except requests.exceptions.RequestException as e:
                    continue

                if response.url.startswith(mirror_url):
                    mirror_picked = mirror_domain
                    break

            self.mirror_picked = mirror_picked

        return mirror_picked

    def get_mirrored_url(self, url):
        """Returns a mirrored URL for a given one.

        :param str url:
        :rtype: str
        """
        mirror_picked = self.mirror_picked
        original_domain = self.extract_domain(url)
        url_mirror = url.replace(original_domain, mirror_picked)
        return url_mirror

    def register(self):
        """Adds this object into TrackerObjectsRegistry.

        :return:
        """
        TrackerObjectsRegistry.add(self)

    @classmethod
    def can_handle(cls, string):
        """Returns boolean whether this tracker can handle torrent from string.

        :param str string: String, describing torrent. E.g. URL from torrent comment.
        :rtype: bool
        """
        for domain in chain([cls.alias], cls.mirrors):
            if domain in string:
                return True
        return False

    @classmethod
    def extract_scheme(cls, url):
        """Extracts scheme from a given URL.

        :param str url:
        :rtype: str
        """
        return urlparse(url).scheme

    @classmethod
    def extract_domain(cls, url):
        """Extracts domain from a given URL.

        :param str url:
        :rtype: str
        """
        return urlparse(url).netloc

    def get_response(self, url, form_data=None, allow_redirects=True,
                     referer=None, cookies=None, query_string=None, as_soup=False):
        """Returns an HTTP resource object from given URL.

        If a dictionary is passed in `form_data` POST HTTP method
        would be used to pass data to resource (even if that dictionary is empty).

        :param url: str - URL to get data from
        :param form_data: dict - data for POST
        :param allow_redirects: bool - whether to follow server redirects
        :param referer: str or None - data to put into Referer header
        :param cookies: dict or None - cookies to use
        :param query_string: str or None - query string (GET parameters) to add to URL
        :param as_soup: bool - whether to return BeautifulSoup object instead of Requests response
        :return: object
        :rtype: Response or BeautifulSoup
        """
        if query_string is not None:
            delim = '?'
            if '?' in url:
                delim = '&'
            url = '%s%s%s' % (url, delim, query_string)

        self.pick_mirror(url)

        url = self.get_mirrored_url(url)

        LOGGER.debug('Fetching %s ...', url)

        headers = {'User-agent': REQUEST_USER_AGENT}

        if referer is not None:
            headers['Referer'] = referer

        r_kwargs = {
            'allow_redirects': allow_redirects,
            'headers': headers,
            'timeout': REQUEST_TIMEOUT,
        }

        if cookies is not None:
            r_kwargs['cookies'] = cookies

        if form_data is not None:
            method = partial(requests.post, data=form_data, **r_kwargs)
        else:
            method = partial(requests.get, **r_kwargs)

        result = None
        try:
            result = method(url)

            if as_soup:
                result = self.make_page_soup(result.text)

            dump_contents('%s_%s.html' % (self.__class__.__name__, datetime.now()), contents=result)

            return result

        except requests.exceptions.RequestException as e:
            LOGGER.error('Failed to get resource from `%s`: %s', getattr(result, 'url', url), e.message)
            return None

    @classmethod
    def make_page_soup(cls, html):
        """Returns BeautifulSoup object from a html.

        :param html: str
        :return: object
        :rtype: BeautifulSoup
        """
        return make_soup(html)

    @classmethod
    def find_links(cls, url, page_soup, definite=None):
        """Returns a list with hyperlinks found in supplied page_soup
        or a definite link.

        :param url: str - page URL
        :param page_soup: BeautifulSoup - page soup
        :param definite: str - regular expression to match link
        :return: list or str
        :rtype: list or str
        """
        if not page_soup:
            return None if definite else []

        if definite is not None:
            link = page_soup.find(href=re.compile(definite))

            if link:
                return cls.expand_link(url, link.get('href'))

            return link

        else:
            links = []

            for link in page_soup.find_all('a'):
                href = link.get('href')

                if href:
                    links.append(cls.expand_link(url, href))

            return links

    @classmethod
    def expand_link(cls, base_url, link):
        """Expands a given relative link using base URL if required.

        :param base_url: str
        :param link: str - absolute or relative link
        :return: str
        :rtype: str
        """
        if not link.startswith('http'):
            link = urljoin(base_url, link)
        return link

    def test_configuration(self):
        """This should implement a configuration test, e.g. make test login and report success.

        :return: bool
        """
        return True

    def get_torrent(self, url):
        """This method should be implemented in torrent tracker handler class
        and must return .torrent file contents.

        :param url: str - URL to download torrent file from
        :return: str - torrent file contents
        :rtype: str
        """
        raise NotImplementedError('`%s` class should implement `get_torrent_file()` method' % self.__class__.__name__)


class GenericTracker(BaseTracker):
    """Generic torrent tracker handler class implementing most common tracker handling methods."""

    def get_id_from_link(self, url):
        """Returns forum thread identifier from full thread URL.

        :param url: str
        :return: str
        :rtype: str
        """
        return url.split('=')[1]

    def get_torrent(self, url):
        """This is the main method which returns torrent file contents
        of file located at URL.

        :param url: str - URL to find and get torrent from
        :return: str or None - torrent file contents
        :rtype: str or None
        """
        torrent_data = None
        download_link = self.get_download_link(url)

        if download_link is None:
            LOGGER.error('Cannot find torrent file download link at %s', url)

        else:
            LOGGER.debug('Torrent download link found: %s', download_link)

            torrent_data = self.download_torrent(download_link, referer=url)

            if torrent_data is None:
                LOGGER.debug('Torrent download from `%s` has failed', download_link)
            else:
                torrent_data = parse_torrent(torrent_data)

        return torrent_data

    def get_download_link(self, url):
        """Tries to find .torrent file download link on page and return it.

        :param url: str - URL to find a download link at.
        :return: str or None
        :rtype: str or None
        """
        raise NotImplementedError('`%s` class should implement `get_download_link()` method' % self.__class__.__name__)

    def download_torrent(self, url, referer=None):
        """Returns .torrent file contents from the given URL.

        :param url: str - torrent file URL
        :param referer: str or None - Referer header value
        :return: str or None
        :rtype: str or None
        """
        raise NotImplementedError('`%s` class should implement `download_torrent()` method' % self.__class__.__name__)


class GenericPublicTracker(GenericTracker):
    """Generic torrent tracker handler class implementing most common handling methods for public trackers."""

    login_required = False

    def get_id_from_link(self, url):
        return url.split('/')[-1]

    def download_torrent(self, url, referer=None):
        LOGGER.debug('Downloading torrent file from %s ...', url)
        # That was a check that user himself visited torrent's page ;)
        response = self.get_response(url, referer=referer)
        return getattr(response, 'content', None)


class GenericPrivateTracker(GenericPublicTracker):
    """Generic torrent tracker handler class implementing most common handling methods
    for private trackers (that require user registration).

    """

    login_required = True

    login_url = None
    """URL where with login form.
    This can include `%(domain)s` marker in place of a domain name when domain mirrors are used
    (see `mirrors` attribute of BaseTracker).

    """

    # Cookie name to verify that a log in was successful.
    auth_cookie_name = None
    # HTTP GET (query string) parameter name to verify that a log in was successful. Probably session ID.
    auth_qs_param_name = None

    def __init__(self, username=None, password=None, cookies=None, query_string=None):
        super(GenericPrivateTracker, self).__init__()

        self.logged_in = False
        # Stores a number of login attempts to prevent recursion.
        self.login_counter = 0

        self.username = username
        self.password = password

        if cookies is None:
            cookies = {}

        self.cookies = cookies
        self.query_string = query_string

    def get_encode_form_data(self, data):
        """Encode dictionary from get_login_form_data using Tracker page encoding.

        :param dict data: :rtype: dict
        """
        return {key: self.encode_value(value) for key, value in data.items()}

    def get_login_form_data(self, login, password):
        """Should return a dictionary with data to be pushed to authorization form.

        :param login:
        :param password:
        :return: dict
        :rtype: dict
        """
        return {'username': login, 'password': password}

    def test_configuration(self):
        return self.login(self.alias)

    def login(self, domain):
        """Implements tracker login procedure.
        Returns success bool.

        :return: bool
        :rtype: bool
        """
        login_url = self.login_url % {'domain': domain}
        LOGGER.debug('Trying to login at %s ...', login_url)

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

        form_data = self.get_login_form_data(self.username, self.password)
        form_data = self.get_encode_form_data(form_data)

        response = self.get_response(
            login_url, form_data,
            allow_redirects=allow_redirects, cookies=self.cookies
        )

        if not response:  # e.g. Connection aborted.
            return False

        # Login success checks.
        parsed_qs = parse_qs(urlparse(response.url).query)
        if self.auth_cookie_name in response.cookies or self.auth_qs_param_name in parsed_qs:
            self.logged_in = True

            if parsed_qs:
                self.query_string = parsed_qs[self.auth_qs_param_name][0]
            self.cookies = response.cookies

            # Save auth info to config.
            self.save_settings()
            LOGGER.debug('Login is successful')
        else:
            LOGGER.warning('Login with given credentials failed')

        return self.logged_in

    def before_download(self, url):
        """Used to perform some required actions right before .torrent download.
        E.g.: to set a sentinel cookie that allows the download.

        :param url: str - torrent file URL
        :return:
        """
        return None

    def get_auth_query_string(self):
        """Returns an auth query string to be passed to get_response()
        for auth purposes.

        :return: auth string, e.g. sid=1234567890
        :rtype: str
        """
        query_string = None
        if self.auth_qs_param_name:
            query_string = '%s=%s' % (self.auth_qs_param_name, self.query_string)
        return query_string

    def download_torrent(self, url, referer=None):
        LOGGER.debug('Downloading torrent file from %s ...', url)

        self.before_download(url)

        response = self.get_response(
            url,
            cookies=self.cookies,
            query_string=self.get_auth_query_string(),
            referer=referer
        )

        return getattr(response, 'content', None)


class TorrtTrackerException(TorrtException):
    """Base torrt tracker exception. All other tracker related exception should inherit from that."""
