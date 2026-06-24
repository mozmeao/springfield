# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from django.core.cache import cache

import pytest
from waffle.testutils import override_switch

pytestmark = pytest.mark.django_db


def _test(
    url,
    client,
    follow=False,
    expected_status=200,
    expected_content=None,
):
    resp = client.get(url, follow=follow)
    assert resp.status_code == expected_status
    if expected_content is not None:
        assert expected_content in resp.text


@pytest.fixture(autouse=True)
def _clear_healthz_cdn_cache():
    # The view caches its page-check result per-process; clear between tests so
    # one test's success doesn't mask another's failure (or vice-versa).
    from springfield.base.views import HEALTHZ_CDN_CACHE_KEY

    cache.delete(HEALTHZ_CDN_CACHE_KEY)
    yield
    cache.delete(HEALTHZ_CDN_CACHE_KEY)


@pytest.fixture
def healthz_cdn_cms_pages(client):
    """Bootstrap the Wagtail tree required for the production
    HEALTHZ_CDN_CRITICAL_PATHS list to fully resolve in tests.

    Only `/whatsnew/general/` needs CMS scaffolding — it doesn't match the
    3-digit version regex in firefox/urls.py and so falls through to Wagtail's
    catch-all. The homepage and versioned whatsnew render via static views
    with no fixture needed, and `/de/...` falls back to en-US in this env.
    """
    import wagtail_factories
    from wagtail.models import Site

    from springfield.cms.tests.factories import (
        GeneralWhatsNewPage2026Factory,
        SimpleRichTextPageFactory,
        WhatsNewIndexPageFactory,
    )

    root_page = SimpleRichTextPageFactory(slug="root_page", live=True)
    hostname = client._base_environ()["SERVER_NAME"]
    try:
        site = Site.objects.get(is_default_site=True)
        site.root_page = root_page
        site.hostname = hostname
        site.save()
    except Site.DoesNotExist:
        wagtail_factories.SiteFactory(
            root_page=root_page,
            is_default_site=True,
            hostname=hostname,
        )

    index = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    general = GeneralWhatsNewPage2026Factory(parent=index)
    general.save_revision().publish()
    return general


def test_healthz(client):
    _test(
        url="/healthz/",
        client=client,
        expected_content="pong",
    )


def test_readiness(client):
    _test(
        url="/readiness/",
        client=client,
    )


@override_switch("HEALTHZ_CDN_DB_CHECKS_ENABLED", active=True)
def test_healthz_cdn(client):
    # Happy path: critical pages all return < 400, so the healthcheck returns "pong".
    # Mock the inner check so the test doesn't depend on the homepage rendering
    # successfully in the test environment.
    with patch("springfield.base.views._check_critical_pages", return_value=(200, "pong")):
        _test(
            url="/healthz-cdn/",
            client=client,
            expected_content="pong",
        )


@override_switch("HEALTHZ_CDN_DB_CHECKS_ENABLED", active=True)
def test_healthz_cdn_actually_renders_critical_pages(client, healthz_cdn_cms_pages):
    # End-to-end smoke test: no mocks on the inner check, so the view really
    # invokes its inner django.test.Client against the live production
    # HEALTHZ_CDN_CRITICAL_PATHS list. The healthz_cdn_cms_pages fixture stands
    # up the one CMS-served path that doesn't otherwise resolve in CI; the
    # other paths render via static views.
    _test(
        url="/healthz-cdn/",
        client=client,
        expected_content="pong",
    )


@override_switch("HEALTHZ_CDN_DB_CHECKS_ENABLED", active=False)
def test_healthz_cdn_bypasses_page_check_when_switch_off(client):
    # When the switch is off, the view returns 200 OK without rendering any internal
    # pages, even if those pages would otherwise fail. Verify by patching the check
    # to raise — if the bypass works, the patch is never reached.
    with patch("springfield.base.views._check_critical_pages", side_effect=AssertionError("should not run")):
        _test(
            url="/healthz-cdn/",
            client=client,
            expected_content="pong",
        )


class _FakeClient:
    """Stand-in for django.test.Client used by the view, so test patches don't
    inadvertently intercept pytest-django's own client. Configure via class attrs."""

    response_status_code = 200
    raise_on_get = None

    def __init__(self, **kwargs):
        pass

    def get(self, path, follow=False):
        if self.raise_on_get is not None:
            raise self.raise_on_get
        return type("Resp", (), {"status_code": self.response_status_code})()


@override_switch("HEALTHZ_CDN_DB_CHECKS_ENABLED", active=True)
def test_healthz_cdn_fails_when_critical_page_returns_5xx(client):
    # Simulate a critical-page render coming back as 500 (e.g. column-dropping
    # migration applied, old code can't query the dropped column).
    fake_client_class = type("Fake", (_FakeClient,), {"response_status_code": 500})
    with patch("springfield.base.views.Client", fake_client_class):
        _test(
            url="/healthz-cdn/",
            client=client,
            expected_status=500,
            expected_content="critical page failed",
        )


@override_switch("HEALTHZ_CDN_DB_CHECKS_ENABLED", active=True)
def test_healthz_cdn_fails_when_critical_page_raises(client):
    # If the internal page render raises despite raise_request_exception=False
    # (e.g. DB connection dropped mid-request), we treat it as failed.
    fake_client_class = type("Fake", (_FakeClient,), {"raise_on_get": RuntimeError("DB gone")})
    with patch("springfield.base.views.Client", fake_client_class):
        _test(
            url="/healthz-cdn/",
            client=client,
            expected_status=500,
            expected_content="critical page failed",
        )


@override_switch("HEALTHZ_CDN_DB_CHECKS_ENABLED", active=True)
def test_healthz_cdn_caches_result(client):
    # The page-check result is cached per-process to absorb a Fastly burst into a
    # single render. Verify it runs once across two back-to-back requests.
    with patch("springfield.base.views._check_critical_pages", return_value=(200, "pong")) as mocked:
        _test(url="/healthz-cdn/", client=client, expected_content="pong")
        _test(url="/healthz-cdn/", client=client, expected_content="pong")
        assert mocked.call_count == 1


def test_healthz_cron(client):
    _test(
        url="/healthz-cron/",
        client=client,
        expected_content="Time Since Last Cron Task Runs",
        expected_status=500,  # because an unsynced DB returns a 500, but with the correct HTML
    )
