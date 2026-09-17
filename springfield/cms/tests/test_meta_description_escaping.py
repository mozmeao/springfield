# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests that `description` and `og:description` are HTML-escaped exactly once.

Double-escaping leaves literal `&#39;` visible in link previews on Slack,
Facebook and anywhere else that unescapes the meta tag before displaying it.
"""

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.homepage_fixtures import get_home_test_page

pytestmark = [pytest.mark.django_db]

DESCRIPTION = """Firefox is Wrexham AFC's official web browser partner & front-of-kit "sponsor"."""


@pytest.fixture
def described_page(index_page):
    page = get_home_test_page()
    page.search_description = DESCRIPTION
    page.save_revision().publish()
    return page


@pytest.mark.parametrize(
    "selector",
    [
        {"name": "description"},
        {"property": "og:description"},
    ],
)
def test_description_meta_tags_are_escaped_once(described_page, rf, selector):
    request = rf.get(described_page.get_full_url())
    response = described_page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    tag = soup.find("meta", selector)
    assert tag is not None, f"no meta tag matching {selector}"

    # BeautifulSoup unescapes once, so a single round-trip must give the
    # original text back. Under double-escaping this reads "AFC&#39;s".
    assert tag["content"] == DESCRIPTION


def test_description_markup_contains_no_double_escaped_entities(described_page, rf):
    request = rf.get(described_page.get_full_url())
    html = described_page.serve(request).content.decode()

    assert "&amp;#39;" not in html
    assert "&amp;amp;" not in html
    assert "&amp;#34;" not in html
