# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.http import Http404

import pytest
from wagtail.models import Site

from springfield.cms.tests.factories import ReferralGetFirefoxPageFactory, ReferralHubPageFactory

pytestmark = [pytest.mark.django_db]

VALID_HUB_REF_KEY = "0123456789ABCDEF"  # 16 chars, all Crockford Base 32
VALID_INVITATION_CODE = "0123456789ABCDEFG"  # 17 chars, all Crockford Base 32


def test_hub_page_get_context_builds_invite_url_from_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get(f"/invite/?ref_key={VALID_HUB_REF_KEY}"))

    # Placeholder algorithm reverses the ref_key.
    assert context["invite_url"] == "http://testserver/get-firefox/?invitation=FEDCBA9876543210"


def test_hub_page_get_context_url_encodes_invite_code(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # Force the helper to return a value with characters that must be
    # percent-encoded so we exercise the urlencode call without relying
    # on the placeholder algorithm ever emitting them.
    hub_page._referral_id_to_invite_code = lambda referral_id: "a b&c=d"

    context = hub_page.get_context(rf.get(f"/invite/?ref_key={VALID_HUB_REF_KEY}"))

    assert context["invite_url"] == "http://testserver/get-firefox/?invitation=a+b%26c%3Dd"


def test_referral_id_to_invite_code_placeholder_algorithm():
    hub_page = ReferralHubPageFactory.build()

    assert hub_page._referral_id_to_invite_code("TESTABCDEF") == "FEDCBAFAKE"
    # A ref_key without the TEST prefix just gets reversed.
    assert hub_page._referral_id_to_invite_code("ABCDE") == "EDCBA"


# ---- validation / unhappy-path coverage ----

# Bad values shared by both pages. Length-based cases are only meaningful
# per-page (16 vs 17) and get their own parametrisations below.
BAD_SHARED_VALUES = [
    ("empty", ""),
    ("lowercase", "abcdefghjkmnpqrs"),  # length adjusted per page in test
    ("hyphen", "ABCDEFGHJKMNPQR-"),
    ("space", "ABCDEFGHJKMNPQ R"),
    ("excluded_letter_i", "IBCDEFGHJKMNPQRS"),
    ("excluded_letter_o", "OBCDEFGHJKMNPQRS"),
]


def _pad_or_truncate(value, length):
    """Right-pad with '0' or truncate to hit the target length while keeping the bad char."""
    if len(value) >= length:
        return value[:length]
    return value + "0" * (length - len(value))


@pytest.mark.parametrize("label, raw", BAD_SHARED_VALUES)
def test_hub_page_raises_404_on_bad_ref_key(rf, label, raw):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    ref_key = _pad_or_truncate(raw, 16) if label != "empty" else ""
    request = rf.get(f"/invite/?ref_key={ref_key}") if ref_key else rf.get("/invite/")

    with pytest.raises(Http404):
        hub_page.get_context(request)


@pytest.mark.parametrize(
    "ref_key",
    [
        "ABCDEFGHJKMNPQR",  # 15 chars
        "ABCDEFGHJKMNPQRST",  # 17 chars
    ],
)
def test_hub_page_raises_404_on_wrong_length_ref_key(rf, ref_key):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    with pytest.raises(Http404):
        hub_page.get_context(rf.get(f"/invite/?ref_key={ref_key}"))


def test_get_firefox_page_get_context_exposes_invitation_code(rf):
    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page)

    context = page.get_context(rf.get(f"/get-firefox/?invitation={VALID_INVITATION_CODE}"))

    assert context["invitation_code"] == VALID_INVITATION_CODE


@pytest.mark.parametrize("label, raw", BAD_SHARED_VALUES)
def test_get_firefox_page_raises_404_on_bad_invitation(rf, label, raw):
    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page)

    invitation = _pad_or_truncate(raw, 17) if label != "empty" else ""
    request = rf.get(f"/get-firefox/?invitation={invitation}") if invitation else rf.get("/get-firefox/")

    with pytest.raises(Http404):
        page.get_context(request)


