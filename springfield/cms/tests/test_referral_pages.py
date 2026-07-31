# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.models import Site

from springfield.cms.tests.factories import ReferralHubPageFactory
from springfield.firefox.referral import crypto

pytestmark = [pytest.mark.django_db]


def test_hub_page_get_context_builds_invite_url_from_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/?ref_key=TESTABCDEFGHJKMN"))

    # The hub encrypts the ref_key into an invite code and wraps it in the
    # shareable download URL. Asserted against the crypto helpers rather than a
    # hardcoded code so this tracks the wiring, not the cipher output (which is
    # covered by the referral crypto tests).
    expected_code = crypto.referral_id_to_invite_code("TESTABCDEFGHJKMN")
    assert context["invite_url"] == crypto.invite_url_for_code(expected_code)
    assert context["invite_url"].startswith("https://www.firefox.com/get-firefox/?invitation=")
    assert crypto.invite_code_to_referral_id(expected_code) == "TESTABCDEFGHJKMN"


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
