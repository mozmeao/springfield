# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import timedelta
from types import SimpleNamespace

from django.db import connection
from django.test.utils import CaptureQueriesContext

import pytest
from wagtail.models import Locale
from wagtail_localize.models import String, StringSegment, StringTranslation, Translation, TranslationSource
from wagtail_localize.strings import StringValue
from wagtail_localize.views.edit_translation import TabHelper
from wagtail_localize_intentional_blanks.utils import mark_segment_do_not_translate

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL
from springfield.cms.previous_translations import ZERO_WIDTH_JOIN_CHARACTER, get_field_label, get_previous_translations
from springfield.cms.tests.factories import FreeFormPage2026Factory
from springfield.cms.tests.helpers import content_context, orphan_stringtranslation, set_rich_text, title_context

pytestmark = pytest.mark.django_db


def translate_segment(translated_page, segment, value):
    StringTranslation.objects.create(
        translation_of_id=segment.string_id,
        locale=translated_page.locale,
        context=segment.context,
        data=value,
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )


@pytest.fixture
def translated_freeform_page(minimal_site):
    """
    A translated page whose text sits in stream blocks, where the editor's name for a field
    and the model's name for it are different.
    """
    source_page = FreeFormPage2026Factory(
        title="Switch to Firefox",
        slug="switch-to-firefox-blocks",
        parent=minimal_site.root_page,
        content=[
            {"type": "rich_text", "value": "<p>Alpha</p>", "id": "11111111-1111-1111-1111-111111111111"},
            {
                "type": "intro",
                "value": {
                    # Every child of the block: a missing one reaches segment extraction as None,
                    # which it cannot read.
                    "settings": {
                        "layout": "vertical",
                        "full_width": False,
                        "slim": False,
                        "show_to": SHOW_TO_ALL,
                        "anchor_id": "",
                        "remove_border_radius": False,
                    },
                    "media": [],
                    "heading": {"superheading_text": "", "heading_text": "<p>Beta</p>", "subheading_text": ""},
                    "content": [],
                },
                "id": "22222222-2222-2222-2222-222222222222",
            },
        ],
    )
    locale = Locale.objects.get(language_code="fr")
    source, _ = TranslationSource.get_or_create_from_instance(source_page)
    translation = Translation.objects.create(source=source, target_locale=locale, enabled=True)
    return SimpleNamespace(source_page=source_page, translation=translation, locale=locale)


@pytest.fixture
def three_paragraph_page(translated_page):
    set_rich_text(translated_page, "<p>Alpha</p><p>Beta</p><p>Gamma</p>")
    return translated_page


def test_drifted_segment_offers_its_previous_translation(translated_page):
    context = title_context(translated_page)
    orphan_stringtranslation(translated_page, context, "Try Firefox", "Essayez Firefox")

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].previous_source == "Try Firefox"
    assert entries[0].current_sources == ("Switch to Firefox",)
    assert entries[0].translation == "Essayez Firefox"
    assert entries[0].is_exact


def test_entries_name_the_field_each_one_came_from(translated_page):
    set_rich_text(translated_page, "<p>Switch today</p>")
    orphan_stringtranslation(translated_page, title_context(translated_page), "Try Firefox", "Essayez Firefox")
    orphan_stringtranslation(translated_page, content_context(translated_page), "Switch now", "Changez maintenant")

    entries = get_previous_translations(translated_page.translation)

    assert {entry.field_label for entry in entries} == {"Title", "Content"}


def test_a_context_whose_field_no_longer_exists_is_left_unlabelled(translated_page):
    source_instance = translated_page.translation.source.get_source_instance()
    context = title_context(translated_page)
    context.path = context.field_path = "field_that_was_renamed"

    assert get_field_label(source_instance, TabHelper(source_instance), context) == ""


def test_a_block_is_named_as_the_translation_editor_names_it(translated_freeform_page):
    """
    The panel sits beside the editor (from wagtail-localize), so the segment
    labels match what the editor shows.
    """
    source = translated_freeform_page.translation.source
    for segment in StringSegment.objects.filter(source=source, context__path__startswith="content.").select_related("context"):
        orphan_stringtranslation(translated_freeform_page, segment.context, "Old text", "Ancien texte")

    entries = get_previous_translations(translated_freeform_page.translation)

    assert {entry.field_label for entry in entries} == {"Rich text", "Intro › Heading"}


def test_untouched_translation_offers_nothing(translated_page):
    assert get_previous_translations(translated_page.translation) == []