@pytest.mark.parametrize(
    "invitation",
    [
        "ABCDEFGHJKMNPQRS",  # 16 chars, one short
        "ABCDEFGHJKMNPQRSTU",  # 18 chars, one long (and contains U which is excluded, but
        # length check runs first so failure mode remains WRONG_LENGTH)
    ],
)
def test_get_firefox_page_raises_404_on_wrong_length_invitation(rf, invitation):
    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page)

    with pytest.raises(Http404):
        page.get_context(rf.get(f"/get-firefox/?invitation={invitation}"))


def _patch_sentry():
    """Patch capture_message and new_scope, returning (mock_capture, mock_scope).

    mock_scope records set_tag / set_extra calls so tests can assert on them.
    """
    scope = mock.MagicMock()
    scope_cm = mock.MagicMock()
    scope_cm.__enter__.return_value = scope
    scope_cm.__exit__.return_value = False

    capture_patch = mock.patch("springfield.cms.models.pages.capture_message")
    scope_patch = mock.patch("springfield.cms.models.pages.new_scope", return_value=scope_cm)
    return capture_patch, scope_patch, scope


def test_hub_page_bad_ref_key_reports_to_sentry(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    capture_patch, scope_patch, scope = _patch_sentry()
    with capture_patch as mock_capture, scope_patch:
        with pytest.raises(Http404):
            hub_page.get_context(rf.get("/invite/?ref_key=abcdefghjkmnpqrs"))

    assert mock_capture.call_count == 1
    args, kwargs = mock_capture.call_args
    assert "ReferralHubPage" in args[0]
    assert "wrong_case" in args[0]
    assert kwargs == {"level": "warning"}

    tag_calls = {call.args for call in scope.set_tag.call_args_list}
    assert tag_calls == {
        ("page", "ReferralHubPage"),
        ("param", "ref_key"),
        ("failure", "wrong_case"),
    }
    scope.set_extra.assert_called_once_with("code_prefix", "abcde")


def test_get_firefox_page_bad_invitation_reports_to_sentry(rf):
    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page)

    capture_patch, scope_patch, scope = _patch_sentry()
    with capture_patch as mock_capture, scope_patch:
        with pytest.raises(Http404):
            page.get_context(rf.get("/get-firefox/"))

    assert mock_capture.call_count == 1
    args, kwargs = mock_capture.call_args
    assert "ReferralGetFirefoxPage" in args[0]
    assert "missing" in args[0]
    assert kwargs == {"level": "warning"}

    tag_calls = {call.args for call in scope.set_tag.call_args_list}
    assert tag_calls == {
        ("page", "ReferralGetFirefoxPage"),
        ("param", "invitation"),
        ("failure", "missing"),
    }
    # No prefix when the code was missing entirely.
    scope.set_extra.assert_not_called()


def test_sentry_report_does_not_leak_full_code(rf):
    """A lowercased real-looking code must not appear in Sentry beyond the 5-char prefix.

    This is the WRONG_CASE footgun: the underlying code may be a genuine referral
    id, so only a short prefix is safe to log.
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)
    real_looking_code = "testabcdefghjkmn"  # 16 lowercase Crockford chars

    capture_patch, scope_patch, scope = _patch_sentry()
    with capture_patch as mock_capture, scope_patch:
        with pytest.raises(Http404):
            hub_page.get_context(rf.get(f"/invite/?ref_key={real_looking_code}"))

    # The message itself must not contain the code.
    assert real_looking_code not in mock_capture.call_args.args[0]
    # No extra beyond the truncated prefix carries the full code.
    for call in scope.set_extra.call_args_list:
        for arg in call.args:
            assert real_looking_code not in str(arg)
    # And prefix really is just 5 chars.
    scope.set_extra.assert_called_once_with("code_prefix", "testa")
