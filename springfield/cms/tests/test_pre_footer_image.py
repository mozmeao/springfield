# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for the per-page pre-footer newsletter form illustration option."""

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet
from springfield.cms.models import FreeFormPage2026, WhatsNewPage2026
from springfield.cms.models.pages import (
    PRE_FOOTER_IMAGE_GLOBE,
    PRE_FOOTER_IMAGE_KIT,
    PRE_FOOTER_IMAGE_NONE,
)

pytestmark = pytest.mark.django_db


def test_pre_footer_image_defaults_to_kit():
    assert FreeFormPage2026(title="x", slug="x").pre_footer_image == PRE_FOOTER_IMAGE_KIT
    assert WhatsNewPage2026(title="x", slug="x").pre_footer_image == PRE_FOOTER_IMAGE_KIT


@pytest.fixture
def publish_freeform_page(minimal_site):
    """Return a callable that creates + publishes a FreeFormPage2026 with the
    given pre_footer_image, ensuring the pre-footer form snippet exists so the
    form renders."""

    def publish(pre_footer_image):
        get_pre_footer_cta_form_snippet()
        page = FreeFormPage2026(
            slug=f"pre-footer-{pre_footer_image}",
            title=f"Pre-footer {pre_footer_image}",
            pre_footer_image=pre_footer_image,
        )
        minimal_site.root_page.add_child(instance=page)
        page.save_revision().publish()
        return page

    return publish


def test_kit_renders_kit_illustration(publish_freeform_page, client):
    page = publish_freeform_page(PRE_FOOTER_IMAGE_KIT)
    html = client.get(page.url).content.decode()
    soup = BeautifulSoup(html, "html.parser")
    illustration = soup.select_one(".fl-newsletterform-illustration img")
    assert illustration is not None
    assert "flare/kit-on-rock.png" in illustration["src"]
    assert "flare/globe.png" not in html


def test_globe_renders_globe_illustration(publish_freeform_page, client):
    page = publish_freeform_page(PRE_FOOTER_IMAGE_GLOBE)
    soup = BeautifulSoup(client.get(page.url).content, "html.parser")
    illustration = soup.select_one(".fl-newsletterform-illustration img")
    assert illustration is not None
    assert "flare/globe.png" in illustration["src"]


def test_none_renders_no_illustration(publish_freeform_page, client):
    page = publish_freeform_page(PRE_FOOTER_IMAGE_NONE)
    soup = BeautifulSoup(client.get(page.url).content, "html.parser")
    assert soup.select_one(".fl-newsletterform-cta") is not None
    assert soup.select_one(".fl-newsletterform-illustration") is None