def test_current_translation_suppresses_an_orphan_stringtranslation_at_its_context(translated_page):
    """A segment that already has a translation does not return its previous translation."""
    context = title_context(translated_page)
    segment = StringSegment.objects.get(source=translated_page.translation.source, context=context)
    translate_segment(translated_page, segment, "Passer à Firefox")
    orphan_stringtranslation(translated_page, context, "Try Firefox", "Essayez Firefox")

    assert get_previous_translations(translated_page.translation) == []


def test_field_edited_twice_offers_its_latest_translation(translated_page):
    """A field edited twice keeps a translation of each earlier version; the latest one is offered."""
    context = title_context(translated_page)
    older = orphan_stringtranslation(translated_page, context, "Try Firefox", "Essayez Firefox")
    latest = orphan_stringtranslation(translated_page, context, "Download Firefox", "Téléchargez Firefox")
    StringTranslation.objects.filter(pk=older.pk).update(updated_at=latest.updated_at - timedelta(days=1))

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].previous_source == latest.translation_of.data
    assert entries[0].translation == latest.data
    # Offering the latest is a heuristic: the entry says so rather than claiming the
    # translator's edit certainly produced this one.
    assert not entries[0].is_exact


def test_a_field_edited_and_translated_twice_still_offers_a_previous_translation(translated_page):
    """
    The panel shows the previous translation, not all of the previous translations.

    Each edit leaves another translation behind, so a field edited twice has
    two of them, but the panel should only show the most recent one.
    """
    source = translated_page.translation.source
    set_rich_text(translated_page, "<p>Get Firefox</p>")
    translate_segment(translated_page, StringSegment.objects.get(source=source, context__path="content"), "Obtenez Firefox")
    set_rich_text(translated_page, "<p>Get Firefox now</p>")
    translate_segment(translated_page, StringSegment.objects.get(source=source, context__path="content"), "Obtenez Firefox maintenant")
    set_rich_text(translated_page, "<p>Get Firefox today</p>")

    entries = get_previous_translations(translated_page.translation)

    assert StringTranslation.objects.filter(locale=translated_page.locale, context__path="content").count() == 2
    assert [(entry.previous_source, entry.translation) for entry in entries] == [("Get Firefox now", "Obtenez Firefox maintenant")]


def test_orphan_stringtranslations_written_at_the_same_moment_offer_the_later_row(translated_page):
    """
    An import writes a whole file of translations in one go, so two leftovers can share a
    timestamp to the microsecond. Picking by timestamp alone leaves the database to break
    the tie and the panel showing a different translation on different machines.
    """
    context = title_context(translated_page)
    earlier = orphan_stringtranslation(translated_page, context, "Try Firefox", "Essayez Firefox")
    later = orphan_stringtranslation(translated_page, context, "Download Firefox", "Téléchargez Firefox")
    StringTranslation.objects.filter(pk=earlier.pk).update(updated_at=later.updated_at)

    entries = get_previous_translations(translated_page.translation)

    assert entries[0].translation == later.data


def test_several_untranslated_paragraphs_and_several_orphan_stringtranslations_offer_nothing(three_paragraph_page):
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    orphan_stringtranslation(three_paragraph_page, context, "Beta old", "Beta FR")
    orphan_stringtranslation(three_paragraph_page, context, "Gamma old", "Gamma FR")

    assert get_previous_translations(three_paragraph_page.translation) == []


