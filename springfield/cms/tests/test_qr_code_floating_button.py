# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import types

from django.core.exceptions import ValidationError

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.fixtures.freeformpage_2026 import get_freeform_page_2026_with_qr_snippet
from springfield.cms.fixtures.snippet_fixtures import get_floating_qr_code_snippet
from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page
from springfield.cms.fixtures.whats_new_page_fixtures import (
    get_whats_new_page_2026_with_qr_snippet,
    get_whats_new_page_with_qr_snippet,
)
from springfield.cms.models.pages import FreeFormPage2026, ThanksPage, WhatsNewPage, WhatsNewPage2026
from springfield.cms.models.snippets import QRCodeFloatingSnippet
from springfield.cms.templatetags.cms_tags import (
    get_floating_qr_code_snippet as floating_snippet_tag,
)

pytestmark = [pytest.mark.django_db]


# ==========================================
# Helpers
# ==========================================


def _get_floating_qr_aside(soup):
    return soup.find("aside", class_="fl-qr-code-floating-snippet")


def _serve_page(page, rf):
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200
    return response


def _make_image(url="https://example.com/qr.png"):
    """Return a mock image object with a file.url attribute, for QRCodeFloatingSnippet.resolve_qr_source unit tests."""
    return types.SimpleNamespace(file=types.SimpleNamespace(url=url))


def _make_page(**kwargs):
    """Return a mock page with empty floating QR override fields by default."""
    defaults = {"floating_qr_url": "", "floating_qr_image": None, "floating_qr_default_open": None}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


PAGES_WITH_FLOATING_QR = [
    get_thanks_page,
    get_freeform_page_2026_with_qr_snippet,
    get_whats_new_page_with_qr_snippet,
    get_whats_new_page_2026_with_qr_snippet,
]


# ==========================================
# Section 1: QRCodeFloatingSnippet.resolve_qr_source unit tests
# ==========================================
# Tests that only need URL fields use unsaved QRCodeFloatingSnippet instances (no DB).
# Tests that need snippet.image use a real DB image via get_placeholder_images().


def test_resolve_qr_source_url_from_snippet():
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=True)
    result = snippet.resolve_qr_source(_make_page())
    assert result == {"type": "qr", "value": "https://firefox.com", "open": True}


def test_resolve_qr_source_image_from_snippet(minimal_site):
    image, _, _, _ = get_placeholder_images()
    snippet = QRCodeFloatingSnippet(url="", default_open=True)
    snippet.image = image
    result = snippet.resolve_qr_source(_make_page())
    assert result == {"type": "image", "value": image.file.url, "open": True}


def test_resolve_qr_source_image_takes_precedence_over_url(minimal_site):
    """When the snippet has both url and image, image wins."""
    image, _, _, _ = get_placeholder_images()
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", default_open=True)
    snippet.image = image
    result = snippet.resolve_qr_source(_make_page())
    assert result["type"] == "image"
    assert result["value"] == image.file.url


def test_resolve_qr_source_floating_qr_url_takes_precedence_over_snippet_url():
    """Page floating_qr_url takes precedence over snippet url."""
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=True)
    page = _make_page(floating_qr_url="https://override.example.com")
    result = snippet.resolve_qr_source(page)
    assert result == {"type": "qr", "value": "https://override.example.com", "open": True}


def test_resolve_qr_source_floating_qr_image_takes_precedence_over_snippet_image(minimal_site):
    """Page floating_qr_image takes precedence over snippet image."""
    image, _, _, _ = get_placeholder_images()
    snippet = QRCodeFloatingSnippet(url="", default_open=True)
    snippet.image = image
    page = _make_page(floating_qr_image=_make_image("https://cdn.example.com/override.png"))
    result = snippet.resolve_qr_source(page)
    assert result["type"] == "image"
    assert result["value"] == "https://cdn.example.com/override.png"


def test_resolve_qr_source_snippet_image_beats_page_floating_qr_url(minimal_site):
    """Image always wins over URL regardless of source — snippet image beats page floating_qr_url."""
    image, _, _, _ = get_placeholder_images()
    snippet = QRCodeFloatingSnippet(url="", default_open=True)
    snippet.image = image
    page = _make_page(floating_qr_url="https://override.example.com")
    result = snippet.resolve_qr_source(page)
    assert result["type"] == "image"


def test_resolve_qr_source_page_floating_qr_image_beats_snippet_url():
    """Page floating_qr_image wins even when the snippet has only a URL and no image."""
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=True)
    page = _make_page(floating_qr_image=_make_image("https://cdn.example.com/override.png"))
    result = snippet.resolve_qr_source(page)
    assert result["type"] == "image"
    assert result["value"] == "https://cdn.example.com/override.png"


