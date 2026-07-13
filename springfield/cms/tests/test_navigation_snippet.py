# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import translation

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale

from lib.l10n_utils import fluent_l10n
from springfield.cms.fixtures.navigation_fixtures import build_top_level_link, get_navigation_snippet, get_navigation_variants
from springfield.cms.models import NavigationSnippet
from springfield.cms.templatetags.cms_tags import add_utm_parameters

pytestmark = [pytest.mark.django_db]

# Mirrors the utm_parameters set in cms/snippets/navigation-snippet.html, used to
# work out the expected href of links pointing at Mozilla-owned domains.
UTM_PARAMETERS = {
    "utm_source": "www.firefox.com",
    "utm_medium": "referral",
    "utm_campaign": "nav",
    "utm_content": "browser",
}


def render_navigation(snippet, request):
    """Render the navigation snippet template to a BeautifulSoup document."""
    with translation.override("en-US"):
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


def is_external(url):
    return url.startswith(("http://", "https://"))


def expected_href(url):
    """The href a link should render, including the nav's UTM params for Mozilla domains."""
    return add_utm_parameters({"utm_parameters": UTM_PARAMETERS}, url)


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


def assert_nav_link(element, value, cta_text, cta_position):
    """A plain nav link: <li><a class="fl-nav-link">."""
    assert element.name == "a"
    assert "fl-nav-link" in element["class"]
    assert element.parent.name == "li"
    assert element.get_text(strip=True) == value["custom_label"]
    assert element["href"] == expected_href(value["link"]["custom_url"])
    assert_analytics(element, cta_text=cta_text, cta_position=cta_position, analytics_id=value["analytics_id"])
    assert_external_and_target(element, value)
    assert_link_icon(element, value)


def assert_nav_button(element, value, cta_text, cta_position):
    """A button-style link: a standalone ghost button (not in a list)."""
    assert element.name == "a"
    assert {"fl-button", "button-ghost", "fl-button-small"} <= set(element["class"])
    assert element.parent.name != "li"
    assert element.get_text(strip=True) == value["custom_label"]
    assert element["href"] == expected_href(value["link"]["custom_url"])
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
    assert link["href"] == expected_href(value["link"]["custom_url"])
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
            assert_nav_link(element, value, cta_text=cta_text, cta_position=cta_position)


def assert_folder(category, item, *, position):
    """A folder: a category whose title opens a dropdown panel of columns."""
    value = item["value"]
    folder_label = value["custom_label"]

    title = category.find("span", class_="fl-menu-title")
    assert title.get_text(strip=True) == folder_label
    assert title.find("span", class_="fl-icon-chevron-down") is not None

    panel = category.find("div", class_="fl-menu-panel")
    assert panel is not None
    assert title["aria-controls"] == panel["id"]
    assert category["data-testid"] == panel["id"]
    assert panel.find("button", class_="fl-menu-close-button") is not None

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


def test_str_includes_name_and_locale(minimal_site):
    snippet = get_navigation_snippet()
    assert snippet.name in str(snippet)
    assert str(snippet.locale) in str(snippet)
