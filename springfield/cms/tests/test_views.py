# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from unittest import mock

from django.http import Http404
from django.test import override_settings

import pytest
from wagtail.models import PageViewRestriction

from springfield.cms.models import SimpleRichTextPage
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
