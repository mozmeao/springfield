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

# The package owns both stored forms of its marker and the settings that override them,
# so we use its helper to recognise segments marked "do not translate".
from wagtail_localize_intentional_blanks.utils import is_do_not_translate

# An escape character that is invisible in a diff, in review, and to grep.
ESCAPE_CHARACTER = "\u200d"


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
    def from_pair(cls, untranslated: Sequence[StringSegment], stale: StringTranslation, is_exact: bool, field_label: str) -> Self:
        """Build an entry, turning the HTML fragments wagtail-localize stores into plain text."""
        user = stale.last_translated_by
        return cls(
            field_label=field_label,
            previous_source=StringValue(stale.translation_of.data).render_text(),
            current_sources=tuple(StringValue(segment.string.data).render_text() for segment in untranslated),
            translation=StringValue(stale.data).render_text(),
            is_exact=is_exact,
            comment=stale.get_comment(),
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
        pair = find_stale_pair(segments, translations_by_context[context_id])
        if pair:
            label = get_field_label(source_instance, tab_helper, segments[0].context)
            entries.append(PreviousTranslation.from_pair(*pair, field_label=label))
    return entries


def find_stale_pair(
    segments: Sequence[StringSegment], string_translations: Sequence[StringTranslation]
) -> tuple[list[StringSegment], StringTranslation, bool] | None:
    """
    Pair the untranslated segments of a context with the translation left over
    from text the source no longer has, and say whether the pairing is certain.

    Rich text paragraphs share a context, and an edited paragraph cannot be told
    apart from one added beside it, so every untranslated segment goes in the pair.
    wagtail-localize keeps every earlier translation, so a field edited twice holds
    two leftovers and the one written most recently is the one to offer. Rows written
    in the same moment, as an import writes them, are separated by the one added
    last (by pk).

    When there is one leftover segment and one untranslated segment, this is a match.
    Otherwise, the entry is a guess and is flagged as not exact. A segment with nothing
    to translate counts towards neither.
    """
    current_string_ids = {segment.string_id for segment in segments}
    translated_string_ids = {row.translation_of_id for row in string_translations if row.translation_of_id in current_string_ids}
    untranslated = [segment for segment in segments if segment.string_id not in translated_string_ids and has_visible_text(segment)]
    stale = [row for row in string_translations if row.translation_of_id not in current_string_ids and row.data and not is_do_not_translate(row)]

    if not untranslated or not stale:
        return None
    if len(untranslated) > 1 and len(stale) > 1:
        return None
    is_exact = len(untranslated) == 1 and len(stale) == 1
    return untranslated, max(stale, key=lambda row: (row.updated_at, row.pk)), is_exact


def has_visible_text(segment: StringSegment) -> bool:
    """Whether the segment holds anything to translate."""
    return bool(StringValue(segment.string.data).render_text().replace(ESCAPE_CHARACTER, "").strip())


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
