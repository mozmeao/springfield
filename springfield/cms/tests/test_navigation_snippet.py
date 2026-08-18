# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import translation

import pytest
from bs4 import BeautifulSoup
from PIL import Image as PILImage
from wagtail.models import Locale, Site

from lib.l10n_utils import fluent_l10n
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.navigation_fixtures import (
    build_column,
    build_folder,
    build_nav_link,
    build_separator,
    build_top_level_link,
    get_navigation_snippet,
    get_navigation_variants,
)
from springfield.cms.models import NavigationSnippet, SpringfieldImage
from springfield.cms.templatetags.cms_tags import add_utm_parameters
from springfield.cms.tests.factories import (
    FreeFormPage2026Factory,
    RoadmapPageFactory,
    StructuralPageFactory,
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
)
from springfield.firefox.templatetags.misc import slugify

pytestmark = [pytest.mark.django_db]

# Mirrors the utm_parameters set in cms/snippets/navigation-snippet.html, used to
# work out the expected href of links pointing at Mozilla-owned domains.
UTM_PARAMETERS = {
    "utm_source": "www.firefox.com",
    "utm_medium": "referral",
    "utm_campaign": "nav",
}


def render_navigation(snippet, request, language="en-US"):
    """Render the navigation snippet template in the given locale, as a BeautifulSoup document."""
    with translation.override(language):
        html = render_to_string(
            "cms/snippets/navigation-snippet.html",
            {
                "value": snippet,
                "request": request,
                "fluent_l10n": fluent_l10n(["en"], settings.FLUENT_DEFAULT_FILES),
            },
        )
    return BeautifulSoup(html, "html.parser")


def make_snippet(items):
    """Create and publish a NavigationSnippet with the given raw stream items."""
    snippet = NavigationSnippet.objects.create(locale=Locale.get_default(), name="Test navigation", items=items)
    snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet


def make_image(width, height, title="Logo"):
    """Create a SpringfieldImage of the given pixel dimensions."""
    buffer = BytesIO()
    PILImage.new("RGB", (width, height), (117, 79, 224)).save(buffer, format="PNG")
    buffer.seek(0)
    return SpringfieldImage.objects.create(title=title, file=ContentFile(buffer.read(), f"{title}.png"))


def render_preview(snippet, request):
    """Render the snippet PREVIEW (header + nav) to a BeautifulSoup document.

    Uses Wagtail's real preview code path so base-flare's context processors
    (settings, LANG, geo) are populated the same way they are in production.
    """
    with translation.override("en-US"):
        response = snippet.serve_preview(request, snippet.default_preview_mode)
        response.render()
    return BeautifulSoup(response.content.decode(), "html.parser")


def is_external(url):
    return url.startswith(("http://", "https://"))


def expected_href(url, utm_content=""):
    """The href a link should render, including the nav's UTM params for Mozilla domains."""
    return add_utm_parameters({"utm_parameters": {**UTM_PARAMETERS, "utm_content": utm_content}}, url)


def assert_link_icon(element, value):
    """Verify the optional leading/trailing icon of a nav link."""
    icon = value["icon"]
    if not icon:
        # No chosen icon: the only fl-icon allowed is the external-link arrow.
        chosen = [span for span in element.find_all("span", class_="fl-icon") if "fl-nav-icon-up-right-arrow" not in span.get("class", [])]
        assert chosen == [], "unexpected icon on a link with no icon set"
        return

    icon_span = element.find("span", class_=f"fl-icon-{icon}")
    assert icon_span is not None, f"missing icon fl-icon-{icon}"

    # icon_position controls whether the icon precedes or follows the label; compare
    # their positions among the link's children (the label is a text node).
    contents = element.contents
    icon_index = contents.index(icon_span)
    label_index = next(index for index, node in enumerate(contents) if isinstance(node, str) and value["custom_label"] in node)
    if value.get("icon_position") == "right":
        assert label_index < icon_index, "right-positioned icon should follow the label"
    else:
        assert icon_index < label_index, "left-positioned icon should precede the label"


