import logging

from torrt.base_tracker import GenericPrivateTracker
from torrt.utils import TrackerClassesRegistry


LOGGER = logging.getLogger(__name__)


class AniDUBTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://tr.anidub.com tracker."""

    alias = 'tr.anidub.com'
    login_url = 'http://%(domain)s/'
    auth_cookie_name = 'dle_user_id'

    def __init__(self, username=None, password=None, cookies=None, query_string=None, quality_prefs=None):
        super(AniDUBTracker, self).__init__(
            username=username, password=password, cookies=cookies, query_string=query_string
        )
        if quality_prefs is None:
            quality_prefs = ['bd720', 'tv720', 'dvd480', 'hwp', 'psp']
        self.quality_prefs = quality_prefs

    def get_login_form_data(self, login, password):
        return {'login_name': login, 'login_password': password, 'login': 'submit'}

    def get_download_link(self, url):
        """Tries to find .torrent file download link at forum thread page and return that one."""
        download_link = None
        page_soup = self.get_response(
            url, referer=url, cookies=self.cookies, query_string=self.query_string, as_soup=True
        )

        if page_soup.select('form input[name="login"]'):
            LOGGER.debug('Login is required to download torrent file.')
            domain =  self.extract_domain(url)
            if self.login(domain):
                download_link = self.get_download_link(url)
        else:

            available_qualities = []

            quality_divs = page_soup.select('div.torrent > div.torrent_c > div')
            for quality_div in quality_divs:
                available_qualities.append(quality_div['id'])

            LOGGER.debug('Available in qualities: %s', ', '.join(available_qualities))

            if available_qualities:

                prefered_qualities = [quality for quality in self.quality_prefs if quality in available_qualities]
                if not prefered_qualities:
                    LOGGER.debug('Torrent is not available in preferred qualities: %s', ', '.join(self.quality_prefs))
                else:
                    target_quality = prefered_qualities[0]
                    LOGGER.debug('Trying to get torrent in `%s` quality ...', target_quality)

                    target_links = page_soup.select('div#%s div.torrent_h a' % target_quality)
                    if target_links:
                        if isinstance(target_links, list):
                            download_link = target_links[0]['href']
                        else:
                            download_link = target_links['href']
                        download_link = self.expand_link(url, download_link)
                    else:
                        LOGGER.debug('Unable to find a link for `%s` quality', target_quality)

        return download_link


TrackerClassesRegistry.add(AniDUBTracker)
