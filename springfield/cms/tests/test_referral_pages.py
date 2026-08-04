# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch
from urllib.parse import parse_qs

from django.conf import settings
from django.db import DatabaseError
from django.http import Http404, HttpResponseNotFound

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.blocks import TabBlock
from springfield.cms.middleware import CMSLocaleFallbackMiddleware
from springfield.cms.tests.factories import ReferralGetFirefoxPageFactory, ReferralHubPageFactory
from springfield.firefox.referral import crypto
from springfield.firefox.referral.models import FirefoxReferralData

pytestmark = [pytest.mark.django_db]

CAPTURE_MESSAGE = "springfield.cms.models.pages.capture_message"

# Referral IDs are 16 characters of canonical uppercase Crockford base32.
# This one mirrors a row from bootstrap_dummy_referral_data.
REFERRAL_ID = "TEST23456X000000"
# Well-formed, but no FirefoxReferralData row names it.
UNKNOWN_REFERRAL_ID = "TESTZZZZZZ000000"


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


def test_tab_referral_controls_render_the_invite_url_from_the_hub_context(rf):
    """End-to-end: /invite/?ref_key=... -> invite_url -> rendered tab controls.

    Ties the referral controls block to the real ReferralHubPage contract, so
    that a change to the invite-code scheme cannot silently leave the controls
    sharing a stale or wrong link.
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get(f"/invite/?ref_key={REFERRAL_ID}"))
    invite_url = context["invite_url"]
    expected_code = crypto.referral_id_to_invite_code(REFERRAL_ID)
    assert invite_url == f"{settings.CANONICAL_URL}/get-firefox/?invitation={expected_code}"

    block = TabBlock()
    value = block.to_python(
        {
            "tab_name": "Share Firefox",
            "referral_controls": [{"type": "referral_controls", "value": {}}],
        }
    )
    html = block.render(value, context={**context, "section_id": "hub", "tab_index": 1})
    soup = BeautifulSoup(html, "html.parser")

    controls = soup.find("div", class_="fl-referral-controls")
    assert controls is not None
    assert controls.find("button", attrs={"data-js": "fl-copy-to-clipboard"})["data-copy-value"] == invite_url

    # The default email body carries the link via its {invite link} placeholder.
    email_href = controls.find("a", class_="fl-referral-controls-share-email")["href"]
    assert parse_qs(email_href.split("?", 1)[1])["body"] == [
        "Here's how to download Firefox. I wanted to share a browser with you "
        f"that protects your privacy and gives you more control online. {invite_url}"
    ]

    # The referrer's own hub URL and ref_key must never reach a shareable field.
    assert "ref_key" not in str(controls)
    assert REFERRAL_ID not in str(controls)


def test_tab_referral_controls_absent_when_hub_opened_without_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/"))

    block = TabBlock()
    value = block.to_python(
        {
            "tab_name": "Share Firefox",
            "referral_controls": [{"type": "referral_controls", "value": {}}],
        }
    )
    html = block.render(value, context={**context, "section_id": "hub", "tab_index": 1})

    assert BeautifulSoup(html, "html.parser").find("div", class_="fl-referral-controls") is None


# install_count -> impact dashboard


def _impact_dash_tab_value():
    """A tab holding one impact dashboard with badges at 1, 5 and 25."""
    return TabBlock().to_python(
        {
            "tab_name": "Your impact",
            "impact_dash": [
                {
                    "type": "impact_dash",
                    "value": {"badges": [{"number": n, "singular_label": "person", "plural_label": "people"} for n in (1, 5, 25)]},
                }
            ],
        }
    )


def test_hub_page_get_context_publishes_install_count_for_known_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)
    # Mirrors a row from bootstrap_dummy_referral_data.
    FirefoxReferralData.objects.create(referral_id=REFERRAL_ID, install_count=342)

    context = hub_page.get_context(rf.get(f"/invite/?ref_key={REFERRAL_ID}"))

    assert context["install_count"] == 342


def test_hub_page_get_context_install_count_zero_for_unknown_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get(f"/invite/?ref_key={UNKNOWN_REFERRAL_ID}"))

    assert context["install_count"] == 0


@pytest.mark.parametrize("query", ["", "?ref_key="])
def test_hub_page_get_context_install_count_zero_without_ref_key(rf, query):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get(f"/invite/{query}"))

    assert context["install_count"] == 0


def test_hub_page_install_count_uses_a_single_query(django_assert_num_queries):
    hub_page = ReferralHubPageFactory.build()
    FirefoxReferralData.objects.create(referral_id=REFERRAL_ID, install_count=342)

    with django_assert_num_queries(1):
        assert hub_page._get_install_count(REFERRAL_ID) == 342


def test_hub_page_install_count_zero_when_database_errors(monkeypatch):
    """The impact dashboard is optional and must not be able to fail the page."""
    hub_page = ReferralHubPageFactory.build()

    def boom(*args, **kwargs):
        raise DatabaseError("relation does not exist")

    monkeypatch.setattr(FirefoxReferralData.objects, "get", boom)

    assert hub_page._get_install_count(REFERRAL_ID) == 0


def test_tab_impact_dash_badges_reflect_the_hub_install_count(rf):
    """End-to-end: /invite/?ref_key=... -> install_count -> achieved badges.

    Catches a rename of the context key on only one side of the boundary.
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)
    FirefoxReferralData.objects.create(referral_id="TEST00000000000A", install_count=12)

    context = hub_page.get_context(rf.get("/invite/?ref_key=TEST00000000000A"))
    assert context["install_count"] == 12

    block = TabBlock()
    html = block.render(_impact_dash_tab_value(), context={**context, "section_id": "hub", "tab_index": 1})
    badges = BeautifulSoup(html, "html.parser").select("ul.fl-impact-dash li.fl-badge")

    # 12 installs clears the 1 and 5 milestones but not 25.
    assert [b.get("data-achieved") for b in badges] == ["true", "true", "false"]


