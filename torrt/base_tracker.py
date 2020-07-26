import logging
import re
from datetime import datetime
from functools import partial
from itertools import chain
from typing import List, Optional, Union
from urllib.parse import urlparse, urljoin, parse_qs

import requests
from bs4 import BeautifulSoup
from requests import Response

from .exceptions import TorrtTrackerException
from .utils import (
    parse_torrent, make_soup, encode_value, WithSettings, TrackerObjectsRegistry, dump_contents, TorrentData
)

LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
REQUEST_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')


class BaseTracker(WithSettings):
    """Base torrent tracker handler class offering helper methods for its ancestors."""

    config_entry_name: str = 'trackers'

    alias: str = None
    """Tracker alias. Usually main tracker domain. See also `mirrors` attribute."""

    mirrors: List[str] = []
    """List of mirror domain names."""

    encoding: Optional[str] = None
    """Tracker html page encoding (cp1251 or other)."""

    test_urls: List[str] = []
    """Page URLs for automatic tests of torrent extraction."""

    def __init__(self):
        self.mirror_picked: Optional[str] = None
        super().__init__()

    def encode_value(self, value: str) -> Union[bytes, str]:
        """Encodes a value.

        :param value:

        """
        return encode_value(value, self.encoding)

    def pick_mirror(self, url: str) -> str:
        """Probes mirrors (domains) one by one and chooses one whick is available to use.

        :param url:

        """
        mirror_picked = self.mirror_picked

        if mirror_picked is None:
            LOGGER.debug('Picking a mirror ...')

            original_domain = self.extract_domain(url)
            mirror_picked = original_domain

            for mirror_domain in self.mirrors:
                mirror_url = f'{self.extract_scheme(url)}://{mirror_domain}'

                LOGGER.debug(f'Probing mirror: `{mirror_url}` ...')

                try:
                    response = requests.get(mirror_url)

                except requests.exceptions.RequestException as e:
                    continue

                if response.url.startswith(mirror_url):
                    mirror_picked = mirror_domain
                    break

            self.mirror_picked = mirror_picked

        return mirror_picked

    def get_mirrored_url(self, url: str) -> str:
        """Returns a mirrored URL for a given one.

        :param url:

        """
        mirror_picked = self.mirror_picked
        original_domain = self.extract_domain(url)
        url_mirror = url.replace(original_domain, mirror_picked)
        return url_mirror

    def register(self):
        """Adds this object into TrackerObjectsRegistry."""

        TrackerObjectsRegistry.add(self)

    @classmethod
    def can_handle(cls, string: str) -> bool:
        """Returns boolean whether this tracker can handle torrent from string.

        :param string: String, describing torrent. E.g. URL from torrent comment.

        """
        for domain in chain([cls.alias], cls.mirrors):
            if domain in string:
                return True
        return False

    @classmethod
    def extract_scheme(cls, url: str) -> str:
        """Extracts scheme from a given URL.

        :param url:

        """
        return urlparse(url).scheme

    @classmethod
    def extract_domain(cls, url: str) -> str:
        """Extracts domain from a given URL.

        :param url:

        """
        return urlparse(url).netloc

    def get_response(
            self,
            url: str,
            form_data: dict = None,
            allow_redirects: bool = True,
            referer: str = None,
            cookies: dict = None,
            query_string: str = None,
            as_soup: bool = False

    ) -> Optional[Union[Response, BeautifulSoup]]:
        """Returns an HTTP resource object from given URL.

        If a dictionary is passed in `form_data` POST HTTP method
        would be used to pass data to resource (even if that dictionary is empty).

        :param url: URL to get data from

        :param form_data: data for POST

        :param allow_redirects: whether to follow server redirects

        :param referer: data to put into Referer header

        :param cookies: cookies to use

        :param query_string:  query string (GET parameters) to add to URL

        :param as_soup: whether to return BeautifulSoup object instead of Requests response

        """
        if query_string is not None:

            delim = '?'

            if '?' in url:
                delim = '&'

            url = f'{url}{delim}{query_string}'

        self.pick_mirror(url)

        url = self.get_mirrored_url(url)

        LOGGER.debug(f'Fetching {url} ...')

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

            dump_contents(f'{self.__class__.__name__}_{datetime.now()}.html', contents=result)

            return result

        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Failed to get resource from `{getattr(result, 'url', url)}`: {e}")
            return None

    @classmethod
    def make_page_soup(cls, html: str) -> BeautifulSoup:
        """Returns BeautifulSoup object from a html.

        :param html:

        """
        return make_soup(html)

    @classmethod
    def find_links(cls, url: str, page_soup: BeautifulSoup, definite: str = None) -> Union[Optional[str], List[str]]:
        """Returns a list with hyperlinks found in supplied page_soup
        or a definite link.

        :param url: page URL
        :param page_soup: page soup
        :param definite: regular expression to match link

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
    def expand_link(cls, base_url: str, link: str) -> str:
        """Expands a given relative link using base URL if required.

        :param base_url:
        :param link: absolute or relative link

        """
        if not link.startswith('http'):
            link = urljoin(base_url, link)

        return link

    def test_configuration(self) -> bool:
        """This should implement a configuration test, e.g. make test login and report success."""
        return True

    def get_torrent(self, url: str) -> Optional[TorrentData]:
        """This method should be implemented in torrent tracker handler class
        and must return .torrent file contents.

        :param url: URL to download torrent file from

        """
        raise NotImplementedError  # pragma: nocover


class GenericTracker(BaseTracker):
    """Generic torrent tracker handler class implementing most common tracker handling methods."""

    def get_id_from_link(self, url: str) -> str:
        """Returns forum thread identifier from full thread URL.

        :param url:

        """
        return url.split('=')[1]

    def get_torrent(self, url: str) -> Optional[TorrentData]:
        """This is the main method which returns torrent file contents
        of file located at URL.

        :param url: URL to find and get torrent from

        """
        download_link = self.get_download_link(url)

        if not download_link:
            LOGGER.error(f'Cannot find torrent file download link at {url}')
            return None

        LOGGER.debug(f'Torrent download link found: {download_link}')

        torrent_contents = self.download_torrent(download_link, referer=url)

        if torrent_contents is None:
            LOGGER.debug(f'Torrent download from `{download_link}` has failed')
            return None

        parsed = parse_torrent(torrent_contents)

        return TorrentData(
            url=url,
            url_file=download_link,
            parsed=parsed,
            raw=torrent_contents,
        )

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link on page and return it.

        :param url: URL to find a download link at.

        """
        raise NotImplementedError  # pragma: nocover

    def download_torrent(self, url: str, referer: str = None) -> bytes:
        """Returns .torrent file contents from the given URL.

        :param url: torrent file URL
        :param referer: Referer header value

        """
        raise NotImplementedError  # pragma: nocover


