# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from operator import attrgetter
from typing import Self

from wagtail_localize.models import StringSegment, StringTranslation, Translation
from wagtail_localize.strings import StringValue

# The package owns both stored forms of its marker and the settings that override them,
# so we use its helper to recognise segments marked "do not translate".
from wagtail_localize_intentional_blanks.utils import is_do_not_translate


@dataclass(frozen=True)
class PreviousTranslation:
    source_then: str
    source_now: str
    translation: str
    comment: str
    translated_by: str

    @classmethod
    def from_pair(cls, untranslated: Sequence[StringSegment], stale: StringTranslation) -> Self:
        """
        Build an entry, turning the HTML fragments wagtail-localize stores into plain text.

        Splitting a paragraph in the editor can leave one holding only a zero-width
        joiner, so segments with no visible text are left out of `source_now`.
        """
        user = stale.last_translated_by
        untranslated_texts = [StringValue(segment.string.data).render_text() for segment in untranslated]
        return cls(
            source_then=StringValue(stale.translation_of.data).render_text(),
            source_now=" ".join(text for text in untranslated_texts if text.replace("‍", "").strip()),
            translation=StringValue(stale.data).render_text(),
            comment=stale.get_comment(),
            translated_by=(user.get_full_name() or user.get_username()) if user else "",
        )


def get_previous_translations(translation: Translation) -> list[PreviousTranslation]:
    """Previous translations for fields whose source text changed since they were translated, in page order."""
    segments_by_context: defaultdict[int, list[StringSegment]] = defaultdict(list)
    for segment in StringSegment.objects.filter(source_id=translation.source_id).select_related("string").order_by("order"):
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
            entries.append(PreviousTranslation.from_pair(*pair))
    return entries


def find_stale_pair(
    segments: Sequence[StringSegment], string_translations: Sequence[StringTranslation]
) -> tuple[list[StringSegment], StringTranslation] | None:
    """
    Pair the untranslated segments of a context with the translation left over
    from text the source no longer has.

    Rich text paragraphs share a context, and an edited paragraph cannot be told
    apart from one added beside it, so every untranslated segment goes in the pair.
    wagtail-localize keeps every earlier translation, so a field edited twice holds
    two leftovers and the latest is the one to offer. In rich text several leftovers
    cannot be told apart, so nothing is offered.
    """
    current_string_ids = {segment.string_id for segment in segments}
    translated_string_ids = {row.translation_of_id for row in string_translations if row.translation_of_id in current_string_ids}
    untranslated = [segment for segment in segments if segment.string_id not in translated_string_ids]
    stale = [row for row in string_translations if row.translation_of_id not in current_string_ids and row.data and not is_do_not_translate(row)]

    if not untranslated or not stale:
        return None
    if len(segments) > 1 and len(stale) > 1:
        return None
    return untranslated, max(stale, key=attrgetter("updated_at"))
