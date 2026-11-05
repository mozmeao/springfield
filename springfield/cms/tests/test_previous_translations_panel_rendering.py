# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale
from wagtail_localize.models import String, StringSegment, StringTranslation, Translation, TranslationSource
from wagtail_localize.strings import StringValue

pytestmark = pytest.mark.django_db


SOURCE_NOW = "Get Firefox!"
SOURCE_THEN = "Get Firefox"


def set_rich_text(translated_page, html):
    """Replace the source page's body copy and re-extract its segments, which is what an
    editor's save does."""
    translated_page.source_page.content = html
    translated_page.source_page.save()
    translated_page.translation.source.update_from_db()
    translated_page.translation.source.refresh_segments()


@pytest.fixture
def drifted_page(translated_page):
    """A translated page with one paragraph of body copy, ready for an orphan at its
    content context."""
    set_rich_text(translated_page, f"<p>{SOURCE_NOW}</p>")
    return translated_page


def get_orphan_stringtranslation(drifted_page, source_text, value, **kwargs):
    """
    A StringTranslation at the content context whose source String has no segment there.

    Built at `content` and never at `title`: a wagtail-localize signal copies a title
    translation's data into the page's draft_title, which the admin then prints in its
    own chrome. An assertion on that text would pass with the panel absent.
    """
    source = drifted_page.translation.source
    context = StringSegment.objects.filter(source=source, context__path="content").first().context
    string = String.from_value(source.locale, StringValue(source_text))
    defaults = {"data": value, "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL, "tool_name": ""}
    defaults.update(kwargs)
    return StringTranslation.objects.create(translation_of=string, locale=drifted_page.locale, context=context, **defaults)


def get_orphan_at_title(drifted_page, source_text, value):
    """A second orphan, at the context that precedes `content` in page order."""
    context = StringSegment.objects.get(source=drifted_page.translation.source, context__path="title").context
    return StringTranslation.objects.create(
        translation_of=String.from_value(drifted_page.translation.source.locale, StringValue(source_text)),
        locale=drifted_page.locale,
        context=context,
        data=value,
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )


def editor_html_for(admin_client, page):
    response = admin_client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))
    assert response.status_code == 200
    return response.content.decode()


def editor_html(admin_client, drifted_page):
    return editor_html_for(admin_client, drifted_page.page)


def get_soup_for_panel(html):
    """The first rendered previous-translations panel."""
    return BeautifulSoup(html, "html.parser").select_one('[data-side-panel="previous-translations"]')


def get_soup_for_toggle(html):
    """The button that opens the panel, which lives in the editor header."""
    return BeautifulSoup(html, "html.parser").select_one('[data-side-panel-toggle="previous-translations"]')


def test_panel_shows_the_whole_entry(admin_client, drifted_page):
    value = "La barre latérale garde vos outils à portée de clic."
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, value)

    html = editor_html(admin_client, drifted_page)

    # All three values, in order.
    assert [dd.get_text(strip=True) for dd in get_soup_for_panel(html).select("dd")] == [SOURCE_THEN, SOURCE_NOW, value]


def test_several_untranslated_paragraphs_are_offered_as_separate_candidates(admin_client, drifted_page):
    """
    Paragraphs of one field share a context, so a field holding two untranslated ones
    cannot say which the leftover translation belonged to.
    """
    set_rich_text(drifted_page, f"<p>{SOURCE_NOW}</p><p>Grab Firefox now</p>")
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    entry = get_soup_for_panel(editor_html(admin_client, drifted_page)).select_one("li")

    assert [dd.get_text(strip=True) for dd in entry.select("dd")] == [
        SOURCE_THEN,
        SOURCE_NOW,
        "Grab Firefox now",
        "La barre latérale",
    ]
    assert "may not be correct" in entry.select_one("[data-inexact-pairing]").get_text()


def test_an_exact_entry_is_offered_without_the_guess_note(admin_client, drifted_page):
    """One untranslated string and one orphan is considered an exact match."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    entry = get_soup_for_panel(editor_html(admin_client, drifted_page)).select_one("li")

    assert entry.select_one("[data-inexact-pairing]") is None


def test_no_panel_without_entries(admin_client, drifted_page):
    """If there are no entries, the panel does not show up."""
    html = editor_html(admin_client, drifted_page)

    assert get_soup_for_panel(html) is None
    assert get_soup_for_toggle(html) is None


def test_labels_carry_the_locale_codes_from_the_translation(admin_client, drifted_page):
    """Run against a *second* target locale, because an assertion built from the
    fixture's own `fr` is satisfied by a template that hardcodes `fr`."""
    german = Locale.objects.create(language_code="de")
    translation = Translation.objects.create(source=drifted_page.translation.source, target_locale=german, enabled=True)
    translation.save_target(publish=False)
    context = StringSegment.objects.filter(source=translation.source, context__path="content").first().context
    StringTranslation.objects.create(
        translation_of=String.from_value(translation.source.locale, StringValue(SOURCE_THEN)),
        locale=german,
        context=context,
        data="Die Seitenleiste",
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )

    text = get_soup_for_panel(editor_html_for(admin_client, translation.get_target_instance())).get_text()

    assert f"Source then ({drifted_page.translation.source.locale.language_code})" in text
    assert "Previous translation (de)" in text
    assert "Previous translation (fr)" not in text


