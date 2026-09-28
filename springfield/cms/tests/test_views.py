# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.http import Http404
from django.test import override_settings

import pytest
from wagtail.models import PageViewRestriction

from springfield.cms.models import SimpleRichTextPage
from springfield.cms.views import wagtail_serve_with_locale_fallback

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def private_page(minimal_site):
    page = SimpleRichTextPage.objects.get(slug="test-page")
    PageViewRestriction.objects.create(page=page, restriction_type=PageViewRestriction.PASSWORD, password="secret")
    return page


@override_settings(WAGTAIL_ENABLE_ADMIN=False)
def test_private_page_without_admin_is_not_found(private_page, rf):
    with pytest.raises(Http404):
        wagtail_serve_with_locale_fallback(rf.get("/en-US/test-page/"), "test-page/")


@override_settings(WAGTAIL_ENABLE_ADMIN=True)
def test_private_page_with_admin_and_no_session_still_errors(private_page, rf):
    with pytest.raises(AttributeError):
        wagtail_serve_with_locale_fallback(rf.get("/en-US/test-page/"), "test-page/")
