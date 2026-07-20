# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.featured_image_section_fixtures import get_featured_image_section_with_scroll_snippet_test_page

pytestmark = [pytest.mark.django_db]


def test_featured_image_section_renders_scroll_to_see_more_snippet(minimal_site, rf):
    page = get_featured_image_section_with_scroll_snippet_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    wrapper = soup.find("div", class_="fl-scroll-to-see-more-wrapper")
    assert wrapper, "Scroll to see more wrapper should be rendered"
    assert "Scroll to see more" in wrapper.get_text()
