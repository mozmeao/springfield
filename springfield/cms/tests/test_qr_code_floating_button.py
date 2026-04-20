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
from springfield.cms.models.snippets import QRCodeFloatingSnippet
from springfield.cms.qr import resolve_qr_source
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
    """Return a mock image object with a file.url attribute, for resolve_qr_source unit tests."""
    return types.SimpleNamespace(file=types.SimpleNamespace(url=url))


def _make_page(**kwargs):
    """Return a mock page with empty override fields by default."""
    defaults = {"override_url": "", "override_image": None, "override_default_open": None}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_snippet(**kwargs):
    """Return a mock snippet with a URL source and default_open=True by default."""
    defaults = {"url": "https://www.firefox.com/mobile/", "image": None, "default_open": True}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


PAGES_WITH_FLOATING_QR = [
    get_thanks_page,
    get_freeform_page_2026_with_qr_snippet,
    get_whats_new_page_with_qr_snippet,
    get_whats_new_page_2026_with_qr_snippet,
]


# ==========================================
# Section 1: resolve_qr_source unit tests
# ==========================================
# These tests use SimpleNamespace objects so no database access is needed.
# resolve_qr_source() uses only getattr(), so mock objects work perfectly.


def test_resolve_qr_source_url_from_snippet():
    snippet = _make_snippet(url="https://firefox.com", image=None)
    page = _make_page()
    assert resolve_qr_source(page, snippet) == {"type": "qr", "value": "https://firefox.com", "open": True}


def test_resolve_qr_source_image_from_snippet():
    image = _make_image("https://cdn.example.com/qr.png")
    snippet = _make_snippet(url="", image=image)
    page = _make_page()
    assert resolve_qr_source(page, snippet) == {"type": "image", "value": "https://cdn.example.com/qr.png", "open": True}


def test_resolve_qr_source_image_takes_precedence_over_url():
    """When the snippet has both url and image, image wins."""
    image = _make_image("https://cdn.example.com/qr.png")
    snippet = _make_snippet(url="https://firefox.com", image=image)
    result = resolve_qr_source(_make_page(), snippet)
    assert result["type"] == "image"
    assert result["value"] == "https://cdn.example.com/qr.png"


def test_resolve_qr_source_override_url_takes_precedence_over_snippet_url():
    """Page override_url takes precedence over snippet url."""
    snippet = _make_snippet(url="https://firefox.com")
    page = _make_page(override_url="https://override.example.com")
    result = resolve_qr_source(page, snippet)
    assert result == {"type": "qr", "value": "https://override.example.com", "open": True}


def test_resolve_qr_source_override_image_takes_precedence_over_snippet_image():
    """Page override_image takes precedence over snippet image."""
    snippet = _make_snippet(url="", image=_make_image("https://cdn.example.com/snippet.png"))
    page = _make_page(override_image=_make_image("https://cdn.example.com/override.png"))
    result = resolve_qr_source(page, snippet)
    assert result["type"] == "image"
    assert result["value"] == "https://cdn.example.com/override.png"


def test_resolve_qr_source_snippet_image_beats_page_override_url():
    """Image always wins over URL regardless of source — snippet image beats page override_url."""
    snippet = _make_snippet(url="", image=_make_image("https://cdn.example.com/snippet.png"))
    page = _make_page(override_url="https://override.example.com")
    result = resolve_qr_source(page, snippet)
    assert result["type"] == "image"


def test_resolve_qr_source_page_override_image_beats_snippet_url():
    """Page override_image wins even when the snippet has only a URL and no image."""
    snippet = _make_snippet(url="https://firefox.com", image=None)
    page = _make_page(override_image=_make_image("https://cdn.example.com/override.png"))
    result = resolve_qr_source(page, snippet)
    assert result["type"] == "image"
    assert result["value"] == "https://cdn.example.com/override.png"


def test_resolve_qr_source_override_default_open_true_overrides_snippet_false():
    snippet = _make_snippet(default_open=False)
    result = resolve_qr_source(_make_page(override_default_open=True), snippet)
    assert result["open"] is True


