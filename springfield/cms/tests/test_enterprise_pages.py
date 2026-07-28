# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.enterprise_page_fixtures import get_enterprise_pages

pytestmark = [
    pytest.mark.django_db,
]

# Every page in the enterprise sub-site (the parent plus its four children).
ENTERPRISE_PAGE_KEYS = ["enterprise", "product", "support", "download", "contact"]


@pytest.fixture
def enterprise_pages(index_page, placeholder_images):
    return get_enterprise_pages()


@pytest.mark.parametrize("page_key", ENTERPRISE_PAGE_KEYS)
def test_enterprise_page_uses_enterprise_theme(page_key, enterprise_pages, rf):
    page = enterprise_pages[page_key]

    response = page.serve(rf.get(page.get_full_url()))
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    body_el = soup.find("body")
    assert body_el
    assert "fl-theme-enterprise" in body_el.get("class", [])


@pytest.mark.parametrize("page_key", ENTERPRISE_PAGE_KEYS)
def test_enterprise_page_has_enterprise_header(page_key, enterprise_pages, rf):
    """Each page renders the enterprise navigation snippet in the header: the
    overridden enterprise logo and the "Request early access" CTA button, which
    together uniquely identify the enterprise navigation (inherited from the
    parent page)."""
    page = enterprise_pages[page_key]

    response = page.serve(rf.get(page.get_full_url()))
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    header = soup.find("header", class_="fl-header")
    assert header

    assert header.find(class_="fl-logo-fx-custom")
    assert "Request early access" in header.get_text()