def assert_external_and_target(element, value):
    """Verify the external-link arrow and new-tab behavior."""
    url = value["link"]["custom_url"]
    arrow = element.find("span", class_="fl-nav-icon-up-right-arrow")
    assert (arrow is not None) == is_external(url), f"external arrow mismatch for {url}"

    if value["link"]["new_window"]:
        assert element["target"] == "_blank"
        assert set(element["rel"]) == {"external", "noopener"}
    else:
        assert element.get("target") is None


def assert_analytics(element, cta_text, cta_position, analytics_id):
    assert element["data-cta-text"] == cta_text
    assert element["data-cta-position"] == cta_position
    assert element["data-cta-uid"] == analytics_id


def assert_nav_link(element, value, cta_text, cta_position, utm_content=""):
    """A plain nav link: <li><a class="fl-nav-link">."""
    assert element.name == "a"
    assert "fl-nav-link" in element["class"]
    assert element.parent.name == "li"
    assert element.get_text(strip=True) == value["custom_label"]
    assert element["href"] == expected_href(value["link"]["custom_url"], utm_content=utm_content)
    assert_analytics(element, cta_text=cta_text, cta_position=cta_position, analytics_id=value["analytics_id"])
    assert_external_and_target(element, value)
    assert_link_icon(element, value)


def assert_nav_button(element, value, cta_text, cta_position):
    """A button-style link: a standalone ghost button (not in a list)."""
    assert element.name == "a"
    assert {"fl-button", "button-ghost", "fl-button-small"} <= set(element["class"])
    assert element.parent.name != "li"
    assert element.get_text(strip=True) == value["custom_label"]
    assert element["href"] == expected_href(value["link"]["custom_url"], utm_content="topnav")
    assert_analytics(element, cta_text=cta_text, cta_position=cta_position, analytics_id=value["analytics_id"])
    if value["link"]["new_window"]:
        assert element["target"] == "_blank"
    else:
        assert element.get("target") is None


def assert_separator(element):
    assert element.name == "span"
    assert "fl-nav-separator" in element["class"]


def assert_top_level_link(category, value, cta_position):
    """A top-level direct link: <li class="fl-menu-category"> with a title link and no panel."""
    assert category.find("div", class_="fl-menu-panel") is None
    link = category.find("a", class_="fl-menu-title")
    assert "fl-menu-top-level-link" in link["class"]
    assert link.get_text(strip=True) == value["custom_label"]
    assert link["href"] == expected_href(value["link"]["custom_url"], utm_content=slugify(value["custom_label"]))
    assert_analytics(link, cta_text=value["custom_label"], cta_position=cta_position, analytics_id=value["analytics_id"])
    assert_external_and_target(link, value)


def assert_column(column_element, children, folder_label, position):
    """A column's stream of links and horizontal rules, matched to its children by index."""
    # Flatten the rendered column into the same order as the source stream:
    # plain links (<a class="fl-nav-link">), button links (<a class="fl-button">)
    # and rules (<span class="fl-nav-separator">).
    rendered = column_element.select("a.fl-nav-link, a.fl-button, span.fl-nav-separator")
    assert len(rendered) == len(children)

    link_count = 0
    for child, element in zip(children, rendered):
        if child["type"] == "separator":
            assert_separator(element)
            continue
        link_count += 1
        value = child["value"]
        cta_text = f"{folder_label} - {value['custom_label']}"
        cta_position = f"{position}.link-{link_count}"
        if value["has_button_style"]:
            assert_nav_button(element, value, cta_text=cta_text, cta_position=cta_position)
        else:
            assert_nav_link(element, value, cta_text=cta_text, cta_position=cta_position, utm_content=slugify(folder_label))


