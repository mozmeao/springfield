# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch
from urllib.parse import parse_qs

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import Http404, HttpResponseNotFound

import pytest
from bs4 import BeautifulSoup
from waffle.testutils import override_switch
from wagtail.models import Site

from springfield.cms.blocks import TabBlock
from springfield.cms.middleware import CMSLocaleFallbackMiddleware
from springfield.cms.tests.factories import ReferralGetFirefoxPageFactory, ReferralHubPageFactory
from springfield.firefox.referral import crypto
from springfield.firefox.referral.models import FirefoxReferralData
from springfield.firefox.referral.utils import REFERRAL_ID_LENGTH

pytestmark = [pytest.mark.django_db]

CAPTURE_MESSAGE = "springfield.cms.models.pages.capture_message"
GEO_MOCK = "springfield.cms.models.pages.get_country_from_request"


@pytest.fixture(autouse=True)
def _default_geo_us():
    """All referral-page serve() calls see country 'US' unless overridden."""
    with patch(GEO_MOCK, return_value="US"):
        yield


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

    # Right length, but `I` is not a Crockford symbol, so this is the shape that
    # serve() reports. Reaching get_context with it means serve() was skipped
    # (CMS preview, serve_password_required_response), which is not the referral
    # flow, so it is treated like a missing ref_key and reported nowhere.
    with patch(CAPTURE_MESSAGE) as capture:
        context = hub_page.get_context(rf.get("/invite/?ref_key=A7B9K2M4PXQRSTVI"))

    assert context["invite_url"] == ""
    assert capture.call_count == 0


def test_hub_page_returns_install_count_of_zero_for_ref_key_with_no_data_match(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    # Anything can land in a public query string, so a ref_key that is not even
    # the right length is ignored rather than filling Sentry with scanner noise.
    _unused_id = "TESTTESTTESTTEST"
    assert len(_unused_id) == REFERRAL_ID_LENGTH
    assert not FirefoxReferralData.objects.filter(referral_id=_unused_id).exists()
    context = hub_page.get_context(rf.get(f"/invite/?ref_key={_unused_id}"))

    assert context["install_count"] == 0


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


@pytest.mark.parametrize("referral_id", [None, ""])
def test_hub_page_install_count_zero_without_referral_id(referral_id):
    hub_page = ReferralHubPageFactory.build()
    assert hub_page._get_install_count(referral_id) == 0


def test_hub_page_install_count_zero_when_database_errors(monkeypatch):
    """The impact dashboard is optional and must not be able to fail the page."""
    hub_page = ReferralHubPageFactory.build()

    def boom(*args, **kwargs):
        raise DatabaseError("relation does not exist")

    monkeypatch.setattr(FirefoxReferralData.objects, "get", boom)

    with patch(CAPTURE_MESSAGE) as capture:
        result = hub_page._get_install_count(REFERRAL_ID)

    assert result == 0
    assert capture.call_count == 1


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


@pytest.mark.parametrize(
    ("ref_key", "reports"),
    [
        # Right length but `I` is not a Crockford symbol, so this plausibly came
        # from the referral flow and is worth a Sentry warning.
        ("A7B9K2M4PXQRSTVI", True),
        # Anything can land in a public query string, so a ref_key that is not
        # even the right length is ignored rather than filling Sentry with
        # scanner noise. Length is the only axis the prefilter looks at, so one
        # case pins it.
        ("junk", False),
    ],
)
def test_hub_page_serve_reports_only_a_correctly_sized_invalid_ref_key(rf, ref_key, reports):
    """serve() is the only gate every public request passes, so it reports."""
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    with patch(CAPTURE_MESSAGE) as capture:
        with pytest.raises(Http404):
            hub_page.serve(rf.get(f"/invite/?ref_key={ref_key}"))

    assert capture.call_count == (1 if reports else 0)
    if reports:
        assert capture.call_args.kwargs["level"] == "warning"


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


def _showcase_block(block_id, headline):
    """Minimal showcase StreamField dict, enough for the template to emit a heading."""
    return {
        "type": "showcase",
        "id": block_id,
        "value": {
            "settings": {"layout": "default"},
            "headline": f'<p data-block-key="a">{headline}</p>',
            "media": [],
        },
    }


def test_hub_page_renders_exactly_one_h1(rf):
    """The pre-footer showcase must not restart the heading levels.

    Its heading counter lives in a separate Jinja block from the main content's,
    so a level reset there would give the page a second h1.
    """
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)
    hub_page.upper_content = [_showcase_block("aa000000-0000-0000-0000-000000000001", "Invite your friends")]
    hub_page.extra_content = [_showcase_block("aa000000-0000-0000-0000-000000000002", "Get Firefox everywhere")]
    hub_page.save()

    response = hub_page.serve(rf.get(f"/en-US/invite/?ref_key={REFERRAL_ID}"))
    soup = BeautifulSoup(response.content, "html.parser")

    assert [h.get_text(strip=True) for h in soup.find_all("h1")] == ["Invite your friends"]

    pre_footer = soup.select_one(".fl-split-page-extra")
    assert pre_footer.find("h2").get_text(strip=True) == "Get Firefox everywhere"


