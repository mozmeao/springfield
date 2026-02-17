# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as expected

from pages.base import BaseRegion


class Modal(BaseRegion):
    _root_locator = (By.ID, "modal")
    _close_locator = (By.ID, "modal-close")

    def close(self):
        modal = self.selenium.find_element(*self._root_locator)
        self.find_element(*self._close_locator).click()
        self.wait.until(expected.staleness_of(modal))

    @property
    def is_displayed(self):
        return self.page.is_element_displayed(*self._root_locator)

    def displays(self, selector):
        return self.is_element_displayed(*selector)


class ModalProtocol(BaseRegion):
    _protocol_root_locator = (By.CLASS_NAME, "mzp-c-modal")
    _protocol_close_locator = (By.CLASS_NAME, "mzp-c-modal-button-close")
    _flare26_root_locator = (By.CLASS_NAME, "fl-dialog")
    _flare26_close_locator = (By.CLASS_NAME, "fl-dialog-close-button")

    def close(self):
        modal = self.selenium.find_element(*self._protocol_root_locator)
        if not modal:
            modal = self.selenium.find_element(*self._flare26_root_locator)

        close = self.selenium.find_element(*self._protocol_close_locator)
        if not close:
            close = self.selenium.find_element(*self._flare26_close_locator)

        close.click()
        self.wait.until(expected.staleness_of(modal))

    @property
    def is_displayed(self):
        is_displayed = self.page.is_element_displayed(*self._protocol_root_locator)
        if not is_displayed:
            is_displayed = self.page.is_element_displayed(*self._flare26_root_locator)
        return is_displayed

    def displays(self, selector):
        return self.is_element_displayed(*selector)