def assert_folder(category, item, *, position):
    """A folder: a category whose title opens a dropdown panel of columns."""
    value = item["value"]
    folder_label = value["custom_label"]

    title = category.find("a", class_="fl-menu-title")
    assert title.get_text(strip=True) == folder_label
    assert title.find("span", class_="fl-icon-chevron-down") is not None

    panel = category.find("div", class_="fl-menu-panel")
    assert panel is not None
    assert category["data-testid"] == panel["id"]

    columns = value["sub_items"]
    column_elements = panel.find_all("div", class_="fl-menu-panel-content-column")
    assert len(column_elements) == len(columns)

    for column_index, (column, column_element) in enumerate(zip(columns, column_elements), start=1):
        assert_column(
            column_element,
            column["value"],
            folder_label=folder_label,
            position=f"{position}.column-{column_index}",
        )


def test_navigation_renders_all_items(minimal_site, rf):
    # Build the data once and render it once, then walk the data and the
    # rendered categories together, matching them by index.
    items = get_navigation_variants()
    snippet = make_snippet(items)
    soup = render_navigation(snippet, rf.get("/en-US/"))

    menu = soup.find("ul", class_="fl-nav-menu")
    assert menu is not None
    assert "fl-nav-menu-cms" in menu["class"]

    categories = menu.find_all("li", class_="fl-menu-category", recursive=False)
    assert len(categories) == len(items)

    for index, (item, category) in enumerate(zip(items, categories), start=1):
        position = f"topnav.item-{index}"
        if item["type"] == "folder":
            assert_folder(category, item, position=position)
        else:
            assert_top_level_link(category, item["value"], cta_position=position)


def test_external_top_level_link(minimal_site, rf):
    # The reproduced nav has only an internal top-level link, so cover the
    # external case (arrow icon + new tab) explicitly, reusing the assertion.
    item = build_top_level_link("Blog", custom_url="https://blog.mozilla.org/", new_window=True, block_id="a1", analytics_id="tl-uid")
    snippet = make_snippet([item])
    soup = render_navigation(snippet, rf.get("/en-US/"))

    category = soup.find("li", class_="fl-menu-category")
    assert_top_level_link(category, item["value"], cta_position="topnav.item-1")


def build_hardcoded_page_link_block(block_type, label, icon="", has_button_style=False, analytics_id="lookup-uid"):
    """Build a What's New / What's Next nav link, which looks its own URL up at render time."""
    return {
        "type": block_type,
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "icon": icon,
            "icon_position": "left",
            "has_button_style": has_button_style,
            "analytics_id": analytics_id,
        },
        "id": "2026nav0-0000-0000-0000-000000000301",
    }


def make_one_folder_snippet(child):
    """Publish a navigation snippet holding one folder whose single column holds the given block."""
    column = build_column([child], block_id="2026nav0-0000-0000-0000-000000000300")
    folder = build_folder("Browser", columns=[column], block_id="2026nav0-0000-0000-0000-000000000003")
    return make_snippet([folder])


def test_whats_new_link_renders_the_whats_new_index_url(minimal_site, rf):
    index = WhatsNewIndexPageFactory(parent=minimal_site.root_page, slug="whatsnew", live=True)
    WhatsNewPage2026Factory(parent=index, slug="145", live=True)
    snippet = make_one_folder_snippet(build_hardcoded_page_link_block("whats_new_link", "What's New", icon="bookmark-fill"))

    soup = render_navigation(snippet, rf.get("/en-US/"))

    link = soup.find("a", class_="fl-nav-link")
    assert link is not None
    assert link["href"].endswith("/whatsnew/?from_main_nav=true")
    assert link.get_text(strip=True) == "What's New"
    assert link.parent.name == "li"
    assert link.find("span", class_="fl-icon-bookmark-fill") is not None
    assert_analytics(link, cta_text="Browser - What's New", cta_position="topnav.item-1.column-1.link-1", analytics_id="lookup-uid")


