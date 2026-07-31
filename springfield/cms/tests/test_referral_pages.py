# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from django.conf import settings

import pytest
from wagtail.models import Site

from springfield.cms.tests.factories import ReferralHubPageFactory
from springfield.firefox.referral import crypto

pytestmark = [pytest.mark.django_db]

CAPTURE_MESSAGE = "springfield.cms.models.pages.capture_message"


def test_hub_page_get_context_builds_invite_url_from_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/?ref_key=TESTABCDEFGHJKMN"))

    # The hub encrypts the `ref_key` into an invite code and wraps it in the
    # shareable download URL. The code itself comes from the crypto helper
    # rather than being hardcoded, so this tracks the wiring and the URL shape,
    # not the cipher output (which is covered by the referral crypto tests).
    expected_code = crypto.referral_id_to_invite_code("TESTABCDEFGHJKMN")
    assert context["invite_url"] == f"{settings.CANONICAL_URL}/get-firefox/?invitation={expected_code}"


def test_hub_page_get_context_invite_url_empty_when_ref_key_missing(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/"))

    assert context["invite_url"] == ""


def test_hub_page_get_context_invite_url_empty_when_ref_key_blank(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/?ref_key="))

    assert context["invite_url"] == ""


def test_hub_page_get_context_invite_url_empty_when_ref_key_invalid(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # A ref_key that is not a valid referral ID (here it has separators and is
    # the wrong length) is treated like a missing one instead of raising.
    context = hub_page.get_context(rf.get("/invite/?ref_key=not-a-valid-ref-key"))

    assert context["invite_url"] == ""


def test_hub_page_reports_correctly_sized_invalid_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # Right length but `I` is not a Crockford symbol, so this plausibly came
    # from the referral flow and is worth a Sentry warning.
    with patch(CAPTURE_MESSAGE) as capture:
        context = hub_page.get_context(rf.get("/invite/?ref_key=A7B9K2M4PXQRSTVI"))

    assert context["invite_url"] == ""
    assert capture.call_count == 1
    assert capture.call_args.kwargs["level"] == "warning"


def test_hub_page_stays_quiet_for_wrong_length_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # Anything can land in a public query string, so a ref_key that is not even
    # the right length is ignored rather than filling Sentry with scanner noise.
    with patch(CAPTURE_MESSAGE) as capture:
        context = hub_page.get_context(rf.get("/invite/?ref_key=junk"))

    assert context["invite_url"] == ""
    assert capture.call_count == 0