def make_translator(django_user_model):
    return django_user_model.objects.create_user(
        username="jbloggs@example.com",
        email="jbloggs@example.com",
        password="irrelevant",
        first_name="Jo",
        last_name="Bloggs",
    )


@pytest.mark.parametrize(("has_translator", "expected_attribution"), [(False, ""), (True, " · Jo Bloggs")])
def test_attribution_follows_the_comment_only_when_there_is_a_translator(
    admin_client, drifted_page, django_user_model, has_translator, expected_attribution
):
    translator = make_translator(django_user_model) if has_translator else None
    orphan = get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale", last_translated_by=translator)

    entry = get_soup_for_panel(editor_html(admin_client, drifted_page)).select_one("li")

    assert "La barre latérale" in entry.get_text()
    assert entry.select_one("p").get_text(strip=True) == f"{orphan.get_comment()}{expected_attribution}"


def test_translator_is_named_without_their_email(admin_client, drifted_page, django_user_model):
    """The translator's username is their email address, which the panel must not print."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale", last_translated_by=make_translator(django_user_model))

    html = editor_html(admin_client, drifted_page)

    assert "Jo Bloggs" in get_soup_for_panel(html).get_text()
    assert "jbloggs@example.com" not in html


def test_one_list_item_per_entry(admin_client, drifted_page):
    """A page with 2 orphaned segments shows both, in the order they appear on the page."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")
    get_orphan_at_title(drifted_page, "Try Firefox", "Essayez Firefox")

    items = get_soup_for_panel(editor_html(admin_client, drifted_page)).select("li")

    assert [item.select_one("dd").get_text(strip=True) for item in items] == ["Try Firefox", SOURCE_THEN]
    assert [item.select_one("h3").get_text(strip=True) for item in items] == ["Title", "Content"]
    assert "Essayez Firefox" in items[0].get_text()
    assert "La barre latérale" in items[1].get_text()


def test_stored_html_renders_as_plain_text(admin_client, drifted_page):
    """wagtail-localize stores strings as HTML fragments; the panel shows their text, escaped once."""
    get_orphan_stringtranslation(drifted_page, "Get Firefox &lt;3", 'Barre <a id="a1">latérale</a> &lt;3')

    markup = str(get_soup_for_panel(editor_html(admin_client, drifted_page)))

    assert "Barre latérale &lt;3" in markup
    assert "Get Firefox &lt;3" in markup
    assert 'id="a1"' not in markup


def test_setting_controls_the_panel(admin_client, drifted_page, settings):
    """The same entry renders a panel with the setting on and none with it off, so a
    broken feature cannot be mistaken for a disabled one."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    assert get_soup_for_panel(editor_html(admin_client, drifted_page)) is not None

    settings.CMS_PREVIOUS_TRANSLATIONS_ENABLED = False
    html = editor_html(admin_client, drifted_page)

    assert get_soup_for_panel(html) is None
    assert get_soup_for_toggle(html) is None


def test_toggle_button_carries_the_entry_count(admin_client, drifted_page):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")
    get_orphan_at_title(drifted_page, "Try Firefox", "Essayez Firefox")

    counter = get_soup_for_toggle(editor_html(admin_client, drifted_page)).select_one("[data-side-panel-toggle-counter]")

    assert counter.get_text(strip=True) == "2"
    # Wagtail hides the counter when the count is falsy, so a visible count is the assertion.
    assert "hidden" not in counter.attrs


def test_status_panel_still_renders(admin_client, drifted_page):
    """The panel is added to the editor's side panels, not substituted for them."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    html = editor_html(admin_client, drifted_page)

    # The "Status" panel still appears.
    assert BeautifulSoup(html, "html.parser").select_one('[data-side-panel="status"]') is not None


def test_panel_follows_the_status_panel(admin_client, drifted_page):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    aside = BeautifulSoup(editor_html(admin_client, drifted_page), "html.parser").select_one("aside.form-side")
    names = [panel["data-side-panel"] for panel in aside.select("[data-side-panel]")]

    assert names.index("previous-translations") > names.index("status")


def test_panel_renders_for_a_translated_snippet(admin_client, pretranslated_phrase_snippet):
    locale = Locale.objects.create(language_code="de")
    translated_snippet = pretranslated_phrase_snippet.copy_for_translation(locale)
    translated_snippet.save()
    source, __ = TranslationSource.get_or_create_from_instance(pretranslated_phrase_snippet)
    Translation.objects.create(source=source, target_locale=locale, enabled=True)

    segment = StringSegment.objects.filter(source=source).first()
    StringTranslation.objects.create(
        translation_of=String.from_value(source.locale, StringValue("Download the browser")),
        locale=locale,
        context=segment.context,
        data="Browser herunterladen",
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )

    url = reverse("wagtailsnippets_cms_pretranslatedphrase:edit", args=[translated_snippet.pk])
    response = admin_client.get(url)

    assert response.status_code == 200
    assert "Browser herunterladen" in get_soup_for_panel(response.content.decode()).get_text()
