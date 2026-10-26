# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import connection
from django.test.utils import CaptureQueriesContext

import pytest
from wagtail.models import Locale
from wagtail_localize.models import String, StringSegment, StringTranslation
from wagtail_localize.strings import StringValue

from springfield.cms.previous_translations import get_previous_translations

pytestmark = pytest.mark.django_db


def orphan_stringtranslation(translated_page, context, source_text, value, **kwargs):
    """
    A StringTranslation at `context` whose source String has no segment there.

    This is the state wagtail-localize leaves behind when an editor changes the
    source: refresh_segments() drops the StringSegment and leaves the translation.
    """
    string = String.from_value(translated_page.translation.source.locale, StringValue(source_text))
    defaults = {
        "data": value,
        "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL,
        "tool_name": "",
        "has_error": False,
    }
    defaults.update(kwargs)
    return StringTranslation.objects.create(
        translation_of=string,
        locale=translated_page.locale,
        context=context,
        **defaults,
    )


def context_of_only_title(translated_page):
    """The context of the page's, with only 1 segment, its title."""
    return StringSegment.objects.get(source=translated_page.translation.source, context__path="title").context


def translate_segment(translated_page, segment, value):
    StringTranslation.objects.create(
        translation_of_id=segment.string_id,
        locale=translated_page.locale,
        context=segment.context,
        data=value,
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )


def set_rich_text(translated_page, html):
    """Replace the source page's rich text and re-extract its segments, which is what
    an editor's save does."""
    translated_page.source_page.content = html
    translated_page.source_page.save()
    translated_page.translation.source.update_from_db()
    translated_page.translation.source.refresh_segments()


def content_context(translated_page):
    return StringSegment.objects.filter(source=translated_page.translation.source, context__path="content").first().context


@pytest.fixture
def three_paragraph_page(translated_page):
    set_rich_text(translated_page, "<p>Alpha</p><p>Beta</p><p>Gamma</p>")
    return translated_page


def test_drifted_segment_offers_its_previous_translation(translated_page):
    context = context_of_only_title(translated_page)
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", "Passer à Chrome")

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].source == "Switch to Chrome"
    assert entries[0].source_now == "Switch to Firefox"
    assert entries[0].value == "Passer à Chrome"
    assert entries[0].field_path == "title"


def test_untouched_translation_offers_nothing(translated_page):
    assert get_previous_translations(translated_page.translation) == []


def test_current_translation_suppresses_an_orphan_stringtranslation_at_its_context(translated_page):
    """A segment that already has a translation does not return its previous translation."""
    context = context_of_only_title(translated_page)
    segment = StringSegment.objects.get(source=translated_page.translation.source, context=context)
    translate_segment(translated_page, segment, "Passer à Firefox")
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", "Passer à Chrome")

    assert get_previous_translations(translated_page.translation) == []


def test_two_orphan_stringtranslations_at_one_context_offer_nothing(translated_page):
    """When there are multiple orphan translations, we can't choose one, so none are returned."""
    context = context_of_only_title(translated_page)
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", "Passer à Chrome")
    orphan_stringtranslation(translated_page, context, "Switch to Safari", "Passer à Safari")

    assert get_previous_translations(translated_page.translation) == []


def test_orphan_stringtranslation_with_empty_data_offers_nothing(translated_page):
    context = context_of_only_title(translated_page)
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", "")

    assert get_previous_translations(translated_page.translation) == []


@pytest.mark.parametrize(
    "marker",
    [
        # The literals are deliberate: the module reads the marker through get_marker(), so
        # spelling it out here is what would catch a change to the package default. Do not
        # "tidy" this into importing DO_NOT_TRANSLATE_MARKER — that would make the test agree
        # with the code by construction and test nothing.
        "__DO_NOT_TRANSLATE__",
        "__DO_NOT_TRANSLATE__|backup|Switch to Chrome",
    ],
    ids=["bare", "with-backup"],
)
def test_intentional_blank_marker_is_never_offered(translated_page, marker):
    context = context_of_only_title(translated_page)
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", marker)

    assert get_previous_translations(translated_page.translation) == []


def test_orphan_stringtranslation_in_another_locale_is_not_offered(translated_page):
    """A TranslationContext is unique on (object, path), so every locale's
    translations of a page hang off the same context rows. Only the locale under
    translation is a candidate: an orphan in another locale belongs to that
    locale's translator, and offering it here would both show text in a language
    this translator is not writing and, by making the context ambiguous, silence
    the entry they should have been offered.
    """
    # Currently, the translated_page is translated into French.
    assert translated_page.translation.target_locale.language_code == "fr"

    # Add an orphaned translation in German.
    context = context_of_only_title(translated_page)
    string = String.from_value(translated_page.translation.source.locale, StringValue("Switch to Chrome"))
    StringTranslation.objects.create(
        translation_of=string,
        locale=Locale.objects.create(language_code="de"),
        context=context,
        data="Zu Chrome wechseln",
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )

    assert get_previous_translations(translated_page.translation) == []