# Invitee page: an unusable invite code is not found


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
def test_get_firefox_page_raises_404_for_malformed_invite_code(rf, query, why):
    page = _get_firefox_page()

    with pytest.raises(Http404):
        page.serve(rf.get(f"/get-firefox/{query}"))


def test_get_firefox_page_serves_a_known_invite_code(rf):
    page = _get_firefox_page()

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

    code = crypto.referral_id_to_invite_code(REFERRAL_ID)
    typed = code.lower() if style == "lowercase" else f"  {code} "

    response = page.serve(rf.get("/en-US/get-firefox/", {"invitation": typed}))

    assert response.status_code == 200


def test_get_firefox_page_get_context_includes_invitation_code(rf):
    page = _get_firefox_page()
    code = crypto.referral_id_to_invite_code(REFERRAL_ID)

    context = page.get_context(rf.get(f"/en-US/get-firefox/?invitation={code}"))

    assert context["invitation_code"] == code


def test_get_firefox_page_get_context_invitation_code_none_when_absent(rf):
    """get_context is called directly by CMS preview without serve() gating it."""
    page = _get_firefox_page()

    context = page.get_context(rf.get("/en-US/get-firefox/"))

    assert context["invitation_code"] is None


def test_get_firefox_page_still_rejects_malformed_codes(rf):
    page = _get_firefox_page()

    with pytest.raises(Http404):
        page.serve(rf.get("/get-firefox/?invitation=nope"))


def test_get_firefox_page_does_not_report_a_missing_invitation_to_sentry(rf):
    """A visitor with no invitation is ordinary traffic, not a decode failure."""
    page = _get_firefox_page()

    with patch("springfield.firefox.referral.crypto.capture_message") as capture:
        with pytest.raises(Http404):
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


def test_get_firefox_page_404_is_exempt_from_locale_fallback_redirection(rf):
    """Regression: /en-US/get-firefox/ with no invitation must not redirect-loop."""
    page = _get_firefox_page()

    def get_response(request):
        try:
            return page.serve(request)
        except Http404:
            return HttpResponseNotFound("not found")

    for query in ["", "?invitation=", "?invitation=nope"]:
        request = rf.get(f"/en-US/get-firefox/{query}")
        response = CMSLocaleFallbackMiddleware(get_response)(request)

        assert response.status_code == 404, query
        assert "Location" not in response, query


# Geo lockout


@pytest.mark.parametrize(
    ("page_factory", "valid_query"),
    [
        (ReferralHubPageFactory, f"?ref_key={REFERRAL_ID}"),
        (ReferralGetFirefoxPageFactory, "?invitation=PLACEHOLDER"),
    ],
)
def test_referral_pages_geo_lockout_redirects_to_firefox_homepage(rf, page_factory, valid_query, settings):
    site = Site.objects.get(is_default_site=True)
    page = page_factory(parent=site.root_page)

    with patch(GEO_MOCK, return_value="DE"):
        request = rf.get(f"/en-US/invite/{valid_query}")
        request.locale = "en-US"
        response = page.serve(request)

    assert response.status_code == 302
    assert response["Location"] == "/en-US/"