def test_whats_new_link_renders_nothing_when_the_index_page_is_missing(minimal_site, rf):
    snippet = make_one_folder_snippet(build_hardcoded_page_link_block("whats_new_link", "What's New"))

    soup = render_navigation(snippet, rf.get("/en-US/"))

    # The folder itself still renders; only the link it holds is left out.
    assert soup.find("div", class_="fl-menu-panel") is not None
    assert soup.find("a", class_="fl-nav-link") is None


def test_whats_new_link_renders_as_a_button_when_button_style_is_set(minimal_site, rf):
    index = WhatsNewIndexPageFactory(parent=minimal_site.root_page, slug="whatsnew", live=True)
    WhatsNewPage2026Factory(parent=index, slug="145", live=True)
    snippet = make_one_folder_snippet(build_hardcoded_page_link_block("whats_new_link", "What's New", has_button_style=True))

    soup = render_navigation(snippet, rf.get("/en-US/"))

    button = soup.find("a", class_="fl-button")
    assert button is not None
    assert {"button-ghost", "fl-button-small"} <= set(button["class"])
    assert button.parent.name != "li"
    assert button["href"].endswith("/whatsnew/?from_main_nav=true")
    assert button.get_text(strip=True) == "What's New"


def test_whats_next_link_renders_the_roadmap_url(minimal_site, rf):
    RoadmapPageFactory(parent=minimal_site.root_page, slug="whatsnext", live=True)
    snippet = make_one_folder_snippet(build_hardcoded_page_link_block("whats_next_link", "What's Next", icon="calendar"))

    soup = render_navigation(snippet, rf.get("/en-US/"))

    link = soup.find("a", class_="fl-nav-link")
    assert link is not None
    assert link["href"].endswith("/whatsnext/")
    assert link.get_text(strip=True) == "What's Next"
    assert link.parent.name == "li"
    assert link.find("span", class_="fl-icon-calendar") is not None
    assert_analytics(link, cta_text="Browser - What's Next", cta_position="topnav.item-1.column-1.link-1", analytics_id="lookup-uid")


def test_whats_next_link_renders_nothing_when_the_roadmap_page_is_missing(minimal_site, rf):
    snippet = make_one_folder_snippet(build_hardcoded_page_link_block("whats_next_link", "What's Next"))

    soup = render_navigation(snippet, rf.get("/en-US/"))

    assert soup.find("div", class_="fl-menu-panel") is not None
    assert soup.find("a", class_="fl-nav-link") is None


def build_browser_column_children():
    """The Browser menu's stream of links, rules and lookup links, as the static nav lays it out."""
    return [
        build_nav_link("Mobile", custom_url="/browsers/mobile/", icon="device-mobile", block_id="2026nav0-0000-0000-0000-000000000401"),
        build_nav_link("Enterprise", custom_url="/enterprise/", icon="globe", block_id="2026nav0-0000-0000-0000-000000000402"),
        build_separator(block_id="2026nav0-0000-0000-0000-000000000403"),
        build_hardcoded_page_link_block("whats_new_link", "What's New", icon="bookmark-fill"),
        build_hardcoded_page_link_block("whats_next_link", "What's Next", icon="calendar"),
        build_separator(block_id="2026nav0-0000-0000-0000-000000000404"),
        build_nav_link(
            "Extensions & Themes",
            custom_url="https://addons.mozilla.org/firefox/",
            icon="extension-fill",
            block_id="2026nav0-0000-0000-0000-000000000405",
        ),
        build_nav_link(
            "Support", custom_url="https://support.mozilla.org/", icon="avatar-info-circle-fill", block_id="2026nav0-0000-0000-0000-000000000406"
        ),
        build_separator(block_id="2026nav0-0000-0000-0000-000000000407"),
        build_nav_link("Download Firefox", custom_url="/download/", has_button_style=True, block_id="2026nav0-0000-0000-0000-000000000408"),
    ]


