# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.models import Site

from springfield.cms.tests.factories import ReferralHubPageFactory

pytestmark = [pytest.mark.django_db]


def test_hub_page_get_context_builds_invite_url_from_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/?ref_key=TESTABCDEF"))

    # Placeholder algorithm reverses the ref_key and swaps a leading TSET for FAKE.
    assert context["invite_url"] == "http://testserver/get-firefox/?invitation=FEDCBAFAKE"


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


def test_hub_page_get_context_url_encodes_invite_code(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # Force the helper to return a value with characters that must be
    # percent-encoded so we exercise the urlencode call without relying
    # on the placeholder algorithm ever emitting them.
    hub_page._referral_id_to_invite_code = lambda referral_id: "a b&c=d"

    context = hub_page.get_context(rf.get("/invite/?ref_key=whatever"))

    assert context["invite_url"] == "http://testserver/get-firefox/?invitation=a+b%26c%3Dd"


def test_referral_id_to_invite_code_placeholder_algorithm():
    hub_page = ReferralHubPageFactory.build()

    assert hub_page._referral_id_to_invite_code("TESTABCDEF") == "FEDCBAFAKE"
    # A ref_key without the TEST prefix just gets reversed.
    assert hub_page._referral_id_to_invite_code("ABCDE") == "EDCBA"