@pytest.mark.parametrize("locale", ["en-US", "en-CA", "de"])
def test_hub_page_geo_lockout_fires_before_ref_key_validation(rf, settings, locale):
    """A geo-locked visitor with a bad ref_key gets the geo redirect, not a 404."""
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    with patch(GEO_MOCK, return_value="DE"):
        request = rf.get(f"/{locale}/invite/?ref_key=bad")
        request.locale = locale
        response = hub_page.serve(request)

    assert response.status_code == 302
    assert response["Location"] == f"/{locale}/"


@pytest.mark.parametrize("locale", ["en-US", "en-CA", "de"])
def test_get_firefox_page_geo_lockout_fires_before_invitation_validation(rf, settings, locale):
    """A geo-locked visitor with a bad invitation gets the geo redirect, not a 404."""
    page = _get_firefox_page()

    with patch(GEO_MOCK, return_value="DE"):
        request = rf.get(f"/{locale}/get-firefox/?invitation=bad")
        request.locale = locale
        response = page.serve(request)

    assert response.status_code == 302
    assert response["Location"] == f"/{locale}/"


# Attribution context


def test_get_firefox_page_get_context_includes_utm_parameters(rf):
    """The referral page context must include utm_parameters with the referral
    campaign so the download-firefox-button component builds an attributed
    Android Play Store URL for the server-rendered badge."""
    page = _get_firefox_page()
    code = crypto.referral_id_to_invite_code(REFERRAL_ID)

    context = page.get_context(rf.get(f"/en-US/get-firefox/?invitation={code}"))

    assert context["utm_parameters"]["utm_campaign"] == "firefox-referral"
    assert context["utm_parameters"]["utm_source"] == "www.firefox.com"
    assert context["utm_parameters"]["utm_medium"] == "referral"


def test_get_firefox_page_get_context_channel_defaults_to_release(rf):
    """Without the REFERRAL_FORCE_NIGHTLY_QA switch active, the download CTA
    must build a Release Bouncer link, as it always has."""
    page = _get_firefox_page()
    code = crypto.referral_id_to_invite_code(REFERRAL_ID)

    with patch("springfield.base.waffle.switch_is_active", return_value=False):
        context = page.get_context(rf.get(f"/en-US/get-firefox/?invitation={code}"))

    assert context["channel"] == "release"


def test_get_firefox_page_get_context_channel_forced_to_nightly_by_switch(rf):
    """QA-only override (WT-1281): the REFERRAL_FORCE_NIGHTLY_QA switch forces
    the download CTA to build a Nightly Bouncer link instead of Release."""
    page = _get_firefox_page()
    code = crypto.referral_id_to_invite_code(REFERRAL_ID)

    with patch("springfield.base.waffle.switch_is_active", return_value=True):
        context = page.get_context(rf.get(f"/en-US/get-firefox/?invitation={code}"))

    assert context["channel"] == "nightly"


@override_switch("REFERRAL_FORCE_NIGHTLY_QA", active=False)
def test_get_firefox_page_renders_download_button(client, settings):
    """The referral page template must render an actual download button (not the
    context-dump skeleton) so the referral-attribution JS has a link to decorate."""
    settings.STUB_ATTRIBUTION_RATE = 1
    settings.STUB_ATTRIBUTION_HMAC_KEY = "test-hmac-key"

    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page, slug="get-firefox")
    # Populate the StreamField so the referral download CTA block is rendered.
    # An empty content field produces only the context-dump skeleton with no
    # download links, which means the referral-attribution JS has nothing to decorate.
    page.upper_content = [
        {
            "type": "intro",
            "id": "aa000000-0000-0000-0000-000000000001",
            "value": {
                "settings": {"slim": False},
                "heading": {
                    "superheading_text": '<p data-block-key="a"></p>',
                    "heading_text": '<p data-block-key="b">Download Firefox</p>',
                    "subheading_text": '<p data-block-key="c"></p>',
                },
                "buttons": [
                    {
                        "type": "referral_download",
                        "id": "bb000000-0000-0000-0000-000000000001",
                        "value": {},
                    }
                ],
            },
        }
    ]
    page.save()

    code = crypto.referral_id_to_invite_code(REFERRAL_ID)
    with patch(GEO_MOCK, return_value="US"), patch("springfield.base.waffle.switch_is_active", return_value=False):
        response = client.get(f"/en-US/get-firefox/?invitation={code}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")

    # A .download-link element (required by stub attribution JS) must be present.
    assert soup.find(class_="download-link") is not None

    # The referral consent checkbox must exist (hidden by default; JS reveals it).
    checkbox = soup.find("input", {"class": "referral-consent-checkbox"})
    assert checkbox is not None

    # The data-referral-code attribute must carry the invitation code.
    referral_root = soup.find(attrs={"data-referral-code": True})
    assert referral_root is not None
    assert referral_root["data-referral-code"] == code

    # The Android Play Store badge must default to the Release app.
    android_badge = soup.find(class_="fl-store-button-android")
    assert android_badge is not None
    assert "id=org.mozilla.firefox" in android_badge["href"]