def get_list_labels(column):
    """The link labels of each <ul> in a rendered column, in document order."""
    return [[link.get_text(strip=True) for link in list_element.find_all("a")] for list_element in column.find_all("ul")]


def test_column_groups_each_group_of_links_into_its_own_list(minimal_site, rf):
    index = WhatsNewIndexPageFactory(parent=minimal_site.root_page, slug="whatsnew", live=True)
    WhatsNewPage2026Factory(parent=index, slug="145", live=True)
    RoadmapPageFactory(parent=minimal_site.root_page, slug="whatsnext", live=True)
    snippet = make_snippet([build_folder("Browser", columns=[build_column(build_browser_column_children(), block_id="c1")], block_id="f1")])

    soup = render_navigation(snippet, rf.get("/en-US/"))

    column = soup.find("div", class_="fl-menu-panel-content-column")
    assert get_list_labels(column) == [
        ["Mobile", "Enterprise"],
        ["What's New", "What's Next"],
        ["Extensions & Themes", "Support"],
    ]
    # Each rule separates two lists, and the button-style link closes the last one.
    assert len(column.find_all("span", class_="fl-nav-separator")) == 3
    button = column.find("a", class_="fl-button")
    assert button.parent.name != "li"


def test_column_keeps_its_lists_intact_when_hardcoded_pages_are_missing(minimal_site, rf):
    # The pages exist in en-US only, so in fr both links resolve to nothing.
    index = WhatsNewIndexPageFactory(parent=minimal_site.root_page, slug="whatsnew", live=True)
    WhatsNewPage2026Factory(parent=index, slug="145", live=True)
    RoadmapPageFactory(parent=minimal_site.root_page, slug="whatsnext", live=True)
    snippet = make_snippet([build_folder("Browser", columns=[build_column(build_browser_column_children(), block_id="c1")], block_id="f1")])

    soup = render_navigation(snippet, rf.get("/fr/"), language="fr")

    column = soup.find("div", class_="fl-menu-panel-content-column")
    assert get_list_labels(column) == [
        ["Mobile", "Enterprise"],
        ["Extensions & Themes", "Support"],
    ]
    # The separators around the dropped links collapse into the one that still divides the two visible lists.
    separators = column.find_all("span", class_="fl-nav-separator")
    assert len(separators) == 2
    for separator in separators:
        assert separator.find_next_sibling().name != "span"
    button = column.find("a", class_="fl-button")
    assert button.parent.name != "li"


def test_str_includes_name_and_locale(minimal_site):
    snippet = get_navigation_snippet()
    assert snippet.name in str(snippet)
    assert str(snippet.locale) in str(snippet)


def test_snippet_stores_logo_cta_button_and_logo_link(minimal_site):
    logo = make_image(240, 80)
    logo_dark = make_image(240, 80, title="dark-logo")
    primary_button = get_button_variants()["primary"]
    snippet = NavigationSnippet.objects.create(
        locale=Locale.get_default(),
        name="Override nav",
        items=[],
        logo=logo,
        logo_dark=logo_dark,
        cta_button=[("button", [primary_button])],
        logo_link=[("link", {"link_to": "custom_url", "custom_url": "https://example.com/campaign/"})],
    )
    snippet.refresh_from_db()
    assert snippet.logo_id == logo.id
    assert snippet.logo_dark_id == logo_dark.id
    assert len(snippet.cta_button) == 1
    assert snippet.cta_button[0].block_type == "button"
    inner_buttons = snippet.cta_button[0].value
    assert len(inner_buttons) == 1
    assert inner_buttons[0].block_type == "button"
    assert inner_buttons[0].value["custom_label"] == primary_button["value"]["custom_label"]
    assert len(snippet.logo_link) == 1
    assert snippet.logo_link[0].value.get_url() == "https://example.com/campaign/"


