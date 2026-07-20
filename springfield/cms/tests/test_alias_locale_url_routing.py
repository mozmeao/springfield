# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests that alias-locale fallback respects the URL router.

These tests verify that when a Django view and a Wagtail page exist at the
same URL path, the correct one is served for alias locales — depending on
whether the Django view uses the ``prefer_cms`` decorator or not.
"""

from django.http import HttpResponse
from django.test import override_settings
from django.urls import path, resolve

import pytest
from wagtail.models import Locale, Page, Site
from wagtail.rich_text import RichText

from springfield.base.i18n import springfield_i18n_patterns
from springfield.cms.decorators import prefer_cms
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory
from springfield.urls import urlpatterns as springfield_urlpatterns

pytestmark = [pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Test views — defined at module level so the URL config can reference them.
# ---------------------------------------------------------------------------

DJANGO_VIEW_RESPONSE = "Django view response"
DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE = "Django prefer_cms fallback view response"
DJANGO_ONLY_VIEW_RESPONSE = "Django-only view response"


def _plain_django_view(request):
    """A plain Django view (no prefer_cms decorator) at a path that also
    has a Wagtail page."""
    return HttpResponse(DJANGO_VIEW_RESPONSE)


@prefer_cms
def _prefer_cms_django_view(request):
    """A prefer_cms-decorated Django view at a path that also has a
    Wagtail page."""
    return HttpResponse(DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE)


def _django_only_view(request):
    """A Django view at a path that has no matching Wagtail page."""
    return HttpResponse(DJANGO_ONLY_VIEW_RESPONSE)


# The shared path for both the Django view and the Wagtail page.
_SHARED_PATH = "test-page/child-page/"

# A path that only the Django view serves — no Wagtail page here.
_DJANGO_ONLY_PATH = "django-only/view/"

# URL configuration
urlpatterns = (
    springfield_i18n_patterns(
        path(_SHARED_PATH, _plain_django_view, name="plain_django_view"),
        path(
            f"prefer-cms/{_SHARED_PATH}",
            _prefer_cms_django_view,
            name="prefer_cms_django_view",
        ),
        path(_DJANGO_ONLY_PATH, _django_only_view, name="django_only_view"),
    )
    + springfield_urlpatterns
)


def _set_up_alias_locale_with_fallback_pages(tiny_localized_site):
    """Set up pt-PT as an alias locale falling back to pt-BR.

    tiny_localized_site already provides pt-BR pages including child-page.
    We also create pt-BR pages under prefer-cms/ for the prefer_cms tests,
    and a pt-PT locale with a live root page (but no prefer-cms translations).

    Returns (pt_br_child, pt_br_prefer_cms_child).
    """
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")

    # Also create pages at the prefer-cms/ path in en-US and pt-BR so the
    # prefer_cms-decorated view has a Wagtail page to find.
    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    # Create prefer-cms parent page in en-US.
    en_us_prefer_cms = SimpleRichTextPageFactory(
        title="Prefer CMS",
        slug="prefer-cms",
        parent=en_us_root,
    )
    en_us_prefer_cms.save_revision().publish()

    # Create test-page and child-page under prefer-cms in en-US.
    en_us_prefer_cms_test = SimpleRichTextPageFactory(
        title="Test Page Under Prefer CMS",
        slug="test-page",
        parent=en_us_prefer_cms,
    )
    en_us_prefer_cms_test.save_revision().publish()

    en_us_prefer_cms_child = SimpleRichTextPageFactory(
        title="Child Under Prefer CMS",
        slug="child-page",
        parent=en_us_prefer_cms_test,
        content=RichText("en-US prefer-cms child content"),
    )
    en_us_prefer_cms_child.save_revision().publish()

    # Translate the prefer-cms tree to pt-BR.
    pt_br_locale = Page.objects.get(locale__language_code="pt-BR", slug="child-page").locale

    pt_br_prefer_cms = en_us_prefer_cms.copy_for_translation(pt_br_locale)
    pt_br_prefer_cms.save_revision().publish()

    pt_br_prefer_cms_test = en_us_prefer_cms_test.copy_for_translation(pt_br_locale)
    pt_br_prefer_cms_test.save_revision().publish()

    pt_br_prefer_cms_child = en_us_prefer_cms_child.copy_for_translation(pt_br_locale)
    pt_br_prefer_cms_child.title = "Filho sob Prefer CMS (pt-BR)"
    pt_br_prefer_cms_child.content = RichText("pt-BR prefer-cms child content")
    pt_br_prefer_cms_child.save_revision().publish()

    # Verify preconditions: the _SHARED_PATH URL matches both a Django view
    # and a Wagtail page, so the tests exercise a genuine conflict.
    match = resolve(f"/en-US/{_SHARED_PATH}")
    assert match.func is _plain_django_view, f"Expected _plain_django_view to own /en-US/{_SHARED_PATH}, got {match.func}"
    matching_page = Page.objects.filter(locale__language_code="en-US", slug="child-page").first()
    assert matching_page.url == f"/en-US/{_SHARED_PATH}", f"Expected Wagtail page at /en-US/{_SHARED_PATH}, got {matching_page.url}"

    # Same check for the prefer-cms path.
    prefer_cms_match = resolve(f"/en-US/prefer-cms/{_SHARED_PATH}")
    assert prefer_cms_match.func is _prefer_cms_django_view, (
        f"Expected _prefer_cms_django_view to own /en-US/prefer-cms/{_SHARED_PATH}, got {prefer_cms_match.func}"
    )
    assert en_us_prefer_cms_child.url == f"/en-US/prefer-cms/{_SHARED_PATH}", (
        f"Expected Wagtail page at /en-US/prefer-cms/{_SHARED_PATH}, got {en_us_prefer_cms_child.url}"
    )

    # Create a pt-PT locale with a live root page but no prefer-cms translations.
    # Tests can use pt_pt_root to simulate "alias locale with live root but missing page".
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    pt_pt_root = en_us_root.copy_for_translation(pt_pt_locale)
    pt_pt_root.save_revision().publish()
    pt_pt_root.refresh_from_db()

    return pt_br_child, pt_br_prefer_cms_child


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_plain_django_view(
    client,
    tiny_localized_site,
):
    """
    A plain Django view must NOT be overridden by alias-locale Wagtail fallback.

    When a non-prefer_cms Django view is registered at the same path as a
    Wagtail page, requesting the alias-locale URL must serve the Django view —
    NOT the Wagtail fallback page. The Django view takes priority because it
    appears before the Wagtail catch-all in the URL router.
    """
    _set_up_alias_locale_with_fallback_pages(tiny_localized_site)

    # pt-PT is an alias locale with a live root page but no page at _SHARED_PATH.
    pt_pt_locale = Locale.objects.get(language_code="pt-PT")
    pt_pt_root = Site.objects.get(is_default_site=True).root_page.get_translation(pt_pt_locale)
    assert pt_pt_root.live is True
    assert not Page.objects.filter(locale=pt_pt_locale, slug="child-page").exists()

    response = client.get(f"/pt-PT/{_SHARED_PATH}")

    # The plain Django view should be returned (since there is no Wagtail Page with that URL).
    assert response.status_code == 200
    assert response.content.decode() == DJANGO_VIEW_RESPONSE


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_plain_django_view_no_alias_page(
    client,
    tiny_localized_site,
):
    """
    A plain Django view must NOT be overridden by alias-locale Wagtail fallback
    even when the alias locale has no live root page.
    """
    _set_up_alias_locale_with_fallback_pages(tiny_localized_site)

    # Unpublish the pt-PT root so pt-PT has a Locale record but no live root page.
    pt_pt_locale = Locale.objects.get(language_code="pt-PT")
    pt_pt_root = Site.objects.get(is_default_site=True).root_page.get_translation(pt_pt_locale)
    pt_pt_root.unpublish()
    pt_pt_root.refresh_from_db()
    assert pt_pt_root.live is False

    response = client.get(f"/pt-PT/{_SHARED_PATH}")

    # The plain Django view should be returned (since there is no Wagtail Page with that URL).
    assert response.status_code == 200
    assert response.content.decode() == DJANGO_VIEW_RESPONSE


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_prefer_cms_view_serves_fallback_page_for_alias_locale(
    client,
    tiny_localized_site,
):
    """
    A prefer_cms view must serve the fallback locale's Wagtail page for an alias locale
    that has a live root page but no translation of the specific page requested.

    When a prefer_cms-decorated Django view is at the same path as a Wagtail
    page, requesting the alias-locale URL must serve the fallback locale's CMS
    content — not the Django fallback view. This is the whole point of
    prefer_cms: prefer CMS content when available.
    Note: pt-PT has a live root page, but no prefer-cms translation.
    Because pt-BR is the fallback locale for pt-PT, the (pt-BR) Wagtail page
    should be served at the pt-PT URL.
    """
    _, pt_br_prefer_cms_child = _set_up_alias_locale_with_fallback_pages(
        tiny_localized_site,
    )
    pt_pt_locale = Locale.objects.get(language_code="pt-PT")
    pt_pt_root = Site.objects.get(is_default_site=True).root_page.get_translation(pt_pt_locale)
    assert pt_pt_root.live is True
    assert not Page.objects.filter(locale=pt_pt_locale, slug="child-page").exists()

    response = client.get(f"/pt-PT/prefer-cms/{_SHARED_PATH}")

    assert response.status_code == 200
    html = response.content.decode()
    # The Wagtail fallback page (pt-BR) content should be served.
    assert pt_br_prefer_cms_child.title in html
    # The Django fallback view text should NOT appear.
    assert DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE not in html
    # content_locale should be set to the fallback locale.
    assert response.wsgi_request.content_locale == "pt-BR"


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_prefer_cms_view_falls_through_to_django_when_no_wagtail_page(
    client,
    tiny_localized_site,
):
    """
    A prefer_cms view must fall through to its Django view when no Wagtail page exists.

    When the fallback locale has no Wagtail page at the requested path,
    wagtail_serve_with_locale_fallback raises Http404. prefer_cms catches
    it and falls through to the Django view.
    """
    url_without_locale = f"prefer-cms/{_SHARED_PATH}"
    url = f"/pt-PT/{url_without_locale}"
    # There is no Wagtail Page that matches the URL used in this test.
    assert not Page.objects.filter(url_path__endswith=url_without_locale).exists()

    response = client.get(url)

    # Since there is no Wagtail page for the URL, we should serve the Django view.
    assert response.status_code == 200
    assert response.content.decode() == DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_django_only_view_unaffected_by_alias_locale_fallback(
    client,
    tiny_localized_site,
):
    """
    A Django view at a path with no Wagtail page is unaffected by alias-locale logic.

    The alias-locale fallback should not interfere with Django views that have
    no corresponding Wagtail page at all. The Django view must be served
    normally.
    """
    response = client.get(f"/pt-PT/{_DJANGO_ONLY_PATH}")
    assert response.status_code == 200
    assert response.content.decode() == DJANGO_ONLY_VIEW_RESPONSE


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_django_only_view_unaffected_in_non_alias_locale(
    client,
    tiny_localized_site,
):
    """A Django view in a non-alias locale is served normally."""
    response = client.get(f"/en-US/{_DJANGO_ONLY_PATH}")
    assert response.status_code == 200
    assert response.content.decode() == DJANGO_ONLY_VIEW_RESPONSE


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_django_only_view_unaffected_by_wagtail_pages(
    client,
    tiny_localized_site,
):
    """
    A Django view at a path with a matching Wagtail page is unaffected by alias-locale logic.

    The alias-locale fallback should not interfere with Django views that are
    not set up to serve Wagtail pages. The Django view must be served normally.

    Note: this test may seem strange or unnecessary; the goal here is to assert
    that our middleware does not mess up the URL routing.
    """
    # Create a Wagtail page tree at _DJANGO_ONLY_PATH in pt-BR so there is a
    # genuine conflict between the Django view and a Wagtail page.
    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    en_us_django_only_parent = SimpleRichTextPageFactory(
        title="Django Only Parent",
        slug="django-only",
        parent=en_us_root,
    )
    en_us_django_only_parent.save_revision().publish()

    en_us_django_only_leaf = SimpleRichTextPageFactory(
        title="Django Only Leaf",
        slug="view",
        parent=en_us_django_only_parent,
    )
    en_us_django_only_leaf.save_revision().publish()
    assert en_us_django_only_leaf.url == f"/en-US/{_DJANGO_ONLY_PATH}"

    # Translate to pt-BR so a fallback page exists for the pt-PT alias locale.
    pt_br_locale = Page.objects.get(locale__language_code="pt-BR", slug="child-page").locale

    pt_br_django_only_parent = en_us_django_only_parent.copy_for_translation(pt_br_locale)
    pt_br_django_only_parent.save_revision().publish()

    pt_br_django_only_leaf = en_us_django_only_leaf.copy_for_translation(pt_br_locale)
    pt_br_django_only_leaf.save_revision().publish()
    assert pt_br_django_only_leaf.url == f"/pt-BR/{_DJANGO_ONLY_PATH}"

    response = client.get(f"/pt-PT/{_DJANGO_ONLY_PATH}")

    # The response is the Django view, since it is set up in the URL configuration
    # to be a simple Django view (no prefer_cms or other overrides).
    assert response.status_code == 200
    assert response.content.decode() == DJANGO_ONLY_VIEW_RESPONSE


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_prefer_cms_view_serves_fallback_page_for_alias_locale_without_live_root(
    client,
    tiny_localized_site,
):
    """
    A prefer_cms view must serve the fallback locale's Wagtail page for an alias locale
    that has a Locale DB record but no live root page.
    """
    _, pt_br_prefer_cms_child = _set_up_alias_locale_with_fallback_pages(tiny_localized_site)
    pt_PT_locale = Locale.objects.get(language_code="pt-PT")
    en_us_root = Site.objects.get(is_default_site=True).root_page
    pt_pt_root = en_us_root.get_translation(pt_PT_locale)

    # Unpublish the pt-PT root page so this test exercises the "Locale exists
    # but no live root" code path in _alias_needs_prewagtail_intercept.
    pt_pt_root.unpublish()
    pt_pt_root.refresh_from_db()
    assert pt_pt_root.live is False

    response = client.get(f"/pt-PT/prefer-cms/{_SHARED_PATH}")

    assert response.status_code == 200
    html = response.content.decode()
    assert pt_br_prefer_cms_child.title in html
    assert DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE not in html
    assert response.wsgi_request.content_locale == "pt-BR"


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_prefer_cms_view_serves_fallback_page_for_alias_locale_without_locale_record(
    client,
    tiny_localized_site,
):
    """
    A prefer_cms view must serve the fallback locale's Wagtail page for an alias
    locale that has no Wagtail Locale DB record at all.
    """
    _, pt_br_prefer_cms_child = _set_up_alias_locale_with_fallback_pages(tiny_localized_site)

    # Delete the pt-PT root page and the Locale itself.
    pt_pt_locale = Locale.objects.get(language_code="pt-PT")
    en_us_root = Site.objects.get(is_default_site=True).root_page
    en_us_root.get_translation(pt_pt_locale).delete()
    pt_pt_locale.delete()
    assert not Locale.objects.filter(language_code="pt-PT").exists()

    response = client.get(f"/pt-PT/prefer-cms/{_SHARED_PATH}")

    assert response.status_code == 200
    html = response.content.decode()
    assert pt_br_prefer_cms_child.title in html
    assert DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE not in html
    assert response.wsgi_request.content_locale == "pt-BR"


@pytest.mark.urls(__name__)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_prefer_cms_view_serves_alias_locale_own_page_when_live_root_and_page_exist(
    client,
    tiny_localized_site,
):
    """
    A prefer_cms view must serve the alias locale's own Wagtail page when it exists,
    not the fallback locale's page or the Django view.

    When the alias locale (pt-PT) has a live root page AND its own translation of
    the requested page, prefer_cms should serve that page directly.
    """
    _, pt_br_prefer_cms_child = _set_up_alias_locale_with_fallback_pages(tiny_localized_site)

    # Create the pt-PT prefer-cms tree so the alias locale has its own page.
    pt_pt_locale = Locale.objects.get(language_code="pt-PT")
    en_us_prefer_cms = Page.objects.get(locale__language_code="en-US", slug="prefer-cms")
    en_us_prefer_cms_test = en_us_prefer_cms.get_children().get(slug="test-page")
    en_us_prefer_cms_child = en_us_prefer_cms_test.get_children().get(slug="child-page")

    pt_pt_prefer_cms = en_us_prefer_cms.copy_for_translation(pt_pt_locale)
    pt_pt_prefer_cms.save_revision().publish()
    pt_pt_prefer_cms_test = en_us_prefer_cms_test.copy_for_translation(pt_pt_locale)
    pt_pt_prefer_cms_test.save_revision().publish()
    pt_pt_prefer_cms_child = en_us_prefer_cms_child.copy_for_translation(pt_pt_locale)
    pt_pt_prefer_cms_child.title = "Filho sob Prefer CMS (pt-PT)"
    pt_pt_prefer_cms_child.save_revision().publish()
    pt_pt_prefer_cms_child.refresh_from_db()
    assert pt_pt_prefer_cms_child.live is True

    response = client.get(f"/pt-PT/prefer-cms/{_SHARED_PATH}")

    assert response.status_code == 200
    html = response.content.decode()
    assert pt_pt_prefer_cms_child.title in html
    assert pt_br_prefer_cms_child.title not in html
    assert DJANGO_VIEW_WITH_PREFER_CMS_RESPONSE not in html
    assert not getattr(response.wsgi_request, "content_locale", None)