def test_resolve_qr_source_override_default_open_false_overrides_snippet_true():
    snippet = _make_snippet(default_open=True)
    result = resolve_qr_source(_make_page(override_default_open=False), snippet)
    assert result["open"] is False


def test_resolve_qr_source_override_default_open_none_uses_snippet_value():
    """When override_default_open is None, the snippet's own default_open is used."""
    snippet = _make_snippet(default_open=False)
    result = resolve_qr_source(_make_page(override_default_open=None), snippet)
    assert result["open"] is False


def test_resolve_qr_source_returns_none_when_neither_url_nor_image():
    snippet = _make_snippet(url="", image=None)
    page = _make_page(override_url="", override_image=None)
    assert resolve_qr_source(page, snippet) is None


def test_resolve_qr_source_page_without_any_override_attrs_falls_back_to_snippet():
    """A page with no override_* attributes at all uses snippet values via getattr fallback."""
    snippet = _make_snippet(url="https://firefox.com")
    page = types.SimpleNamespace()  # no override_url, override_image, override_default_open
    result = resolve_qr_source(page, snippet)
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
def test_page_clean_raises_when_both_override_url_and_image_set(get_page_fn, minimal_site):
    image, _, _, _ = get_placeholder_images()
    page = get_page_fn()
    page.override_url = "https://override.example.com"
    page.override_image = image
    with pytest.raises(ValidationError, match="Only one of override_url and override_image is allowed"):
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
def test_page_clean_passes_with_override_url_only(get_page_fn, minimal_site):
    page = get_page_fn()
    page.override_url = "https://override.example.com"
    page.override_image = None
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
def test_page_clean_passes_with_override_image_only(get_page_fn, minimal_site):
    image, _, _, _ = get_placeholder_images()
    page = get_page_fn()
    page.override_url = ""
    page.override_image = image
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
    PAGES_WITH_FLOATING_QR + [get_whats_new_page_with_qr_snippet],
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
    """Setting page.override_image causes an <img> to render instead of an SVG."""
    image, _, _, _ = get_placeholder_images()
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    page.override_image = image

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
    page.override_default_open = None  # don't override; use snippet's default_open=True

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside
    assert "is-open" in aside.get("class", []), "is-open class should be present when default_open=True"


@pytest.mark.parametrize("get_page_fn", PAGES_WITH_FLOATING_QR)
def test_floating_snippet_no_is_open_class_when_override_default_open_false(get_page_fn, minimal_site, rf):
    """Page override_default_open=False overrides the snippet's default_open=True."""
    page = get_page_fn()
    page.show_floating_qr_code_snippet = True
    page.override_default_open = False

    soup = BeautifulSoup(_serve_page(page, rf).content, "html.parser")
    aside = _get_floating_qr_aside(soup)
    assert aside
    assert "is-open" not in aside.get("class", []), "is-open class should not be present when override_default_open=False"


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


def test_floating_snippet_tag_returns_live_snippet(minimal_site):
    snippet = get_floating_qr_code_snippet()
    locale = Locale.objects.get(language_code="en-US")
    context = {"page": types.SimpleNamespace(locale=locale)}
    assert floating_snippet_tag(context) == snippet


def test_floating_snippet_tag_returns_none_when_no_snippet_exists(minimal_site):
    QRCodeFloatingSnippet.objects.all().delete()
    locale = Locale.objects.get(language_code="en-US")
    context = {"page": types.SimpleNamespace(locale=locale)}
    assert floating_snippet_tag(context) is None


def test_floating_snippet_tag_uses_self_locale_as_fallback(minimal_site):
    """Falls back to context["self"].locale when context["page"] is absent."""
    snippet = get_floating_qr_code_snippet()
    locale = Locale.objects.get(language_code="en-US")
    context = {"self": types.SimpleNamespace(locale=locale)}
    assert floating_snippet_tag(context) == snippet


def test_floating_snippet_tag_returns_none_when_no_locale_in_context(minimal_site):
    get_floating_qr_code_snippet()  # ensure a snippet exists
    assert floating_snippet_tag({}) is None