def test_tab_impact_dash_all_locked_when_hub_opened_without_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/"))

    block = TabBlock()
    html = block.render(_impact_dash_tab_value(), context={**context, "section_id": "hub", "tab_index": 1})
    soup = BeautifulSoup(html, "html.parser")

    # The badges still render -- they are the goal to work towards -- but none
    # are achieved.
    assert len(soup.select("li.fl-badge")) == 3
    assert soup.select("li.fl-badge.is-achieved") == []


# Hub: a malformed or missing ref_key is not found


@pytest.mark.parametrize(
    ("query", "why"),
    [
        ("", "no query string at all"),
        ("?ref_key=", "present but blank"),
        ("?ref_key=TEST23456X", "too short"),
        ("?ref_key=TEST23456X000000Y", "too long"),
        ("?ref_key=test23456x000000", "lowercase"),
        ("?ref_key=TESTIIIIIIIIIIII", "ambiguous Crockford letter"),
        ("?ref_key=TEST-23456X00000", "punctuation"),
        ("?other=TEST23456X000000", "wrong parameter name"),
    ],
)
def test_hub_page_serve_raises_404_for_unusable_ref_key(rf, query, why):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    with pytest.raises(Http404):
        hub_page.serve(rf.get(f"/invite/{query}"))


def test_hub_page_serve_succeeds_for_a_well_formed_ref_key(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # The locale prefix matters: l10n_utils.render redirects to add one when the
    # path has none, so an unprefixed path would return 302 before rendering.
    response = hub_page.serve(rf.get(f"/en-US/invite/?ref_key={REFERRAL_ID}"))

    assert response.status_code == 200


def test_hub_page_serve_does_not_require_the_ref_key_to_exist_in_the_database(rf):
    """The hub still renders for a well-formed but unknown key.

    Only the shape is enforced here; an unknown key simply has no installs, so
    the badges stay locked. Enforcing existence would 404 a referrer whose row
    has not been created yet.
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    response = hub_page.serve(rf.get(f"/en-US/invite/?ref_key={UNKNOWN_REFERRAL_ID}"))

    assert response.status_code == 200


def test_hub_page_get_context_stays_tolerant_of_a_missing_ref_key(rf):
    """serve() is the gate; get_context must not raise on its own.

    It is called directly by the context-dump template and by CMS preview, both
    of which have no ref_key.
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/invite/"))

    assert context["invite_url"] == ""
    assert context["install_count"] == 0


# Invitee page: an unusable invite code goes to the localized home page


def _get_firefox_page():
    site = Site.objects.get(is_default_site=True)
    return ReferralGetFirefoxPageFactory(parent=site.root_page)


@pytest.mark.parametrize(
    ("query", "why"),
    [
        ("", "no query string at all"),
        ("?invitation=", "present but blank"),
        ("?invitation=SHORT", "too short"),
        ("?invitation=10123456789ABCDEFG", "too long"),
        ("?invitation=1-123456789ABCDEF", "punctuation"),
        ("?invitation=Z0123456789ABCDEF", "key version not in the keyring"),
        ("?other=10123456789ABCDEF", "wrong parameter name"),
    ],
)
def test_get_firefox_page_redirects_home_for_malformed_invite_code(rf, query, why):
    page = _get_firefox_page()

    response = page.serve(rf.get(f"/get-firefox/{query}"))

    assert response.status_code == 302
    assert response["Location"] == "/en-US/"


def test_get_firefox_page_redirects_home_for_unknown_invite_code(rf):
    """Well-formed but naming a referral that does not exist.

    Any well-formed code decrypts to some referral ID -- there is no integrity
    check in the cipher -- so existence has to be settled against the table.
    """
    page = _get_firefox_page()
    code = crypto.referral_id_to_invite_code(UNKNOWN_REFERRAL_ID)

    response = page.serve(rf.get(f"/get-firefox/?invitation={code}"))

    assert response.status_code == 302
    assert response["Location"] == "/en-US/"


def test_get_firefox_page_serves_a_known_invite_code(rf):
    page = _get_firefox_page()
    FirefoxReferralData.objects.create(referral_id=REFERRAL_ID, install_count=342)

    # The code the hub would have generated for that referral ID.
    code = crypto.referral_id_to_invite_code(REFERRAL_ID)
    response = page.serve(rf.get(f"/en-US/get-firefox/?invitation={code}"))

    assert response.status_code == 200


@pytest.mark.parametrize("style", ["lowercase", "surrounding whitespace"])
def test_get_firefox_page_accepts_a_code_that_only_needs_normalizing(rf, style):
    """An invitee may retype or paste a code, so decoding folds case and trims.

    The hub's own ref_key stays strict -- it arrives machine-generated -- but the
    invitation is handled by a person and must survive their copy and paste.
    """
    page = _get_firefox_page()
    FirefoxReferralData.objects.create(referral_id=REFERRAL_ID, install_count=342)

    code = crypto.referral_id_to_invite_code(REFERRAL_ID)
    typed = code.lower() if style == "lowercase" else f"  {code} "

    response = page.serve(rf.get("/en-US/get-firefox/", {"invitation": typed}))

    assert response.status_code == 200


def test_get_firefox_page_redirect_uses_the_visitor_locale(rf):
    """A non-English visitor must not be forced into /en-US/."""
    page = _get_firefox_page()
    request = rf.get("/get-firefox/")
    request.locale = "de"

    response = page.serve(request)

    assert response["Location"] == "/de/"


def test_get_firefox_page_allows_the_visitor_through_when_database_errors(monkeypatch, rf):
    """Fail open: a referral-table outage must not break the invitee funnel."""
    page = _get_firefox_page()
    code = crypto.referral_id_to_invite_code(REFERRAL_ID)

    def boom(*args, **kwargs):
        raise DatabaseError("relation does not exist")

    monkeypatch.setattr(FirefoxReferralData.objects, "filter", boom)

    response = page.serve(rf.get(f"/en-US/get-firefox/?invitation={code}"))

    assert response.status_code == 200


def test_get_firefox_page_still_rejects_malformed_codes_when_database_errors(monkeypatch, rf):
    """Failing open applies to verification only, not to the shape check."""
    page = _get_firefox_page()

    def boom(*args, **kwargs):
        raise DatabaseError("relation does not exist")

    monkeypatch.setattr(FirefoxReferralData.objects, "filter", boom)

    response = page.serve(rf.get("/get-firefox/?invitation=nope"))

    assert response.status_code == 302


def test_get_firefox_page_does_not_report_a_missing_invitation_to_sentry(rf):
    """A visitor with no invitation is ordinary traffic, not a decode failure."""
    page = _get_firefox_page()

    with patch("springfield.firefox.referral.crypto.capture_message") as capture:
        page.serve(rf.get("/get-firefox/"))

    assert capture.call_count == 0


def test_hub_page_404_is_exempt_from_locale_fallback_redirection(rf):
    """Regression: /en-US/invite/ with no ref_key must not redirect-loop.

    CMSLocaleFallbackMiddleware turns a 404 into a redirect when a live page
    exists at the same path in an acceptable locale. For a page that 404s its own
    request that page is itself, so without the exemption the middleware
    redirects to /en-US/invite/ forever (ERR_TOO_MANY_REDIRECTS).
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    def get_response(request):
        try:
            return hub_page.serve(request)
        except Http404:
            return HttpResponseNotFound("not found")

    for query in ["", "?ref_key=", "?ref_key=nope"]:
        request = rf.get(f"/en-US/invite/{query}")
        response = CMSLocaleFallbackMiddleware(get_response)(request)

        assert response.status_code == 404, query
        assert "Location" not in response, query
