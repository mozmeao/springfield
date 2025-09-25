# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from pages.firefox.browsers.desktop_landing import DesktopPage


@pytest.mark.smoke
@pytest.mark.nondestructive
def test_navigation(base_url, selenium):
    page = DesktopPage(selenium, base_url).open()
    page.navigation.open_resources_menu()
    assert page.navigation.is_resources_menu_displayed
