# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.test import override_settings

import pytest
from wagtail.models import Locale, Page, Site

from springfield.cms.models import (
    AbstractSpringfieldCMSPage,
    SimpleRichTextPage,
    StructuralPage,
)
from springfield.cms.tests.factories import StructuralPageFactory, WhatsNewIndexPageFactory, WhatsNewPageFactory

pytestmark = [
    pytest.mark.django_db,
]


@mock.patch("springfield.cms.models.SimpleRichTextPage.get_view_restrictions")
@pytest.mark.parametrize(
    "fake_restrictions, expected_headers",
    (
        ([], "max-age=600"),
        ([mock.Mock()], "max-age=0, no-cache, no-store, must-revalidate, private"),
    ),
    ids=[
        "Default, unrestricted-page behaviour",
        "Restricted-page behaviour",
    ],
)
def test_cache_control_headers_on_pages_with_view_restrictions(
    mock_get_view_restrictions,
    fake_restrictions,
    expected_headers,
    client,
    minimal_site,
):
    mock_get_view_restrictions.return_value = fake_restrictions

    page = SimpleRichTextPage.objects.last()  # made by the minimal_site fixture

    # Confirm we're using the base page
    assert isinstance(page, AbstractSpringfieldCMSPage)

    _relative_url = page.relative_url(minimal_site)
    assert _relative_url == "/en-US/test-page/"

    response = client.get(_relative_url)

    assert response.get("Cache-Control") == expected_headers


def test_StructuralPage_serve_methods(
    minimal_site,
    rf,
):
    "Show that structural pages redirect to their parent rather than serve anything"

    root_page = SimpleRichTextPage.objects.first()
    sp = StructuralPageFactory(parent=root_page, slug="folder-page")
    sp.save()

    _relative_url = sp.relative_url(minimal_site)
    assert _relative_url == "/en-US/folder-page/"

    request = rf.get(_relative_url)
    live_result = sp.serve(request)
    assert live_result.headers["location"].endswith(root_page.url)

    preview_result = sp.serve_preview(request)
    assert preview_result.headers["location"].endswith(root_page.url)


@pytest.mark.parametrize(
    "config, page_class, success_expected",
    (
        ("__all__", SimpleRichTextPage, True),  # same as default
        ("firefox.SomeOtherPageClass,cms.StructuralPage,cms.SimpleRichTextPage", StructuralPage, True),
        ("cms.SimpleRichTextPage", SimpleRichTextPage, True),
        ("cms.SimpleRichTextPage,firefox.SomeOtherPageClass", SimpleRichTextPage, True),
        ("firefox.SomeOtherPageClass,cms.SimpleRichTextPage", SimpleRichTextPage, True),
        ("firefox.SomeOtherPageClass,firefox.SomeOtherPageClass", SimpleRichTextPage, False),
        ("firefox.SomeOtherPageClass", SimpleRichTextPage, False),
        ("firefox.SomeOtherPageClass,legal.SomeLegalPageClass", StructuralPage, False),
    ),
)
def test_CMS_ALLOWED_PAGE_MODELS_controls_Page_can_create_at(
    config,
    page_class,
    success_expected,
    minimal_site,
):
    home_page = SimpleRichTextPage.objects.last()
    with override_settings(Dev=False, CMS_ALLOWED_PAGE_MODELS=config.split(",")):
        assert page_class.can_create_at(home_page) == success_expected


@mock.patch("springfield.cms.models.base.get_locales_for_cms_page")
def test__patch_request_for_springfield__locales_available_via_cms(
    mock_get_locales_for_cms_page,
    minimal_site,
    rf,
):
    request = rf.get("/some-path/that/is/irrelevant")

    page = SimpleRichTextPage.objects.last()  # made by the minimal_site fixture

    mock_get_locales_for_cms_page.return_value = ["en-US", "fr", "pt-BR"]

    patched_request = page.specific._patch_request_for_springfield(request)
    assert sorted(patched_request._locales_available_via_cms) == ["en-US", "fr", "pt-BR"]


def test__patch_request_for_springfield_annotates_is_cms_page(tiny_localized_site, rf):
    request = rf.get("/some-path/that/is/irrelevant")
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]
    assert en_us_test_page.specific.__class__ == SimpleRichTextPage

    patched_request = en_us_test_page.specific._patch_request_for_springfield(request)
    assert patched_request.is_cms_page is True


def test_whats_new_index_page_redirects_to_latest_whats_new(
    minimal_site,
    rf,
):
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/whatsnew/"

    v123_page = WhatsNewPageFactory(parent=index_page, slug="123", version="123")
    v123_page.save()
    v124_page = WhatsNewPageFactory(parent=index_page, slug="124", version="124")
    v124_page.save()

    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v124_page.url)


def test_whats_new_index_page_redirects_to_home_if_no_children(
    minimal_site,
    rf,
):
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/whatsnew/"

    request = rf.get(_relative_url)

    # No WhatsNewPage exists yet, so should redirect to /
    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_whats_new_index_page_redirects_to_locale_appropriate_child(
    tiny_localized_site,
    rf,
):
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page

    pt_br_locale = Locale.objects.get(language_code="pt-BR")
    pt_br_root_page = en_us_root_page.get_translation(pt_br_locale)

    assert pt_br_root_page

    en_us_index_page = WhatsNewIndexPageFactory(parent=en_us_root_page, slug="whatsnew")
    en_us_index_page.save()

    pt_br_index_page = en_us_index_page.copy_for_translation(pt_br_locale)
    pt_br_index_page.title = "O que há de novo no Firefox"
    pt_br_index_page.save()
    pt_br_index_page.save_revision().publish()

    _en_us_relative_url = en_us_index_page.relative_url(tiny_localized_site)
    assert _en_us_relative_url == "/en-US/whatsnew/"

    _pt_br_relative_url = pt_br_index_page.relative_url(tiny_localized_site)
    assert _pt_br_relative_url == "/pt-BR/whatsnew/"

    en_us_v123_page = WhatsNewPageFactory(parent=en_us_index_page, slug="123", version="123")
    en_us_v123_page.save()
    en_us_v124_page = WhatsNewPageFactory(parent=en_us_index_page, slug="124", version="124")
    en_us_v124_page.save()

    pt_br_v123_page = en_us_v123_page.copy_for_translation(pt_br_locale)
    pt_br_v123_page.title = "O que tem de novo no Firefox 123"
    pt_br_v123_page.save_revision().publish()

    pt_br_v124_page = en_us_v124_page.copy_for_translation(pt_br_locale)
    pt_br_v124_page.title = "O que tem de novo no Firefox 124"
    pt_br_v124_page.save_revision().publish()

    pt_br_index_page.refresh_from_db()

    en_us_request = rf.get(_en_us_relative_url)

    response = en_us_index_page.specific.serve(en_us_request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(en_us_v124_page.url)

    pt_br_request = rf.get(_pt_br_relative_url)
    response = pt_br_index_page.specific.serve(pt_br_request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(pt_br_v124_page.url)
