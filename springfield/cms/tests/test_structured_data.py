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
from wagtail.models import Page, PageViewRestriction

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
# BreadcrumbList — get_breadcrumb_ancestors() helper on AbstractSpringfieldCMSPage
#
# Full template-render coverage is skipped: the fixture pages extend
# base-protocol.html (no structured_data block). The helper is what actually
# determines whether the emitted BreadcrumbList is correct, so we cover it
# directly.
# ---------------------------------------------------------------------------


def test_get_breadcrumb_ancestors_starts_at_site_root(tiny_localized_site):
    """The ancestor list must start at Site.root_page, never above it.

    Regression guard for the "Welcome to your new Wagtail site!" leak: in
    production the Wagtail tree root and per-locale roots sit above
    Site.root_page, and their titles must not appear in the BreadcrumbList.
    """
    home = Page.objects.get(locale__language_code="en-US", slug="home")
    test_page = home.get_children().get(slug="test-page")
    child_page = test_page.get_children().get(slug="child-page")

    ancestors = list(child_page.specific.get_breadcrumb_ancestors())

    assert ancestors == [home, test_page]


def test_get_breadcrumb_ancestors_excludes_wagtail_system_root(tiny_localized_site):
    """The depth-1 Wagtail system root must never appear in the breadcrumb."""
    home = Page.objects.get(locale__language_code="en-US", slug="home")
    test_page = home.get_children().get(slug="test-page")

    wagtail_root = Page.objects.get(depth=1)

    for page in test_page.specific.get_breadcrumb_ancestors():
        assert page != wagtail_root
        assert page.depth > 1


def test_get_breadcrumb_ancestors_all_items_have_full_url(tiny_localized_site):
    """Every ancestor returned must be routable (full_url is not None).

    This is the invariant that a valid Google BreadcrumbList requires: every
    non-final `item` must be a resolvable URL.
    """
    home = Page.objects.get(locale__language_code="en-US", slug="home")
    child_page = home.get_children().get(slug="test-page").get_children().get(slug="child-page")

    for page in child_page.specific.get_breadcrumb_ancestors():
        assert page.full_url is not None, f"Ancestor {page!r} has full_url=None — would emit invalid BreadcrumbList"


def test_get_breadcrumb_ancestors_only_returns_live_pages(tiny_localized_site):
    """Unpublished ancestors must be excluded."""
    home = Page.objects.get(locale__language_code="en-US", slug="home")
    test_page = home.get_children().get(slug="test-page")
    child_page = test_page.get_children().get(slug="child-page")

    test_page.unpublish()

    ancestors = list(child_page.specific.get_breadcrumb_ancestors())
    assert test_page not in ancestors


def test_get_breadcrumb_ancestors_excludes_ancestor_above_site_root_page(prod_shape_site):
    """Regression guard for the production bug this method was written to fix.

    Uses a fixture that mirrors production's 3-level tree, where a non-routable
    page ('Welcome to your new Wagtail site!') sits at depth 2 above
    Site.root_page at depth 3. A regression to depth-based filtering
    (`filter(depth__gt=1)`) would leak that page's title into the breadcrumb;
    this test would catch it. The other tests in this file use `tiny_localized_site`
    where Site.root_page is at depth 2, so they cannot reproduce this scenario.
    """
    article = prod_shape_site["article"]
    default_seed = prod_shape_site["default_seed"]
    homepage = prod_shape_site["homepage"]
    features = prod_shape_site["features"]

    ancestors = list(article.specific.get_breadcrumb_ancestors())

    ancestor_pks = [a.pk for a in ancestors]
    assert default_seed.pk not in ancestor_pks
    assert all(a.title != "Welcome to your new Wagtail site!" for a in ancestors)
    assert ancestor_pks == [homepage.pk, features.pk]


def test_get_breadcrumb_ancestors_excludes_view_restricted_ancestors(prod_shape_site):
    """Access-restricted ancestors must not leak into public JSON-LD.

    A password-protected or group-restricted ancestor would otherwise expose
    its title and URL to Google when a public descendant is crawled.
    """
    features = prod_shape_site["features"]
    article = prod_shape_site["article"]

    PageViewRestriction.objects.create(
        page=features,
        restriction_type=PageViewRestriction.PASSWORD,
        password="secret",
    )

    ancestors = list(article.specific.get_breadcrumb_ancestors())
    assert features.pk not in [a.pk for a in ancestors]


def test_get_breadcrumb_ancestors_query_count(prod_shape_site, django_assert_max_num_queries):
    """Tripwire for the docstring's `Don't refactor to full_url is not None` warning.

    In steady state, the helper should fire exactly 2 queries: one for `.public()`'s
    PageViewRestriction lookup and one for the ancestor QuerySet. Site.get_site_root_paths
    is cached — in production requests it's always warm; here we pre-call it to isolate
    the steady-state cost from the one-time cache warmup.

    If a future refactor swaps the url_path prefix filter for per-ancestor Python
    attribute access (`[a for a in ... if a.full_url]`), this ceiling will trip.
    """
    from wagtail.models import Site

    Site.get_site_root_paths()  # warm the cache the way production requests do

    article = prod_shape_site["article"]
    with django_assert_max_num_queries(2):
        list(article.specific.get_breadcrumb_ancestors())