def test_clean_rejects_oversized_logo(minimal_site):
    snippet = NavigationSnippet(locale=Locale.get_default(), name="too big", logo=make_image(500, 200))
    with pytest.raises(ValidationError) as exc_info:
        snippet.clean()
    assert "logo" in exc_info.value.message_dict


def test_clean_rejects_oversized_logo_dark(minimal_site):
    snippet = NavigationSnippet(locale=Locale.get_default(), name="too big", logo_dark=make_image(500, 200))
    with pytest.raises(ValidationError) as exc_info:
        snippet.clean()
    assert "logo_dark" in exc_info.value.message_dict


def serve_page_soup(page, site, rf):
    """Serve a page (en-US) and return its rendered document as BeautifulSoup."""
    with translation.override("en-US"):
        response = page.serve(rf.get(page.relative_url(site)))
        if hasattr(response, "render"):
            response.render()
    return BeautifulSoup(response.content.decode(), "html.parser")


def test_page_header_overrides_logo_and_button(minimal_site, rf):
    site = Site.objects.get(is_default_site=True)
    logo = make_image(240, 80, title="page-logo")
    logo_dark = make_image(240, 80, title="page-logo-dark")
    override_button = get_button_variants()["primary"]
    override_button["value"]["custom_label"] = "Buy now"
    snippet = make_snippet([build_top_level_link("Home", custom_url="/", block_id="b1")])
    snippet.logo = logo
    snippet.logo_dark = logo_dark
    snippet.cta_button = [("button", [override_button])]
    snippet.logo_link = [("link", {"link_to": "custom_url", "custom_url": "https://example.com/campaign/"})]
    snippet.save_revision().publish()
    snippet.refresh_from_db()

    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet)
    soup = serve_page_soup(page, site, rf)

    logo_anchor = soup.find("a", class_="fl-logo-fx")
    assert logo_anchor["href"] == "https://example.com/campaign/"

    light_img = logo_anchor.find("img", class_="display-light")
    dark_img = logo_anchor.find("img", class_="display-dark")
    assert logo.get_rendition("width-400").url in light_img["src"]
    assert logo_dark.get_rendition("width-400").url in dark_img["src"]
    # The default CSS-painted logo is not used for the override.
    assert "logo-word-hor-2026.svg" not in soup.decode()

    # The override replaces the default download button.
    assert "Buy now" in soup.get_text()
    assert soup.find("div", class_="nav-cta-wrap") is None


def test_page_header_dark_logo_omitted_when_unset(minimal_site, rf):
    site = Site.objects.get(is_default_site=True)
    logo = make_image(240, 80, title="light-only")
    snippet = make_snippet([build_top_level_link("Home", custom_url="/", block_id="b1")])
    snippet.logo = logo
    snippet.save_revision().publish()
    snippet.refresh_from_db()

    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet)
    soup = serve_page_soup(page, site, rf)

    logo_anchor = soup.find("a", class_="fl-logo-fx")
    images = logo_anchor.find_all("img")
    assert len(images) == 1
    assert logo.get_rendition("width-400").url in images[0]["src"]
    assert logo_anchor.find("img", class_="display-dark") is None


def make_default_snippet(name="Default nav", items=None):
    """Create and publish a default NavigationSnippet in the default locale."""
    snippet = NavigationSnippet.objects.create(
        locale=Locale.get_default(),
        name=name,
        is_default=True,
        items=items or [],
    )
    snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet


def test_get_default_returns_none_when_no_default(minimal_site):
    # A non-default snippet exists but must be ignored.
    make_snippet([build_top_level_link("Home", custom_url="/", block_id="b1")])
    with translation.override("en-US"):
        assert NavigationSnippet.get_default() is None


def test_get_default_returns_published_default(minimal_site):
    snippet = make_default_snippet()
    with translation.override("en-US"):
        assert NavigationSnippet.get_default() == snippet


