# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from unittest import mock

from django.http import Http404
from django.test import override_settings
from django.urls import reverse

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, PageViewRestriction

from springfield.cms.models import SimpleRichTextPage
from springfield.cms.tests.factories import LocaleFactory
from springfield.cms.utils import LOCALE_FALLBACK_EXEMPT_ATTR
from springfield.cms.views import wagtail_serve_with_locale_fallback

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def test_page(minimal_site):
    return SimpleRichTextPage.objects.get(slug="test-page")


@pytest.mark.parametrize(
    "restriction_type, password",
    (
        (PageViewRestriction.PASSWORD, "secret"),
        (PageViewRestriction.LOGIN, ""),
    ),
    ids=["Password restriction reads request.session", "Login restriction reads request.user"],
)
@override_settings(WAGTAIL_ENABLE_ADMIN=False)
def test_private_page_without_admin_is_not_found(restriction_type, password, test_page, rf, caplog):
    PageViewRestriction.objects.create(page=test_page, restriction_type=restriction_type, password=password)
    request = rf.get("/en-US/test-page/")

    with caplog.at_level(logging.WARNING, logger="springfield.cms.views"), pytest.raises(Http404):
        wagtail_serve_with_locale_fallback(request, "test-page/")

    # Otherwise the locale fallback finds this same page and redirects to it in a loop.
    assert getattr(request, LOCALE_FALLBACK_EXEMPT_ATTR, False)
    assert "/en-US/test-page/" in caplog.text


@override_settings(WAGTAIL_ENABLE_ADMIN=True)
def test_private_page_with_admin_and_no_session_still_errors(test_page, rf):
    PageViewRestriction.objects.create(page=test_page, restriction_type=PageViewRestriction.PASSWORD, password="secret")

    with pytest.raises(AttributeError):
        wagtail_serve_with_locale_fallback(rf.get("/en-US/test-page/"), "test-page/")


@override_settings(WAGTAIL_ENABLE_ADMIN=False)
def test_unrelated_attribute_error_without_admin_still_errors(test_page, rf):
    unrelated_error = AttributeError("'NoneType' object has no attribute 'title'", name="title", obj=None)

    with mock.patch("springfield.cms.views.wagtail_serve", side_effect=unrelated_error), pytest.raises(AttributeError):
        wagtail_serve_with_locale_fallback(rf.get("/en-US/test-page/"), "test-page/")


@pytest.fixture
def create_locales(minimal_site):
    """Replace the locales `minimal_site` creates with the given language codes."""

    def _create_locales(*language_codes):
        Locale.objects.filter(language_code="fr").delete()
        return [LocaleFactory(language_code=code) for code in language_codes]

    return _create_locales


@override_settings(FALLBACK_LOCALES={"en-CA": "en-US", "en-GB": "en-US"})
def test_submit_page_translation_includes_aliases(admin_client, create_locales, test_page):
    """Check the patched submit page translation view's alias related additions.
    See CmsConfig._patch_submit_translation_form"""
    create_locales("de", "en-CA", "en-GB")
    submit_url = reverse("wagtail_localize:submit_page_translation", args=(test_page.pk,))

    response = admin_client.get(submit_url)

    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # "Select all except aliases" control added
    select_all_except_aliases = soup.select_one("input#id_select_all_except_aliases")
    assert select_all_except_aliases is not None

    # Languages that are aliases show a badge of their source language
    language_labels = [label.get_text(strip=True, separator="\n") for label in soup.select("#id_locales label")]
    expected_language_labels = [
        "German",
        "English (Canada)\nalias → en-US",
        "English (Great Britain)\nalias → en-US",
    ]
    assert language_labels == expected_language_labels


@pytest.mark.parametrize(
    "locales",
    [
        (),  # only default en-US
        ("de",),
        ("en-CA", "en-GB"),
    ],
    ids=["no_locales", "no_aliases", "all_aliases"],
)
@override_settings(FALLBACK_LOCALES={"en-CA": "en-US", "en-GB": "en-US"})
def test_submit_page_translation_no_select_all_except_aliases_checkbox(admin_client, create_locales, locales, test_page):
    """The "Select all except aliases" control is added only if some languages are aliases."""
    create_locales(*locales)
    submit_url = reverse("wagtail_localize:submit_page_translation", args=(test_page.pk,))

    response = admin_client.get(submit_url)

    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    select_all_except_aliases = soup.select_one("input#id_select_all_except_aliases")
    assert select_all_except_aliases is None