class GenericPublicTracker(GenericTracker):
    """Generic torrent tracker handler class implementing most common handling methods for public trackers."""

    login_required: bool = False

    def get_id_from_link(self, url: str) -> str:
        return url.split('/')[-1]

    def download_torrent(self, url: str, referer: str = None) -> Optional[bytes]:
        LOGGER.debug(f'Downloading torrent file from {url} ...')
        # That was a check that user himself visited torrent's page ;)
        response = self.get_response(url, referer=referer)
        return getattr(response, 'content', None)


class GenericPrivateTracker(GenericPublicTracker):
    """Generic torrent tracker handler class implementing most common handling methods
    for private trackers (that require user registration).

    """

    login_required: bool = True

    login_url: str = None
    """URL where with login form.
    This can include `%(domain)s` marker in place of a domain name when domain mirrors are used
    (see `mirrors` attribute of BaseTracker).

    """

    auth_cookie_name: str = None
    """Cookie name to verify that a log in was successful."""

    auth_qs_param_name: str = None
    """HTTP GET (query string) parameter name to verify that a log in was successful. Probably session ID."""

    def __init__(self, username: str = None, password: str = None, cookies: dict = None, query_string: str = None):
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

    def get_encode_form_data(self, data: dict) -> dict:
        """Encode dictionary from get_login_form_data using Tracker page encoding.

        :param dict data:

        """
        return {key: self.encode_value(value) for key, value in data.items()}

    def get_login_form_data(self, login: str, password: str) -> dict:
        """Should return a dictionary with data to be pushed to authorization form.

        :param login:
        :param password:

        """
        return {'username': login, 'password': password}

    def test_configuration(self) -> bool:
        return self.login(self.alias)

    def login(self, domain: str) -> bool:
        """Implements tracker login procedure. Returns success bool."""

        login_url = self.login_url % {'domain': domain}

        LOGGER.debug(f'Trying to login at {login_url} ...')

        if self.logged_in:
            raise TorrtTrackerException(f'Consecutive login attempt detected at `{self.__class__.__name__}`')

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

    def before_download(self, url: str):
        """Used to perform some required actions right before .torrent download.
        E.g.: to set a sentinel cookie that allows the download.

        :param url: torrent file URL

        """

    def get_auth_query_string(self) -> str:
        """Returns an auth query string to be passed to get_response()
        for auth purposes.

        :return: auth string, e.g. sid=1234567890

        """
        query_string = None

        if self.auth_qs_param_name:
            query_string = f'{self.auth_qs_param_name}={self.query_string}'

        return query_string

    def download_torrent(self, url: str, referer: str = None) -> Optional[bytes]:
        LOGGER.debug(f'Downloading torrent file from {url} ...')

        self.before_download(url)

        response = self.get_response(
            url,
            cookies=self.cookies,
            query_string=self.get_auth_query_string(),
            referer=referer
        )

        return getattr(response, 'content', None)
