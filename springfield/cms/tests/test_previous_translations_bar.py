# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

from django.urls import reverse

import pytest
from pytest_django.asserts import assertInHTML
from wagtail.models import Locale
from wagtail_localize.models import String, StringSegment, StringTranslation, Translation, TranslationSource
from wagtail_localize.strings import StringValue

pytestmark = pytest.mark.django_db


SOURCE_NOW = "Get Firefox!"
SOURCE_THEN = "Get Firefox"


@pytest.fixture
def drifted_page(translated_page):
    """A translated page with one paragraph of body copy, ready for an orphan at its
    content context."""
    translated_page.source_page.content = f"<p>{SOURCE_NOW}</p>"
    translated_page.source_page.save()
    translated_page.translation.source.update_from_db()
    translated_page.translation.source.refresh_segments()
    return translated_page


def get_orphan_stringtranslation(drifted_page, source_text, value, **kwargs):
    """
    A StringTranslation at the content context whose source String has no segment there.

    Built at `content` and never at `title`: a wagtail-localize signal copies a title
    translation's data into the page's draft_title, which the admin then prints in its
    own chrome. An assertion on that text would pass with the bar absent.
    """
    source = drifted_page.translation.source
    context = StringSegment.objects.filter(source=source, context__path="content").first().context
    string = String.from_value(source.locale, StringValue(source_text))
    defaults = {"data": value, "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL, "tool_name": ""}
    defaults.update(kwargs)
    return StringTranslation.objects.create(translation_of=string, locale=drifted_page.locale, context=context, **defaults)


def editor_html_for(admin_client, page):
    response = admin_client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))
    assert response.status_code == 200
    return response.content.decode()


def editor_html(admin_client, drifted_page):
    return editor_html_for(admin_client, drifted_page.page)


def test_bar_shows_the_whole_card(admin_client, drifted_page):
    value = "La barre latérale garde vos outils à portée de clic."
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, value)

    html = editor_html(admin_client, drifted_page)

    # The whole row, not one span of it: the current source is what ties an entry to a
    # segment on screen, and a check for the translation alone would pass with it dropped.
    assertInHTML(
        f"""
        <summary class="previous-translations-row">
            <span class="previous-translations-source">{SOURCE_NOW}</span>
            <span class="previous-translations-arrow" aria-hidden="true">&rarr;</span>
            <span class="previous-translations-value">{value}</span>
        </summary>
        """,
        html,
    )
    # Source *then* lives in the open detail, and it is the only thing that lets a
    # translator reject a pairing the one-to-one rule got wrong.
    assert f"<dd>{SOURCE_THEN}</dd>" in html


def test_bar_renders_nothing_without_entries(admin_client, drifted_page):
    assert "previous-translations" not in editor_html(admin_client, drifted_page)


def test_bar_and_rows_start_closed(admin_client, drifted_page):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    html = editor_html(admin_client, drifted_page)

    # The bar exists
    assert '<details class="previous-translations">' in html
    # The bar is closed
    assert "<details open" not in html
    assert 'class="previous-translations" open' not in html


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

    html = editor_html_for(admin_client, translation.get_target_instance())

    assert f"Source then ({drifted_page.translation.source.locale.language_code})" in html
    assert "Previous translation (de)" in html
    assert "Previous translation (fr)" not in html


def test_absent_translator_renders_no_attribution(admin_client, drifted_page):
    """An entry whose translation has no translator does not say who it was translated by."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale", last_translated_by=None)

    html = editor_html(admin_client, drifted_page)

    # The bar renders
    assert '<span class="previous-translations-value">La barre latérale</span>' in html
    # The bar does not say who it was translated by
    assert not re.search(r"Translated manually on [^<]*&middot;", html)


def test_attribution_follows_the_comment_after_a_separator(admin_client, drifted_page, django_user_model):
    """An entry whose translation has a translator says who it was translated by."""
    translator = django_user_model.objects.create_user(
        username="jbloggs@example.com",
        email="jbloggs@example.com",
        password="irrelevant",
        first_name="Jo",
        last_name="Bloggs",
    )
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale", last_translated_by=translator)

    html = editor_html(admin_client, drifted_page)

    assert re.search(r"Translated manually on [^<]*&middot; Jo Bloggs", html)
    assert "jbloggs@example.com" not in html


def test_one_card_per_entry(admin_client, drifted_page):
    """A page with 2 orphaned segments shows both."""
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")
    title_context = StringSegment.objects.get(source=drifted_page.translation.source, context__path="title").context
    StringTranslation.objects.create(
        translation_of=String.from_value(drifted_page.translation.source.locale, StringValue("Switch to Chrome")),
        locale=drifted_page.locale,
        context=title_context,
        data="Passer à Chrome",
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )

    html = editor_html(admin_client, drifted_page)

    assert html.count('<details class="previous-translations-entry">') == 2
    assert '<span class="previous-translations-value">La barre latérale</span>' in html
    assert '<span class="previous-translations-value">Passer à Chrome</span>' in html


def test_markup_in_a_translation_is_escaped(admin_client, drifted_page):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, 'Barre <a href="/x/">latérale</a>')

    html = editor_html(admin_client, drifted_page)

    assert "&lt;a href=&quot;/x/&quot;&gt;" in html


def test_setting_disables_the_bar(admin_client, drifted_page, settings):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")
    settings.CMS_PREVIOUS_TRANSLATIONS_ENABLED = False

    assert "previous-translations" not in editor_html(admin_client, drifted_page)


def test_bar_renders_for_a_translated_snippet(admin_client, pretranslated_phrase_snippet):
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
    assert '<span class="previous-translations-value">Browser herunterladen</span>' in response.content.decode()


def test_heading_counts_the_segments_in_the_singular(admin_client, drifted_page):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")

    assert "1 untranslated segment has a previous translation" in editor_html(admin_client, drifted_page)


def test_heading_counts_the_segments_in_the_plural(admin_client, drifted_page):
    get_orphan_stringtranslation(drifted_page, SOURCE_THEN, "La barre latérale")
    title_context = StringSegment.objects.get(source=drifted_page.translation.source, context__path="title").context
    StringTranslation.objects.create(
        translation_of=String.from_value(drifted_page.translation.source.locale, StringValue("Switch to Chrome")),
        locale=drifted_page.locale,
        context=title_context,
        data="Passer à Chrome",
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )

    assert "2 untranslated segments have previous translations" in editor_html(admin_client, drifted_page)
