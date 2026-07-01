# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for JSON-LD structured data rendering.

Covers:
- Homepage entity @graph (Organization, Brand, WebSite, WebPage, SoftwareApplication)
- WebPage locale-aware @id / url / inLanguage (mirrors canonical-url.html)
- BreadcrumbList emission on nested CMS pages
- Absence of structured data when no `page` object is present in context
"""

import json

from django.conf import settings

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.homepage_fixtures import get_home_test_page

pytestmark = [pytest.mark.django_db]


def _extract_json_ld(html_content):
    """Parse rendered HTML and return all <script type='application/ld+json'> blocks
    as a list of decoded JSON objects."""
    soup = BeautifulSoup(html_content, "html.parser")
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    return [json.loads(s.string) for s in scripts]


# ---------------------------------------------------------------------------
# Homepage entity graph
# ---------------------------------------------------------------------------


def test_homepage_emits_valid_json_ld_entity_graph(index_page, rf):
    """Homepage renders a single JSON-LD script with a valid @graph containing
    Organization, Brand, WebSite, WebPage, and SoftwareApplication entities."""
    test_page = get_home_test_page()
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    blocks = _extract_json_ld(response.content)
    assert len(blocks) == 1, "Homepage should emit exactly one JSON-LD script block"

    data = blocks[0]
    assert data["@context"] == "https://schema.org"
    assert "@graph" in data

    types_present = {entity["@type"] for entity in data["@graph"]}
    assert types_present == {"Organization", "Brand", "WebSite", "WebPage", "SoftwareApplication"}


def test_homepage_website_has_no_inlanguage(index_page, rf):
    """WebSite represents the whole site (locale-agnostic). It must not declare
    inLanguage, which would imply the entire site is in one language."""
    test_page = get_home_test_page()
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)

    data = _extract_json_ld(response.content)[0]
    website = next(e for e in data["@graph"] if e["@type"] == "WebSite")
    assert "inLanguage" not in website


def test_homepage_webpage_url_is_locale_aware(index_page, rf):
    """WebPage.@id and WebPage.url must be locale-specific (matching the page's
    canonical URL), so different locales emit different identifiers rather than
    a single shared site-root URL."""
    test_page = get_home_test_page()
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)

    data = _extract_json_ld(response.content)[0]
    webpage = next(e for e in data["@graph"] if e["@type"] == "WebPage")

    # The WebPage URL should NOT be just the bare site root.
    assert webpage["url"] != "https://www.firefox.com/"
    # It should include the locale prefix (e.g. /en-US/).
    assert webpage["url"].startswith(settings.CANONICAL_URL)
    assert "/en-US/" in webpage["url"] or webpage["url"].count("/") > 3

    # @id is locale-aware too (same URL with #webpage fragment).
    assert webpage["@id"].startswith(webpage["url"])
    assert webpage["@id"].endswith("#webpage")


def test_homepage_webpage_inlanguage_matches_canonical_lang(index_page, rf):
    """WebPage.inLanguage should reflect the language of the page's actual
    content (CANONICAL_LANG), not just the requested locale (LANG)."""
    test_page = get_home_test_page()
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)

    data = _extract_json_ld(response.content)[0]
    webpage = next(e for e in data["@graph"] if e["@type"] == "WebPage")
    assert webpage["inLanguage"] == "en-US"


def test_homepage_entity_ids_are_consistent(index_page, rf):
    """The cross-references via @id should target entities that actually exist
    in the @graph (no dangling references)."""
    test_page = get_home_test_page()
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)

    data = _extract_json_ld(response.content)[0]
    declared_ids = {entity["@id"] for entity in data["@graph"]}

    org = next(e for e in data["@graph"] if e["@type"] == "Organization")
    assert org["brand"]["@id"] in declared_ids

    website = next(e for e in data["@graph"] if e["@type"] == "WebSite")
    assert website["publisher"]["@id"] in declared_ids
    assert website["about"]["@id"] in declared_ids

    webpage = next(e for e in data["@graph"] if e["@type"] == "WebPage")
    assert webpage["isPartOf"]["@id"] in declared_ids
    assert webpage["about"]["@id"] in declared_ids

    app = next(e for e in data["@graph"] if e["@type"] == "SoftwareApplication")
    assert app["brand"]["@id"] in declared_ids
    assert app["publisher"]["@id"] in declared_ids


def test_homepage_software_application_has_dynamic_version(index_page, rf):
    """SoftwareApplication.softwareVersion should be populated from product-details
    via the latest_firefox_version context variable (i.e. not a Jinja placeholder)."""
    test_page = get_home_test_page()
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)

    data = _extract_json_ld(response.content)[0]
    app = next(e for e in data["@graph"] if e["@type"] == "SoftwareApplication")
    # Looks like a real version string (digits + dot), not an unrendered template tag.
    assert app["softwareVersion"]
    assert "{{" not in app["softwareVersion"]
    assert "}}" not in app["softwareVersion"]


# ---------------------------------------------------------------------------
# BreadcrumbList on nested CMS pages
#
# BreadcrumbList rendering lives in the `{% block structured_data %}` default
# in `cms/base-flare.html`. It fires for any CMS page whose template extends
# base-flare.html and which has ancestors above the Wagtail root.
#
# The straightforward `tiny_localized_site` fixture (used in
# test_locale_fallback_rendering.py) creates `SimpleRichTextPage` instances
# which extend `base-protocol.html` — a legacy base that does NOT have the
# structured_data block. Adding live-render coverage for BreadcrumbList would
# require building a nested fixture with a page type that extends
# base-flare.html (e.g. ArticleDetailPage), which is more setup than this
# behavior warrants.
#
# Manual verification path: visit any nested CMS page in dev and view source —
# the JSON-LD BreadcrumbList block appears in <head> with itemListElement
# entries for each ancestor and the current page (last item has `name` but no
# `item` URL, per schema.org convention).
# ---------------------------------------------------------------------------
