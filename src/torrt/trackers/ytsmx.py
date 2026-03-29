from typing import ClassVar

from bs4 import BeautifulSoup

from ..base_tracker import GenericPublicTracker
from ..exceptions import TorrtTrackerException

API_BASE = 'https://yts.bz/api/v2/'
QualityLinks = dict[str, str]
QualityLink = tuple[str, str]


class YtsmxTrackerException(TorrtTrackerException):
    """Yts.mx specific exceptions"""


class YtsmxTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for yts.mx tracker."""

    active: bool = False
    """Having 403 with js in responses. Requires investigation."""

    alias: str = 'yts.mx'
    mirrors: ClassVar[list[str]] = ['yts.mx', 'yts.bz', 'yts.lt']

    test_urls: ClassVar[list[str]] = [
        'https://yts.mx/movies/the-matrix-1999',
    ]

    def __init__(self, *, quality_prefs: list[str] | None = None, **kwargs):
        super().__init__()

        if quality_prefs is None:
            quality_prefs = ['1080P.WEB', '720P.WEB']
        else:
            quality_prefs = [self._sanitize_quality(pref) for pref in quality_prefs]

        self.quality_prefs = quality_prefs

    @staticmethod
    def _sanitize_quality(q: str) -> str:
        """sanitizes quality provided by configuration"""

        return q.strip().upper()

    @staticmethod
    def _get_quality_from_torrent(torrent: dict) -> str:
        """returns sanitized quality string from API's torrent dict"""

        return f"{torrent['quality']}.{torrent['type']}".upper()

    def _get_torrent_page(self, url: str) -> BeautifulSoup:
        """loads and parses main torrent's page"""

        soup = self.get_torrent_page(url)
        if not soup:
            raise YtsmxTrackerException('main torrent page loading failed')

        return soup

    @classmethod
    def extract_movie_id(cls, root: BeautifulSoup) -> str:
        """returns movie id from tracker's info page"""

        movie_info_tag = root.find("div", {"id": "movie-info"})
        if not movie_info_tag:
            raise YtsmxTrackerException('div#movie-info not found on page')

        movie_id = movie_info_tag.attrs['data-movie-id']
        if not movie_id.isdigit():
            raise YtsmxTrackerException('movie-id is not a digit. Markup is changed')

        return movie_id

    def _get_movie_details(self, movie_id: str) -> dict:
        """returns dict with movie info by calling API"""

        response = self.get_response(f'{API_BASE}movie_details.json?movie_id={movie_id}')
        if not response:
            raise YtsmxTrackerException("API didn't respond")

        movie_info_json = response.json()

        return movie_info_json

    @classmethod
    def get_quality_links(cls, movie_details: dict) -> QualityLinks:
        """extract quality and it's link from API response"""

        try:
            qualities = {
                cls._get_quality_from_torrent(torrent): torrent['url']
                for torrent in movie_details['data']['movie']['torrents']
            }
        except KeyError as e:
            raise YtsmxTrackerException('API movie details response is not parser. API changed') from e

        return qualities

    def _get_preferred_link(self, links: QualityLinks) -> QualityLink | None:
        """returns most preferred `QualityLink` of all `links` or `None`"""

        preferred_qualities = [q for q in self.quality_prefs if q in links]
        if preferred_qualities:
            quality = preferred_qualities[0]
            link = links[quality]
            return quality, link

        return None

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        try:
            # 1. load movie page, cache it
            soup = self._get_torrent_page(url)

            # 2. find movie ID - (eg. 38698)
            movie_id = self.extract_movie_id(soup)

            # 3. ask the API for details
            movie_details = self._get_movie_details(movie_id)

            # 4. parse torrent details to find preffered quality
            available_qualities = self.get_quality_links(movie_details)

        except YtsmxTrackerException as e:
            self.log_error(str(e))
            return ''

        self.log_debug(f"Available in qualities: {', '.join(available_qualities)}")

        if pref_link := self._get_preferred_link(available_qualities):
            _, link = pref_link
            return link

        self.log_info(
            'Torrent is not available in preferred qualities: '
            f"{', '.join(self.quality_prefs)}" or '(empty)'
        )

        quality, link = next(iter(available_qualities.items()))
        self.log_info(f'Fallback to `{quality}` quality ...')

        return link
