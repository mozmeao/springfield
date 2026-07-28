# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse

import pytest
from wagtail.models import Page

from springfield.cms.models import FreeFormPage2026

# A term that appears only in a StreamField body block, never in a page title.
BODY_ONLY_TERM = "Zzyzxqualia"


@pytest.fixture
def free_form_page_with_body_term(minimal_site) -> FreeFormPage2026:
    root_page = minimal_site.root_page
    page = FreeFormPage2026(slug="content-search-target", title="Plain Boring Title")
    page.upper_content = [("notification", {"message": f"<p>{BODY_ONLY_TERM} mobile browser</p>"})]
    root_page.add_child(instance=page)
    page.save_revision().publish()
    return page


@pytest.mark.django_db
def test_content_search_finds_streamfield_body_content(free_form_page_with_body_term, admin_client):
    """The admin content-search view uses .search(), so it finds a page by text
    that lives only in a StreamField body block."""
    response = admin_client.get(reverse("cms_content_search"), {"q": BODY_ONLY_TERM})

    assert response.status_code == 200
    assert b"Plain Boring Title" in response.content


@pytest.mark.django_db
def test_content_search_finds_page_by_title(free_form_page_with_body_term, admin_client):
    """The admin content-search view uses .search(), which should also find a page by its title."""
    response = admin_client.get(reverse("cms_content_search"), {"q": "Plain Boring Title"})

    assert response.status_code == 200
    assert b"Plain Boring Title" in response.content


@pytest.mark.django_db
def test_builtin_autocomplete_cannot_find_body_content(free_form_page_with_body_term):
    """Regression guard: the reason this view exists. Wagtail's admin page search
    uses .autocomplete(), which only reads AutocompleteFields (title), so it never
    matches StreamField body content."""
    assert Page.objects.autocomplete(BODY_ONLY_TERM).count() == 0
    assert Page.objects.search(BODY_ONLY_TERM).count() == 1