def test_resolve_qr_source_floating_qr_default_open_true_overrides_snippet_false():
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=False)
    result = snippet.resolve_qr_source(_make_page(floating_qr_default_open=True))
    assert result["open"] is True


def test_resolve_qr_source_floating_qr_default_open_false_overrides_snippet_true():
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=True)
    result = snippet.resolve_qr_source(_make_page(floating_qr_default_open=False))
    assert result["open"] is False


def test_resolve_qr_source_floating_qr_default_open_none_uses_snippet_value():
    """When floating_qr_default_open is None, the snippet's own default_open is used."""
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=False)
    result = snippet.resolve_qr_source(_make_page(floating_qr_default_open=None))
    assert result["open"] is False


def test_resolve_qr_source_returns_none_when_neither_url_nor_image():
    snippet = QRCodeFloatingSnippet(url="", image=None, default_open=True)
    assert snippet.resolve_qr_source(_make_page(floating_qr_url="", floating_qr_image=None)) is None


def test_resolve_qr_source_page_without_any_floating_qr_attrs_falls_back_to_snippet():
    """A page with no floating_qr_* attributes at all uses snippet values via getattr fallback."""
    snippet = QRCodeFloatingSnippet(url="https://firefox.com", image=None, default_open=True)
    result = snippet.resolve_qr_source(types.SimpleNamespace())
    assert result == {"type": "qr", "value": "https://firefox.com", "open": True}


# ==========================================
# Section 2: QRCodeFloatingSnippet.clean()
# ==========================================


def test_snippet_clean_raises_when_no_url_and_no_image(minimal_site):
    snippet = QRCodeFloatingSnippet(
        locale=Locale.objects.get(language_code="en-US"),
        heading="<p>Test</p>",
        url="",
        image=None,
        default_open=True,
    )
    with pytest.raises(ValidationError, match="Missing url or image"):
        snippet.clean()


def test_snippet_clean_passes_with_url_only(minimal_site):
    snippet = QRCodeFloatingSnippet(
        locale=Locale.objects.get(language_code="en-US"),
        url="https://firefox.com",
        image=None,
    )
    snippet.clean()  # should not raise


def test_snippet_clean_passes_with_image_only(minimal_site):
    image, _, _, _ = get_placeholder_images()
    snippet = QRCodeFloatingSnippet(
        locale=Locale.objects.get(language_code="en-US"),
        url="",
        image=image,
    )
    snippet.clean()  # should not raise


def test_snippet_clean_passes_with_both_url_and_image(minimal_site):
    image, _, _, _ = get_placeholder_images()
    snippet = QRCodeFloatingSnippet(
        locale=Locale.objects.get(language_code="en-US"),
        url="https://firefox.com",
        image=image,
    )
    snippet.clean()  # should not raise


# ==========================================
# Section 3: Page clean() validation
# ==========================================


@pytest.mark.parametrize(
    "get_page_fn",
    [
        get_thanks_page,
        get_freeform_page_2026_with_qr_snippet,
        get_whats_new_page_with_qr_snippet,
        get_whats_new_page_2026_with_qr_snippet,
    ],
)
def test_page_clean_raises_when_both_floating_qr_url_and_image_set(get_page_fn, minimal_site):
    image, _, _, _ = get_placeholder_images()
    page = get_page_fn()
    page.floating_qr_url = "https://override.example.com"
    page.floating_qr_image = image
    with pytest.raises(ValidationError, match="Only one of floating_qr_url and floating_qr_image is allowed"):
        page.clean()


@pytest.mark.parametrize(
    "get_page_fn",
    [
        get_thanks_page,
        get_freeform_page_2026_with_qr_snippet,
        get_whats_new_page_with_qr_snippet,
        get_whats_new_page_2026_with_qr_snippet,
    ],
)
def test_page_clean_passes_with_floating_qr_url_only(get_page_fn, minimal_site):
    page = get_page_fn()
    page.floating_qr_url = "https://override.example.com"
    page.floating_qr_image = None
    page.clean()  # should not raise


@pytest.mark.parametrize(
    "get_page_fn",
    [
        get_thanks_page,
        get_freeform_page_2026_with_qr_snippet,
        get_whats_new_page_with_qr_snippet,
        get_whats_new_page_2026_with_qr_snippet,
    ],
)
def test_page_clean_passes_with_floating_qr_image_only(get_page_fn, minimal_site):
    image, _, _, _ = get_placeholder_images()
    page = get_page_fn()
    page.floating_qr_url = ""
    page.floating_qr_image = image
    page.clean()  # should not raise


