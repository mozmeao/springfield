# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model

from wagtail_localize.models import StringSegment, StringTranslation, Translation, TranslationContext
from wagtail_localize.strings import StringValue
from wagtail_localize.views.edit_translation import TabHelper, get_segment_location_info
from wagtail_localize_intentional_blanks.utils import is_do_not_translate

# Splitting a paragraph in the rich text editor can leave one of these behind as a
# paragraph's only content, which reads as empty and has nothing to translate.
ZERO_WIDTH_JOIN_CHARACTER = "\u200d"


@dataclass(frozen=True)
class PreviousTranslation:
    """
    One translation left behind by a source edit, with the text that stands where it
    used to apply.

    `previous_source` and `translation` were written together and are a matter of record.
    `current_sources` is what the field holds that nobody has translated yet.
    """

    field_label: str
    previous_source: str
    current_sources: tuple[str, ...]
    translation: str
    is_exact: bool
    # Note: wagtail-localize builds the comment from the tool or the translation
    # type, so the comment may be blank when a row has neither.
    comment: str | None
    translated_by: str

    @classmethod
    def from_leftover(cls, leftover: StringTranslation, current_sources: tuple[str, ...], is_exact: bool, field_label: str) -> Self:
        """Build an entry, turning the HTML fragments wagtail-localize stores into plain text."""
        user = leftover.last_translated_by
        return cls(
            field_label=field_label,
            previous_source=StringValue(leftover.translation_of.data).render_text(),
            current_sources=current_sources,
            translation=StringValue(leftover.data).render_text(),
            is_exact=is_exact,
            comment=leftover.get_comment(),
            translated_by=(user.get_full_name() or user.get_username()) if user else "",
        )


def get_previous_translations(translation: Translation) -> list[PreviousTranslation]:
    """Previous translations for fields whose source text changed since they were translated, in page order."""
    source_instance = translation.source.get_source_instance()
    tab_helper = TabHelper(source_instance)
    segments_by_context: defaultdict[int, list[StringSegment]] = defaultdict(list)
    for segment in StringSegment.objects.filter(source_id=translation.source_id).select_related("string", "context").order_by("order"):
        segments_by_context[segment.context_id].append(segment)

    translations_by_context: defaultdict[int, list[StringTranslation]] = defaultdict(list)
    for string_translation in StringTranslation.objects.filter(
        locale_id=translation.target_locale_id, context_id__in=segments_by_context
    ).select_related("translation_of", "last_translated_by"):
        translations_by_context[string_translation.context_id].append(string_translation)

    entries = []
    for context_id, segments in segments_by_context.items():
        pairing = find_stale_pairing(segments, translations_by_context[context_id])
        if pairing is not None:
            untranslated, leftovers, is_exact = pairing
            # Every leftover at a context is offered against the same untranslated text, so
            # that text is read once rather than once per entry.
            current_sources = tuple(StringValue(segment.string.data).render_text() for segment in untranslated)
            label = get_field_label(source_instance, tab_helper, segments[0].context)
            entries.extend(
                PreviousTranslation.from_leftover(leftover, current_sources=current_sources, is_exact=is_exact, field_label=label)
                for leftover in leftovers
            )
    return entries


def find_stale_pairing(
    segments: Sequence[StringSegment], string_translations: Sequence[StringTranslation]
) -> tuple[list[StringSegment], list[StringTranslation], bool] | None:
    """
    Pair the untranslated segments of a context with the translations left over
    from text the source no longer has, and say whether the pairing is certain.

    Rich text paragraphs share a context, and an edited paragraph cannot be told
    apart from one added beside it, so every untranslated segment goes in the pairing.
    wagtail-localize keeps every earlier translation, so leftovers build up over a
    field's life. At most one leftover is offered per untranslated segment, taking the
    ones written most recently. Rows written in the same moment, as an import writes
    them, are separated by the one added last (by pk).

    A pairing is a match of one leftover and one untranslated segment, or when
    the context holds a single segment. Otherwise each leftover is a guess and
    is flagged as not exact.
    """
    current_string_ids = {segment.string_id for segment in segments}
    leftovers = [row for row in string_translations if row.translation_of_id not in current_string_ids and row.data and not is_do_not_translate(row)]
    if not leftovers:
        return None

    # Most fields have no leftover to offer, and reading a segment's text means parsing
    # its HTML, so nothing is parsed until there is something to pair it with.
    translated_string_ids = {row.translation_of_id for row in string_translations}
    untranslated = [segment for segment in segments if segment.string_id not in translated_string_ids and has_visible_text(segment)]
    if not untranslated:
        return None
    # If a paragraph is deleted while another is added, it leaves a single
    # leftover, which looks the same as when a second paragraph is edited.
    # We don't try to definitively solve for this scenario; we just mark it as
    # an inexact match.
    is_exact = len(untranslated) == 1 and (len(segments) == 1 or len(leftovers) == 1)
    newest_first = sorted(leftovers, key=lambda row: (row.updated_at, row.pk), reverse=True)
    return untranslated, newest_first[: len(untranslated)], is_exact


def has_visible_text(segment: StringSegment) -> bool:
    """Whether the segment holds anything to translate."""
    return bool(StringValue(segment.string.data).render_text().replace(ZERO_WIDTH_JOIN_CHARACTER, "").strip())


def get_field_label(source_instance: Model, tab_helper: TabHelper, context: TranslationContext) -> str:
    """
    Return the label for this field.

    This label matches what wagtail-localize already shows the user for each
    segment.
    """
    try:
        location = get_segment_location_info(source_instance, tab_helper, context.path, context.get_field_path(source_instance))
    except (KeyError, FieldDoesNotExist):
        return ""

    return " › ".join(str(part) for part in (location["field"], location["subField"]) if part)
