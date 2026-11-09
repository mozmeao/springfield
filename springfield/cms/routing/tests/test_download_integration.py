# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Serve integration for DownloadPage, which matches its rules on the server."""

from types import SimpleNamespace

from django.conf import settings
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

import pytest
from waffle.testutils import override_switch
from wagtail.models import Site

from springfield.cms.models import DownloadPage
from springfield.cms.routing.arming import OrganicArmingCondition
from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule
from springfield.cms.tests.factories import DownloadIndexPageFactory, DownloadPageFactory, LocaleFactory

pytestmark = [pytest.mark.django_db]


def create_country_rule(page, target, operator, expected_value, sort_order=0):
    rule = RoutingRule.objects.create(page=page, target=target, sort_order=sort_order)
    RoutingCondition.objects.create(rule=rule, signal="country", operator=operator, expected_value=expected_value)
    return rule


def build_download_tree(index_slug):
    site = Site.objects.get(is_default_site=True)
    index = DownloadIndexPageFactory(parent=site.root_page, slug=index_slug)
    android = DownloadPageFactory(parent=index, slug="android", platform="android")
    variant = DownloadPageFactory(parent=android, slug="china", platform="android")
    rule = create_country_rule(android, variant, "is", "CN")
    return SimpleNamespace(site=site, index=index, android=android, variant=variant, rule=rule)


@pytest.fixture
def download():
    # Off the /download/ path, whose Django fallback route would swallow the redirect.
    return build_download_tree("routed-download")


def publish_translation(page, locale):
    translation = page.copy_for_translation(locale)
    translation.save()
    translation.publish(translation.save_revision())
    return translation.specific


@pytest.fixture
def translated_download(download):
    """The download tree published in ``de`` too; the copied rule still targets the English variant."""
    locale = LocaleFactory(language_code="de")
    publish_translation(download.site.root_page, locale)
    publish_translation(download.index, locale)
    download.de_android = publish_translation(download.android, locale)
    download.de_variant = publish_translation(download.variant, locale)
    return download


def get_page(client, page, country=None, query="", **extra):
    headers = {"HTTP_CF_IPCOUNTRY": country} if country else {}
    return client.get(page.get_url() + query, **headers, **extra)


# ---------------------------------------------------------------------------
# Adoption surface.
# ---------------------------------------------------------------------------


def test_download_page_matches_on_the_server():
    assert isinstance(DownloadPage.get_routing_trigger(), OrganicArmingCondition)
    assert DownloadPage.routing_matches_on_server() is True


def test_any_download_page_under_the_index_can_host_rules(download):
    windows = DownloadPageFactory(parent=download.index, slug="windows", platform="windows")
    windows_variant = DownloadPageFactory(parent=windows, slug="variant", platform="windows")
    assert download.android.is_routing_canonical() is True
    assert windows.is_routing_canonical() is True
    assert download.variant.is_routing_canonical() is False
    assert windows_variant.is_routing_canonical() is False


def test_a_nested_download_page_is_a_valid_target(download):
    RoutingRule(page=download.android, target=download.variant, match_all=True).full_clean()  # does not raise


def vary_names(response):
    return {name.strip().lower() for name in response.get("Vary", "").split(",") if name.strip()}


def test_a_variant_links_to_the_same_platform_pages_as_its_canonical(client, download):
    windows = DownloadPageFactory(parent=download.index, slug="windows", platform="windows")
    canonical_links = client.get(download.android.get_url()).context["platform_links"]
    variant_links = client.get(download.variant.get_url()).context["platform_links"]
    assert canonical_links["windows"] == windows.get_url()
    assert canonical_links["android"] == download.android.get_url()
    assert variant_links == canonical_links


# ---------------------------------------------------------------------------
# Serve path.
# ---------------------------------------------------------------------------


