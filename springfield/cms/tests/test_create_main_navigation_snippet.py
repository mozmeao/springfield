# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import StringIO

from django.core.management import call_command

import pytest

from springfield.cms.management.commands.create_main_navigation_snippet import SNIPPET_TRANSLATION_KEY
from springfield.cms.models import NavigationSnippet
from springfield.cms.tests.factories import SimpleRichTextPageFactory


def run_command():
    call_command("create_main_navigation_snippet", stdout=StringIO())


def get_snippet(language_code):
    return NavigationSnippet.objects.get(translation_key=SNIPPET_TRANSLATION_KEY, locale__language_code=language_code)


def collect_nav_links(snippet):
    """Map every nav link's label to its link value, flattening folders and columns."""
    return {
        child.value["custom_label"]: child.value["link"]
        for folder in snippet.items
        for column in folder.value["sub_items"]
        for child in column
        if child.block_type == "link"
    }


@pytest.fixture
def navigation_site(minimal_site):
    """A site with a CMS page published at one of the navigation's link paths."""
    SimpleRichTextPageFactory(slug="mobile", title="Firefox Mobile", parent=minimal_site.root_page)
    return minimal_site


@pytest.mark.django_db
def test_creates_the_english_navigation_snippet(navigation_site):
    run_command()

    snippet = get_snippet("en-US")
    assert snippet.name == "Main navigation"
    assert snippet.live is True
    # The site keeps rendering the static navigation until an editor opts in.
    assert snippet.is_default is False

    assert [folder.value["custom_label"] for folder in snippet.items] == ["Browser", "Features", "Resources"]

    browser_column = snippet.items[0].value["sub_items"][0]
    assert [(child.block_type, (child.value or {}).get("custom_label", "")) for child in browser_column] == [
        ("link", "Mobile"),
        ("link", "Enterprise"),
        ("separator", ""),
        ("whats_new_link", "What’s New"),
        ("whats_next_link", "What’s Next"),
        ("separator", ""),
        ("link", "Extensions & Themes"),
        ("link", "Support"),
        ("separator", ""),
        ("link", "Download Firefox"),
    ]
    assert browser_column[-1].value["has_button_style"] is True
    assert browser_column[0].value["icon"] == "device-mobile"


@pytest.mark.django_db
def test_links_to_cms_pages_where_a_page_is_published_at_the_path(navigation_site):
    run_command()

    links = collect_nav_links(get_snippet("en-US"))

    mobile = links["Mobile"]
    assert mobile["link_to"] == "page"
    assert mobile["page"].slug == "mobile"

    # No CMS page serves /newsletter/ — it is a static Django view — so the link
    # falls back to a relative URL, which picks up the locale prefix at render time.
    newsletter = links["Newsletter"]
    assert newsletter["link_to"] == "relative_url"
    assert newsletter["relative_url"] == "/newsletter/"

    support = links["Support"]
    assert support["link_to"] == "custom_url"
    assert support["custom_url"] == "https://support.mozilla.org/"


@pytest.mark.django_db
def test_rerunning_leaves_the_navigation_unchanged(navigation_site):
    run_command()
    items_after_first_run = list(get_snippet("en-US").items.raw_data)

    run_command()

    # One snippet per locale: the English source and its French translation.
    assert NavigationSnippet.objects.filter(translation_key=SNIPPET_TRANSLATION_KEY).count() == 2
    assert list(get_snippet("en-US").items.raw_data) == items_after_first_run


@pytest.mark.django_db
def test_translates_the_navigation_into_the_configured_locales(navigation_site):
    run_command()

    snippet = get_snippet("fr")
    assert snippet.live is True
    assert [folder.value["custom_label"] for folder in snippet.items] == ["Navigateur", "Fonctionnalités", "Ressources"]

    # Translating the labels leaves the link targets alone.
    links = collect_nav_links(snippet)
    assert links["Mobile"]["page"].slug == "mobile"
    assert links["Newsletter"]["relative_url"] == "/newsletter/"
