# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.base import BasePage


class FirefoxMobilePage(BasePage):
    _URL_TEMPLATE = "/{locale}/browsers/mobile/"

    _android_download_link_locator = (By.CSS, "[href*='play.google.com'][data-cta-type='firefox_mobile']")
    _ios_download_link_locator = (By.CSS, "[href*='apps.apple.com'][data-cta-type='firefox_mobile']")
    _focus_android_download_link_locator = (By.CSS, "[href*='play.google.com'][data-cta-type='firefox_focus']")
    _focus_ios_download_link_locator = (By.CSS, "[href*='apps.apple.com'][data-cta-type='firefox_focus']")

    @property
    def is_android_download_link_displayed(self):
        return self.is_element_displayed(*self._android_download_link_locator)

    @property
    def is_ios_download_link_displayed(self):
        return self.is_element_displayed(*self._ios_download_link_locator)

    @property
    def is_focus_android_download_link_displayed(self):
        return self.is_element_displayed(*self._focus_android_download_link_locator)

    @property
    def is_focus_ios_download_link_displayed(self):
        return self.is_element_displayed(*self._focus_ios_download_link_locator)