def test_one_untranslated_paragraph_with_two_orphan_stringtranslations_offers_the_latest(three_paragraph_page):
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    translate_segment(three_paragraph_page, segments[2], "Gamma FR")
    older = orphan_stringtranslation(three_paragraph_page, context, "Beta older", "Beta FR ancien")
    latest = orphan_stringtranslation(three_paragraph_page, context, "Beta old", "Beta FR")
    StringTranslation.objects.filter(pk=older.pk).update(updated_at=latest.updated_at - timedelta(days=1))

    entries = get_previous_translations(three_paragraph_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Beta",)
    assert entries[0].previous_source == "Beta old"
    assert entries[0].translation == "Beta FR"
    assert not entries[0].is_exact


def test_orphan_stringtranslation_with_empty_data_offers_nothing(translated_page):
    context = title_context(translated_page)
    orphan_stringtranslation(translated_page, context, "Try Firefox", "")

    assert get_previous_translations(translated_page.translation) == []


@pytest.mark.parametrize(
    "marker",
    [
        # The literals here are intentional, to catch changes to the package default.
        "__DO_NOT_TRANSLATE__",
        "__DO_NOT_TRANSLATE__|backup|Try Firefox",
    ],
    ids=["bare", "with-backup"],
)
def test_intentional_blank_marker_is_never_offered(translated_page, marker):
    context = title_context(translated_page)
    orphan_stringtranslation(translated_page, context, "Try Firefox", marker)

    assert get_previous_translations(translated_page.translation) == []


def test_a_field_marked_do_not_translate_and_then_edited_does_not_appear_in_panel(translated_page):
    """
    Since the field was marked as "Do Not Translate", it is still considered
    translated, so it is not offered as a previous translation.
    """
    source = translated_page.translation.source
    set_rich_text(translated_page, "<p>Get Firefox</p>")
    translate_segment(translated_page, StringSegment.objects.get(source=source, context__path="content"), "Obtenez Firefox")
    set_rich_text(translated_page, "<p>Get Firefox now</p>")
    mark_segment_do_not_translate(translated_page.translation, StringSegment.objects.get(source=source, context__path="content"))

    set_rich_text(translated_page, "<p>Get Firefox today</p>")

    # The literal is intentional, to catch changes to
    # the wagtail_localize_intentional_blanks default.
    marker_row = StringTranslation.objects.get(locale=translated_page.locale, context__path="content", data__startswith="__DO_NOT_TRANSLATE__")
    assert marker_row.translation_of_id == StringSegment.objects.get(source=source, context__path="content").string_id
    assert get_previous_translations(translated_page.translation) == []


def test_orphan_stringtranslation_in_another_locale_is_not_offered(translated_page):
    # Currently, the translated_page is translated into French.
    assert translated_page.translation.target_locale.language_code == "fr"

    # Add an orphaned translation in German.
    context = title_context(translated_page)
    string = String.from_value(translated_page.translation.source.locale, StringValue("Try Firefox"))
    StringTranslation.objects.create(
        translation_of=string,
        locale=Locale.objects.create(language_code="de"),
        context=context,
        data="Firefox ausprobieren",
        translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
    )

    assert get_previous_translations(translated_page.translation) == []


def test_errored_orphan_stringtranslation_is_still_offered(translated_page):
    """An errored translation is not usable as-is, but it is still the text a
    translator would otherwise retype from nothing."""
    context = title_context(translated_page)
    orphan_stringtranslation(translated_page, context, "Try Firefox", 'Essayez <a href="/x/">Firefox</a>', has_error=True)

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].translation == "Essayez Firefox"


def test_errored_current_translation_suppresses_the_entry(translated_page):
    """Since the segment is still considered translated, nothing is returned."""
    context = title_context(translated_page)
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
    orphan_stringtranslation(translated_page, context, "Try Firefox", "Essayez Firefox")

    assert get_previous_translations(translated_page.translation) == []


def test_orphan_stringtranslation_without_a_translation_type_has_no_comment(translated_page):
    """
    wagtail-localize builds the comment from the translation type, and has
    nothing to say about a row that carries neither a type nor a tool. The
    'previous translations' panel shows the comment, so it even if it is blank.
    """
    context = title_context(translated_page)
    orphan_stringtranslation(translated_page, context, "Try Firefox", "Essayez Firefox", translation_type="")

    entries = get_previous_translations(translated_page.translation)

    assert entries[0].comment is None


def test_source_with_no_segments_returns_empty(translated_page):
    StringSegment.objects.filter(source=translated_page.translation.source).delete()

    assert get_previous_translations(translated_page.translation) == []