# ==========================================
# Section 4: Page rendering integration tests
# ==========================================


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_qr_snippet_renders_when_flag_on(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside, "Floating QR <aside> should render when show_floating_qr_code_snippet=True"
    assert "Get Firefox on your phone" in aside.get_text()


@pytest.mark.parametrize(
    "get_page_fn",
    PAGES_WITH_FLOATING_QR,
)
def test_floating_qr_snippet_does_not_render_when_flag_off(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_floating_qr_code_snippet = False

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    assert not _get_floating_qr_aside(soup), "Floating QR <aside> should not render when show_floating_qr_code_snippet=False"


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_renders_svg_for_url_source(get_page_fn, minimal_site, rf):
    """Default fixture snippet has a URL, so an SVG QR code should be rendered."""
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside
    assert aside.find("svg"), "SVG should render when source is a URL"
    assert not aside.find("img"), "img tag should not render when source is a URL"


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_renders_img_for_image_override(get_page_fn, minimal_site, rf):
    """Setting page.floating_qr_image causes an <img> to render instead of an SVG."""
    image, _, _, _ = get_placeholder_images()
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    page.floating_qr_image = image

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside
    assert aside.find("img"), "img tag should render when source is an image"
    assert not aside.find("svg"), "SVG should not render when source is an image"


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_has_is_open_class_when_default_open_true(get_page_fn, minimal_site, rf):
    """Snippet fixture defaults to default_open=True; aside should have the is-open class."""
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    page.floating_qr_default_open = None  # don't override; use snippet's default_open=True

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside
    assert "is-open" in aside.get("class", []), "is-open class should be present when default_open=True"


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_no_is_open_class_when_floating_qr_default_open_false(get_page_fn, minimal_site, rf):
    """Page floating_qr_default_open=False overrides the snippet's default_open=True."""
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    page.floating_qr_default_open = False

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside
    assert "is-open" not in aside.get("class", []), "is-open class should not be present when floating_qr_default_open=False"


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_takes_precedence_over_non_floating(get_page_fn, minimal_site, rf):
    """When both flags are True, only the floating snippet renders (template uses elif)."""
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    page.show_qr_code_snippet = True

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    assert _get_floating_qr_aside(soup), "Floating snippet should render"
    assert not soup.find("aside", class_="fl-qr-code-snippet"), "Non-floating snippet should not also render"


# ==========================================
# Section 5: Template tag tests
# ==========================================


def test_floating_snippet_tag_returns_context_dict(minimal_site):
    get_floating_qr_code_snippet()
    locale = Locale.objects.get(language_code="en-US")
    context = {"page": types.SimpleNamespace(locale=locale)}
    result = floating_snippet_tag(context)
    assert result is not None
    assert set(result.keys()) == {"heading", "content", "qr"}


def test_floating_snippet_tag_returns_none_when_no_snippet_exists(minimal_site):
    QRCodeFloatingSnippet.objects.all().delete()
    locale = Locale.objects.get(language_code="en-US")
    context = {"page": types.SimpleNamespace(locale=locale)}
    assert floating_snippet_tag(context) is None


def test_floating_snippet_tag_uses_self_locale_as_fallback(minimal_site):
    """Falls back to context["self"].locale when context["page"] is absent."""
    get_floating_qr_code_snippet()
    locale = Locale.objects.get(language_code="en-US")
    context = {"self": types.SimpleNamespace(locale=locale)}
    result = floating_snippet_tag(context)
    assert result is not None
    assert set(result.keys()) == {"heading", "content", "qr"}


def test_floating_snippet_tag_returns_none_when_no_locale_in_context(minimal_site):
    get_floating_qr_code_snippet()  # ensure a snippet exists
    assert floating_snippet_tag({}) is None


def test_floating_snippet_tag_applies_page_overrides(minimal_site):
    """Page floating_qr_url override is reflected in the returned dict."""
    get_floating_qr_code_snippet()
    locale = Locale.objects.get(language_code="en-US")
    page = types.SimpleNamespace(
        locale=locale,
        floating_qr_url="https://override.example.com",
        floating_qr_image=None,
        floating_qr_default_open=None,
    )
    result = floating_snippet_tag({"page": page})
    assert result["qr"]["value"] == "https://override.example.com"


def test_floating_snippet_tag_no_page_overrides_when_page_missing(minimal_site):
    """When only self is in context, no page overrides are applied."""
    get_floating_qr_code_snippet()
    locale = Locale.objects.get(language_code="en-US")
    context = {"self": types.SimpleNamespace(locale=locale)}
    result = floating_snippet_tag(context)
    assert result is not None
    assert result["qr"] is not None


# ==========================================
# Section 6: QRCodeFloatingSnippet.build_context unit tests
# ==========================================
# These tests use unsaved QRCodeFloatingSnippet instances (no DB write needed).


def _make_real_snippet(**kwargs):
    defaults = {"url": "https://www.firefox.com/mobile/", "image": None, "default_open": True, "heading": "", "content": ""}
    defaults.update(kwargs)
    return QRCodeFloatingSnippet(**defaults)


def test_build_context_returns_expected_keys():
    snippet = _make_real_snippet()
    result = snippet.build_context(_make_page())
    assert set(result.keys()) == {"heading", "content", "qr"}


def test_build_context_qr_matches_resolve_qr_source():
    snippet = _make_real_snippet()
    page = _make_page()
    result = snippet.build_context(page)
    assert result["qr"] == snippet.resolve_qr_source(page)


def test_build_context_heading_and_content_from_snippet():
    snippet = _make_real_snippet(heading="<p>Scan me</p>", content="<p>Download Firefox</p>")
    result = snippet.build_context(_make_page())
    assert result["heading"] == "<p>Scan me</p>"
    assert result["content"] == "<p>Download Firefox</p>"


def test_build_context_qr_is_none_when_no_url_or_image():
    snippet = _make_real_snippet(url="", image=None)
    result = snippet.build_context(_make_page())
    assert result["qr"] is None


def test_build_context_with_no_page_falls_back_to_snippet():
    snippet = _make_real_snippet(url="https://firefox.com")
    result = snippet.build_context()
    assert result["qr"] == {"type": "qr", "value": "https://firefox.com", "open": True}


# ==========================================
# Section 7: get_context() context variable tests
# ==========================================


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_get_context_sets_hide_qr_snippet_from_cookie(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    rf.cookies["moz-qr-snippet-dismissed"] = "1"
    request = rf.get(page.get_full_url())
    context = page.get_context(request)
    assert context["hide_qr_snippet"] == "1"
    rf.cookies.pop("moz-qr-snippet-dismissed", None)


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_get_context_hide_qr_snippet_falsy_when_no_cookie(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    request = rf.get(page.get_full_url())
    context = page.get_context(request)
    assert not context["hide_qr_snippet"]


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_get_context_sets_floating_qr_snippet_when_flag_on(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    request = rf.get(page.get_full_url())
    context = page.get_context(request)
    assert "floating_qr_snippet" in context
    assert set(context["floating_qr_snippet"].keys()) == {"heading", "content", "qr"}


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_get_context_no_floating_qr_snippet_when_flag_off(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_floating_qr_code_snippet = False
    request = rf.get(page.get_full_url())
    context = page.get_context(request)
    assert "floating_qr_snippet" not in context


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_get_context_no_floating_qr_snippet_when_no_live_snippet(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    QRCodeFloatingSnippet.objects.all().delete()
    page.show_floating_qr_code_snippet = True
    request = rf.get(page.get_full_url())
    context = page.get_context(request)
    assert "floating_qr_snippet" not in context


# ==========================================
# Section 8: Cookie-based hiding (integration)
# ==========================================


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_not_rendered_when_dismissed_cookie_set(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    rf.cookies["moz-qr-snippet-dismissed"] = "1"
    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    assert not _get_floating_qr_aside(soup), "Floating QR <aside> should not render when dismissed cookie is set"
    rf.cookies.pop("moz-qr-snippet-dismissed", None)


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_rendered_without_dismissed_cookie(get_page_fn, minimal_site, rf):
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    assert _get_floating_qr_aside(soup), "Floating QR <aside> should render when dismissed cookie is absent"


# ==========================================
# Section 9: QRCodeFloatingSnippetMixin.override_translatable_fields
# ==========================================


@pytest.mark.parametrize("page_class", [ThanksPage, FreeFormPage2026, WhatsNewPage, WhatsNewPage2026])
def test_qr_mixin_override_translatable_fields_includes_slug_and_qr_fields(page_class):
    """Pages using QRCodeFloatingSnippetMixin must include slug (from AbstractSpringfieldCMSPage)
    alongside the three QR-specific synchronized fields."""
    field_names = {f.field_name for f in page_class.override_translatable_fields}
    assert "slug" in field_names
    assert "floating_qr_url" in field_names
    assert "floating_qr_image" in field_names
    assert "floating_qr_default_open" in field_names