@override_switch("user_routing", active=True)
def test_a_matching_visitor_is_redirected_with_attribution_only(client, download):
    response = get_page(client, download.android, country="CN", query="?utm_source=x&routing=1&routed=")
    assert response.status_code == 302
    assert response["Location"] == download.variant.get_url() + "?utm_source=x"
    assert response["Cache-Control"] == f"max-age={settings.ROUTING_RESOLVER_CACHE_SECONDS}"
    assert not response.cookies
    assert not response.has_header("Set-Cookie")
    # Site-wide middleware may add its own Vary; routing adds none, so no language or country.
    redirect_vary = vary_names(response)
    canonical_vary = vary_names(get_page(client, download.android, country="US"))
    assert redirect_vary <= canonical_vary
    assert not redirect_vary & {"accept-language", "cf-ipcountry", "cloudfront-viewer-country"}
    # Control: the locale redirect on the unprefixed URL varies on language, so the check above can fail.
    locale_redirect = client.get(download.android.get_url().removeprefix("/en-US"), HTTP_CF_IPCOUNTRY="CN")
    assert "accept-language" in vary_names(locale_redirect)


@override_settings(DEV=False)
@pytest.mark.parametrize("country", ("US", None))
def test_visitors_who_match_nothing_get_the_page_unchanged(client, download, country):
    dark = get_page(client, download.android, country=country).content
    with override_switch("user_routing", active=True):
        response = get_page(client, download.android, country=country)
    assert response.status_code == 200
    assert response.content == dark


@override_switch("user_routing", active=True)
def test_loop_breaker_serves_canonical(client, download):
    assert get_page(client, download.android, country="CN", query="?routed=1").status_code == 200


@override_switch("user_routing", active=True)
def test_kill_switch_serves_canonical(client, download):
    RoutingConfig.objects.create(page=download.android, routing_paused=True)
    assert get_page(client, download.android, country="CN").status_code == 200


def test_switch_off_serves_canonical(client, download):
    assert get_page(client, download.android, country="CN").status_code == 200


@override_switch("user_routing", active=True)
def test_the_variant_itself_is_served(client, download):
    assert get_page(client, download.variant, country="CN").status_code == 200


@override_switch("user_routing", active=True)
@override_settings(DEV=False, ALLOWED_HOSTS=["*"])
def test_geo_param_redirects_off_production_only(client, download):
    assert get_page(client, download.android, query="?geo=CN").status_code == 302
    assert get_page(client, download.android, query="?geo=CN", HTTP_HOST="www.firefox.com").status_code == 200


@override_switch("user_routing", active=True)
def test_a_translated_canonical_redirects_to_the_translated_variant(client, translated_download):
    response = get_page(client, translated_download.de_android, country="CN")
    assert response.status_code == 302
    assert response["Location"] == translated_download.de_variant.get_url()


def no_match_query_count(client, page):
    url = page.get_url()
    # Warm the caches so the counts differ only by what the routing code does.
    client.get(url, HTTP_CF_IPCOUNTRY="US")
    with CaptureQueriesContext(connection) as context:
        client.get(url, HTTP_CF_IPCOUNTRY="US")
    return len(context.captured_queries)


@override_switch("user_routing", active=True)
def test_no_match_costs_the_same_with_one_rule_or_three(client, download):
    one_rule = no_match_query_count(client, download.android)
    create_country_rule(download.android, download.variant, "is", "HK", sort_order=1)
    create_country_rule(download.android, download.variant, "in", "MO, TW", sort_order=2)
    assert no_match_query_count(client, download.android) == one_rule


@override_switch("user_routing", active=True)
def test_the_django_fallback_route_still_swallows_the_redirect(client):
    # prefer_cms keeps only a 200 from Wagtail. Remove this once /download/android/ has no Django view.
    download = build_download_tree("download")
    response = get_page(client, download.android, country="CN")
    assert response.status_code == 200
    assert "firefox/browsers/mobile/android.html" in [template.name for template in response.templates]