def test_get_default_ignores_unpublished_default(minimal_site):
    # A default snippet that was never published is not live and must be skipped.
    NavigationSnippet.objects.create(locale=Locale.get_default(), name="Draft default", is_default=True, items=[], live=False)
    with translation.override("en-US"):
        assert NavigationSnippet.get_default() is None


def test_get_default_returns_most_recently_published(minimal_site):
    older = make_default_snippet(name="Older default")
    newer = make_default_snippet(name="Newer default")
    # Force a deterministic ordering on last_published_at.
    NavigationSnippet.objects.filter(pk=older.pk).update(last_published_at="2020-01-01T00:00:00Z")
    NavigationSnippet.objects.filter(pk=newer.pk).update(last_published_at="2020-06-01T00:00:00Z")
    with translation.override("en-US"):
        assert NavigationSnippet.get_default() == newer


def get_page_navigation(page):
    """Resolve a page's navigation in the en-US active locale."""
    with translation.override("en-US"):
        return page.get_navigation()


def test_page_uses_own_custom_navigation(minimal_site):
    site = Site.objects.get(is_default_site=True)
    own = make_snippet([build_top_level_link("Own", custom_url="/own/", block_id="o1")])
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=own)
    assert get_page_navigation(page) == own


def test_child_inherits_parent_custom_navigation(minimal_site):
    site = Site.objects.get(is_default_site=True)
    parent_nav = make_snippet([build_top_level_link("Parent", custom_url="/p/", block_id="p1")])
    parent = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=parent_nav)
    child = FreeFormPage2026Factory(parent=parent, custom_navigation=None)
    assert get_page_navigation(child) == parent_nav


def test_descendant_inherits_nearest_ancestor_through_structural_page(minimal_site):
    site = Site.objects.get(is_default_site=True)
    grandparent_nav = make_snippet([build_top_level_link("GP", custom_url="/gp/", block_id="g1")])
    grandparent = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=grandparent_nav)
    structural = StructuralPageFactory(parent=grandparent)  # mixin-less intermediate, no nav
    child = FreeFormPage2026Factory(parent=structural, custom_navigation=None)
    assert get_page_navigation(child) == grandparent_nav


def test_nearest_ancestor_wins(minimal_site):
    site = Site.objects.get(is_default_site=True)
    far_nav = make_snippet([build_top_level_link("Far", custom_url="/far/", block_id="f1")])
    near_nav = make_snippet([build_top_level_link("Near", custom_url="/near/", block_id="n1")])
    far = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=far_nav)
    near = FreeFormPage2026Factory(parent=far, custom_navigation=near_nav)
    child = FreeFormPage2026Factory(parent=near, custom_navigation=None)
    assert get_page_navigation(child) == near_nav


def test_unresolvable_ancestor_nav_is_skipped(minimal_site):
    # When a nearer ancestor's nav does not resolve in the active locale, the walk
    # continues to a farther ancestor whose nav does.
    site = Site.objects.get(is_default_site=True)
    draft_nav = NavigationSnippet.objects.create(locale=Locale.get_default(), name="Draft nav", items=[], live=False)
    available_nav = make_snippet([build_top_level_link("Avail", custom_url="/a/", block_id="a1")])
    far = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=available_nav)
    near = FreeFormPage2026Factory(parent=far, custom_navigation=draft_nav)
    child = FreeFormPage2026Factory(parent=near, custom_navigation=None)
    assert get_page_navigation(child) == available_nav


def test_get_navigation_excludes_default_snippet(minimal_site):
    # A default snippet exists, but get_navigation() returns None because the
    # default belongs to the header template (get_default_navigation tag), not
    # the page's custom_navigation context var.
    site = Site.objects.get(is_default_site=True)
    make_default_snippet()
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=None)
    assert get_page_navigation(page) is None


def test_falls_back_to_none_when_no_default(minimal_site):
    site = Site.objects.get(is_default_site=True)
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=None)
    assert get_page_navigation(page) is None
