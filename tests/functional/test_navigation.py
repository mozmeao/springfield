# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from pages.firefox.home import FirefoxHomePage


@pytest.mark.smoke
@pytest.mark.nondestructive
def test_navigation(base_url, selenium):
    page = FirefoxHomePage(selenium, base_url, locale="de").open()
    page.navigation.open_resources_menu()
    assert page.navigation.is_resources_menu_displayed