def test_errored_orphan_stringtranslation_is_still_offered(translated_page):
    """An errored translation is not usable as-is, but it is still the text a
    translator would otherwise retype from nothing."""
    context = context_of_only_title(translated_page)
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", 'Passer à <a href="/x/">Chrome</a>', has_error=True)

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].value == 'Passer à <a href="/x/">Chrome</a>'


def test_errored_current_translation_suppresses_the_entry(translated_page):
    """Since the segment is still considered translated, nothing is returned."""
    context = context_of_only_title(translated_page)
    segment = StringSegment.objects.get(source=translated_page.translation.source, context=context)
    StringTranslation.objects.update_or_create(
        translation_of_id=segment.string_id,
        locale=translated_page.locale,
        context=context,
        defaults={
            "data": 'Passer à <a href="/x/">Firefox</a>',
            "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL,
            "has_error": True,
        },
    )
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", "Passer à Chrome")

    assert get_previous_translations(translated_page.translation) == []


def test_source_with_no_segments_returns_empty(translated_page):
    StringSegment.objects.filter(source=translated_page.translation.source).delete()

    assert get_previous_translations(translated_page.translation) == []


def test_one_untranslated_paragraph_among_three_yields_that_paragraph(three_paragraph_page):
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    translate_segment(three_paragraph_page, segments[2], "Gamma FR")
    orphan_stringtranslation(three_paragraph_page, context, "Beta old", "Beta FR")

    entries = [entry for entry in get_previous_translations(three_paragraph_page.translation) if entry.field_path == "content"]

    assert len(entries) == 1
    assert entries[0].source_now == "Beta"
    assert entries[0].value == "Beta FR"


def test_two_untranslated_paragraphs_at_one_context_yield_nothing(three_paragraph_page):
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    orphan_stringtranslation(three_paragraph_page, context, "Beta old", "Beta FR")

    entries = [entry for entry in get_previous_translations(three_paragraph_page.translation) if entry.field_path == "content"]

    assert entries == []


def test_deleted_paragraph_is_paired_with_an_unrelated_new_one(three_paragraph_page):
    """
    Deleting a paragraph and appending another leaves one orphan_stringtranslation and one untranslated
    segment at the same context, so the pairing is one-to-one and the entry is offered
    even though the two have nothing to do with each other. What saves the translator
    is the display: the entry carries both source strings, and they do not match.
    """
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    for segment, value in zip(segments, ["Alpha FR", "Beta FR", "Gamma FR"]):
        translate_segment(three_paragraph_page, segment, value)

    set_rich_text(three_paragraph_page, "<p>Alpha</p><p>Gamma</p><p>Delta</p>")

    entries = [entry for entry in get_previous_translations(three_paragraph_page.translation) if entry.field_path == "content"]

    assert len(entries) == 1
    assert entries[0].source_now == "Delta"  # the paragraph that was appended
    assert entries[0].source == "Beta"  # the paragraph that was deleted
    assert entries[0].value == "Beta FR"


def test_unresolvable_field_path_falls_back_to_the_raw_path(translated_page):
    context = context_of_only_title(translated_page)
    orphan_stringtranslation(translated_page, context, "Switch to Chrome", "Passer à Chrome")
    # field_path is a stored column that get_field_path only computes when empty.
    context.field_path = ""
    context.path = "no_such_field"
    context.save(update_fields=["field_path", "path"])

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].field_path == "no_such_field"


def count_queries(translated_page):
    with CaptureQueriesContext(connection) as captured:
        get_previous_translations(translated_page.translation)
    return len(captured)


def test_query_count_does_not_grow_with_the_number_of_segments(three_paragraph_page):
    orphan_stringtranslation(three_paragraph_page, context_of_only_title(three_paragraph_page), "Switch to Chrome", "Passer à Chrome")
    count_for_a_few_strings = count_queries(three_paragraph_page)

    set_rich_text(three_paragraph_page, "".join(f"<p>Para {n}</p>" for n in range(30)))
    count_for_many_strings = count_queries(three_paragraph_page)

    assert count_for_many_strings == count_for_a_few_strings


def test_query_count_does_not_grow_with_the_number_of_contexts_and_candidates(translated_page):
    """Each translatable field is its own context, so this is the test that varies the
    thing the entry loop iterates over. One orphan_stringtranslation per context, so the entry count grows
    with the context count and the query count must not."""
    # Unconditional: SimpleRichTextPageFactory leaves `content` empty, so translated_page
    # has exactly one context until something puts body copy on it. Without this the
    # loop below has nothing to iterate and the test asserts 1 == 1.
    set_rich_text(translated_page, "<p>Body</p>")
    source = translated_page.translation.source
    contexts = [segment.context for segment in StringSegment.objects.filter(source=source).select_related("context")]
    assert len(contexts) > 1, "this test is vacuous with a single context"

    orphan_stringtranslation(translated_page, contexts[0], "Switch to Chrome", "Passer à Chrome")
    one = count_queries(translated_page)

    for index, context in enumerate(contexts[1:], start=1):
        orphan_stringtranslation(translated_page, context, f"Old source {index}", f"Ancienne traduction {index}")
    several = count_queries(translated_page)

    assert len(get_previous_translations(translated_page.translation)) == len(contexts)
    assert several == one
