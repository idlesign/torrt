from typing import List, Dict, Tuple, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag
from requests.models import Response

from ..exceptions import TorrtTrackerException
from ..base_tracker import GenericPublicTracker


API_BASE = 'https://yts.mx/api/v2/'
QualityLinks = Dict[str, str]
QualityLink = Tuple[str, str]

class YtsmxTrackerException(TorrtTrackerException):
    """Yts.mx specific exceptions"""

class YtsmxTracker(GenericPublicTracker):
    """This class implements .torrent files downloads for https://yts.mx tracker."""

    alias: str = 'yts.mx'

    test_urls: List[str] = [
        'https://yts.mx/movies/the-matrix-resurrections-2021',
    ]

    def __init__(self, quality_prefs: List[str] = None):
        super().__init__()

        if quality_prefs is None:
            quality_prefs = ['1080P.WEB', '720P.WEB']
        else:
            quality_prefs = [self._sanitize_quality(x) for x in quality_prefs]

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

    def _extract_movie_id(self, root: BeautifulSoup) -> str:
        """returns movie id from tracker's info page"""

        movie_info_tag = root.find("div", {"id": "movie-info"})
        if not movie_info_tag:
            raise YtsmxTrackerException('div#movie-info not found on page')

        movie_info_tag: Tag
        movie_id = movie_info_tag.attrs['data-movie-id']
        if not movie_id.isdigit():
            raise YtsmxTrackerException('movie-id is not a digit. Markup is changed')

        return movie_id

    def _get_movie_details(self, movie_id: str) -> dict:
        """returns dict with movie info by calling API"""

        response = self.get_response(f'{API_BASE}movie_details.json?movie_id={movie_id}')
        if not response:
            raise YtsmxTrackerException("API didn't respond")

        response: Response
        movie_info_json = response.json()

        return movie_info_json

    def _get_quality_links(self, movie_details: dict) -> QualityLinks:
        """extract quality and it's link from API response"""

        try:
            qualities = {
                self._get_quality_from_torrent(torrent): torrent['url']
                for torrent in movie_details['data']['movie']['torrents']
            }
        except KeyError:
            raise YtsmxTrackerException('API movie details response is not parser. API changed')

        return qualities

    def _get_preffered_link(self, links: QualityLinks) -> Optional[QualityLink]:
        """returns most preffered `QualityLink` of all `links` or `None`"""

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
            movie_id = self._extract_movie_id(soup)

            # 3. ask the API for details
            movie_details = self._get_movie_details(movie_id)

            # 4. parse torrent details to find preffered quality
            available_qualities = self._get_quality_links(movie_details)

        except YtsmxTrackerException as e:
            self.log_error(str(e))
            return ''

        self.log_debug(f"Available in qualities: {', '.join(available_qualities)}")

        pref_link = self._get_preffered_link(available_qualities)
        if pref_link:
            _, link = pref_link
            return link

        else:
            self.log_info(
                'Torrent is not available in preferred qualities: '
                f"{', '.join(self.quality_prefs)}" or '(empty)'
            )

            quality, link = next(iter(available_qualities.items()))
            self.log_info(f'Fallback to `{quality}` quality ...')

            return link

        return ''