def test_get_firefox_page_renders_nightly_download_link_when_switch_active(client, settings):
    """QA-only override (WT-1281): with REFERRAL_FORCE_NIGHTLY_QA active, the
    rendered download button(s) must point at a Nightly Bouncer product,
    not Release."""
    settings.STUB_ATTRIBUTION_RATE = 1
    settings.STUB_ATTRIBUTION_HMAC_KEY = "test-hmac-key"

    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page, slug="get-firefox")
    page.upper_content = [
        {
            "type": "intro",
            "id": "aa000000-0000-0000-0000-000000000001",
            "value": {
                "settings": {"slim": False},
                "heading": {
                    "superheading_text": '<p data-block-key="a"></p>',
                    "heading_text": '<p data-block-key="b">Download Firefox</p>',
                    "subheading_text": '<p data-block-key="c"></p>',
                },
                "buttons": [
                    {
                        "type": "referral_download",
                        "id": "bb000000-0000-0000-0000-000000000001",
                        "value": {},
                    }
                ],
            },
        }
    ]
    page.save()

    code = crypto.referral_id_to_invite_code(REFERRAL_ID)
    with patch(GEO_MOCK, return_value="US"), patch("springfield.base.waffle.switch_is_active", return_value=True):
        response = client.get(f"/en-US/get-firefox/?invitation={code}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")

    download_link = soup.find(class_="download-link")
    assert download_link is not None
    assert "firefox-nightly" in download_link["data-direct-link"]

    # The Android Play Store badge must point at the separate Nightly listing.
    android_badge = soup.find(class_="fl-store-button-android")
    assert android_badge is not None
    assert "id=org.mozilla.fenix" in android_badge["href"]


# Duplicate-block validation


def _intro_block_with_referral_download(block_id, btn_id):
    """Minimal intro block StreamField dict carrying one referral_download button."""
    return {
        "type": "intro",
        "id": block_id,
        "value": {
            "settings": {"slim": False},
            "heading": {
                "superheading_text": '<p data-block-key="a"></p>',
                "heading_text": '<p data-block-key="b">Download Firefox</p>',
                "subheading_text": '<p data-block-key="c"></p>',
            },
            "buttons": [
                {"type": "referral_download", "id": btn_id, "value": {}},
            ],
        },
    }


def test_get_firefox_page_clean_rejects_duplicate_referral_download_blocks():
    """Two referral download CTAs on the same page produce duplicate HTML IDs.

    Wagtail permits the block more than once, so the page model enforces the
    single-instance constraint in clean() before the content can be published.
    """
    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page)
    page.upper_content = [
        _intro_block_with_referral_download(
            "aa000000-0000-0000-0000-000000000001",
            "bb000000-0000-0000-0000-000000000001",
        ),
        _intro_block_with_referral_download(
            "aa000000-0000-0000-0000-000000000002",
            "bb000000-0000-0000-0000-000000000002",
        ),
    ]

    with pytest.raises(ValidationError) as exc_info:
        page.clean()

    assert "upper_content" in exc_info.value.message_dict


def test_get_firefox_page_clean_accepts_a_single_referral_download_block():
    """A single referral download CTA passes clean() without error."""
    site = Site.objects.get(is_default_site=True)
    page = ReferralGetFirefoxPageFactory(parent=site.root_page)
    page.upper_content = [
        _intro_block_with_referral_download(
            "aa000000-0000-0000-0000-000000000001",
            "bb000000-0000-0000-0000-000000000001",
        ),
    ]

    page.clean()  # must not raise
