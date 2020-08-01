from typing import List

from ..base_tracker import GenericPrivateTracker


class AniDUBTracker(GenericPrivateTracker):
    """This class implements .torrent files downloads for http://tr.anidub.com tracker."""

    alias: str = 'tr.anidub.com'

    login_url: str = 'https://%(domain)s/'
    auth_cookie_name: str = 'dle_user_id'

    def __init__(
            self,
            username: str = None,
            password: str = None,
            cookies: dict = None,
            query_string: str = None,
            quality_prefs: List[str] = None
    ):
        super(AniDUBTracker, self).__init__(
            username=username, password=password, cookies=cookies, query_string=query_string
        )

        if quality_prefs is None:
            quality_prefs = ['bd720', 'tv720', 'dvd480', 'hwp', 'psp']

        self.quality_prefs = quality_prefs

    def get_login_form_data(self, login: str, password: str) -> dict:
        return {'login_name': login, 'login_password': password, 'login': 'submit'}

    def get_download_link(self, url: str) -> str:
        """Tries to find .torrent file download link at forum thread page and return that one."""

        download_link = ''

        page_soup = self.get_torrent_page(url)

        if page_soup.select('form input[name="login"]'):

            self.log_debug('Login is required to download torrent file.')
            domain = self.extract_domain(url)

            if self.login(domain):
                download_link = self.get_download_link(url)

        else:

            available_qualities = []

            quality_divs = page_soup.select('div.torrent > div.torrent_c > div')

            for quality_div in quality_divs:
                available_qualities.append(quality_div['id'])

            self.log_debug(f"Available in qualities: {', '.join(available_qualities)}")

            if available_qualities:

                preferred_qualities = [
                    quality
                    for quality in self.quality_prefs
                    if quality in available_qualities
                ]

                if not preferred_qualities:
                    self.log_debug(
                        "Torrent is not available in preferred qualities: "
                        f"{', '.join(self.quality_prefs)}")

                else:

                    target_quality = preferred_qualities[0]

                    self.log_debug(f'Trying to get torrent in `{target_quality}` quality ...')

                    target_links = page_soup.select(f'div#{target_quality} div.torrent_h a')

                    if target_links:

                        if isinstance(target_links, list):
                            download_link = target_links[0]['href']

                        else:
                            download_link = target_links['href']

                        download_link = self.expand_link(url, download_link)

                    else:
                        self.log_debug(f'Unable to find a link for `{target_quality}` quality')

        return download_link