def test_one_untranslated_paragraph_among_three_yields_that_paragraph(three_paragraph_page):
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    translate_segment(three_paragraph_page, segments[2], "Gamma FR")
    orphan_stringtranslation(three_paragraph_page, context, "Beta old", "Beta FR")

    entries = get_previous_translations(three_paragraph_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Beta",)
    assert entries[0].translation == "Beta FR"
    assert entries[0].is_exact


def test_untranslated_paragraphs_at_one_context_are_offered_as_separate_candidates(three_paragraph_page):
    """An edited paragraph next to an added one cannot be told apart, so the entry carries
    each as its own candidate."""
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    orphan_stringtranslation(three_paragraph_page, context, "Beta old", "Beta FR")

    entries = get_previous_translations(three_paragraph_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Beta", "Gamma")
    assert entries[0].previous_source == "Beta old"
    assert entries[0].translation == "Beta FR"
    assert not entries[0].is_exact


def test_a_zero_width_joiner_paragraph_on_its_own_offers_nothing(translated_page):
    """
    A paragraph holding only a zero-width joiner is nothing anyone can translate, so a
    leftover translation has nothing at that context to pair with.
    """
    set_rich_text(translated_page, "<p>Alpha</p><p>\u200d</p>")
    context = content_context(translated_page)
    first_paragraph = StringSegment.objects.filter(source=translated_page.translation.source, context=context).order_by("order").first()
    translate_segment(translated_page, first_paragraph, "Alpha FR")
    orphan_stringtranslation(translated_page, context, "Beta old", "Beta FR")

    assert get_previous_translations(translated_page.translation) == []


def test_a_zero_width_joiner_paragraph_does_not_make_the_pairing_a_guess(translated_page):
    """One real paragraph beside an empty one is one candidate, so the entry is exact."""
    set_rich_text(translated_page, "<p>Alpha</p><p>\u200d</p>")
    context = content_context(translated_page)
    orphan_stringtranslation(translated_page, context, "Alpha old", "Alpha FR ancien")

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Alpha",)
    assert entries[0].is_exact


def test_a_zero_width_joiner_paragraph_does_not_silence_an_entry(three_paragraph_page):
    set_rich_text(three_paragraph_page, f"<p>Alpha</p><p>{ZERO_WIDTH_JOIN_CHARACTER}</p><p>Gamma</p>")
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    translate_segment(three_paragraph_page, segments[0], "Alpha FR")
    older = orphan_stringtranslation(three_paragraph_page, context, "Gamma older", "Gamma FR ancien")
    latest = orphan_stringtranslation(three_paragraph_page, context, "Gamma old", "Gamma FR")
    StringTranslation.objects.filter(pk=older.pk).update(updated_at=latest.updated_at - timedelta(days=1))

    entries = get_previous_translations(three_paragraph_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Gamma",)
    assert entries[0].translation == "Gamma FR"
    assert not entries[0].is_exact


def test_zero_width_joiner_paragraph_is_left_out_of_the_entry(translated_page):
    """Splitting a paragraph in the editor can leave one holding only a zero-width joiner."""
    set_rich_text(translated_page, "<p>Alpha</p><p>\u200d</p><p>Gamma</p>")
    orphan_stringtranslation(translated_page, content_context(translated_page), "Alpha Gamma old", "Alpha Gamma FR")

    entries = get_previous_translations(translated_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Alpha", "Gamma")


def test_deleted_paragraph_is_paired_with_an_unrelated_new_one(three_paragraph_page):
    """
    Deleting a paragraph and appending another leaves one
    orphan_stringtranslation and one untranslated segment at the same context,
    so the the entry is offered, even though the two do not necessarily match.
    We offer the previous translation, and leave it to the editor to determine
    what to do.
    """
    context = content_context(three_paragraph_page)
    segments = list(StringSegment.objects.filter(source=three_paragraph_page.translation.source, context=context).order_by("order"))
    for segment, value in zip(segments, ["Alpha FR", "Beta FR", "Gamma FR"]):
        translate_segment(three_paragraph_page, segment, value)

    set_rich_text(three_paragraph_page, "<p>Alpha</p><p>Gamma</p><p>Delta</p>")

    entries = get_previous_translations(three_paragraph_page.translation)

    assert len(entries) == 1
    assert entries[0].current_sources == ("Delta",)  # the paragraph that was appended
    assert entries[0].previous_source == "Beta"  # the paragraph that was deleted
    assert entries[0].translation == "Beta FR"
    assert entries[0].is_exact


def count_queries(translated_page):
    with CaptureQueriesContext(connection) as captured:
        get_previous_translations(translated_page.translation)
    return len(captured)


def test_query_count_does_not_grow_with_the_number_of_segments(three_paragraph_page):
    orphan_stringtranslation(three_paragraph_page, title_context(three_paragraph_page), "Try Firefox", "Essayez Firefox")
    count_for_a_few_strings = count_queries(three_paragraph_page)

    set_rich_text(three_paragraph_page, "".join(f"<p>Para {n}</p>" for n in range(30)))
    count_for_many_strings = count_queries(three_paragraph_page)

    assert count_for_many_strings == count_for_a_few_strings


def test_query_count_does_not_grow_with_the_number_of_contexts_and_candidates(translated_page):
    set_rich_text(translated_page, "<p>Body</p>")
    source = translated_page.translation.source
    contexts = [segment.context for segment in StringSegment.objects.filter(source=source).select_related("context")]
    assert len(contexts) > 1, "this test is vacuous with a single context"

    orphan_stringtranslation(translated_page, contexts[0], "Try Firefox", "Essayez Firefox")
    one = count_queries(translated_page)

    for index, context in enumerate(contexts[1:], start=1):
        orphan_stringtranslation(translated_page, context, f"Old source {index}", f"Ancienne traduction {index}")
    several = count_queries(translated_page)

    assert len(get_previous_translations(translated_page.translation)) == len(contexts)
    assert several == one
