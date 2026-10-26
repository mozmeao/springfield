# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict
from dataclasses import dataclass

from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist

from wagtail_localize.models import StringSegment, StringTranslation

# The package owns both stored forms of its marker and the settings that override them,
# so we use its helper methods to find segments that have been marjed by it.
from wagtail_localize_intentional_blanks.utils import is_do_not_translate


@dataclass(frozen=True)
class PreviousTranslation:
    field_path: str
    source_now: str
    source: str
    value: str
    comment: str
    translated_by: str


def get_previous_translations(translation):
    """
    Return every untranslated segment of `translation` that has exactly one
    recoverable translation at its context, in segment order.

    A context can hold many segments (for example, each paragraph of a rich
    text field shares one).
    A result here is offered only where the pairing is unambiguous: one
    untranslated segment and one translation.
    """
    segments = defaultdict(list)
    for segment in StringSegment.objects.filter(source_id=translation.source_id).select_related("context", "string").order_by("order"):
        segments[segment.context_id].append(segment)

    if not segments:
        return []

    rows = StringTranslation.objects.filter(locale_id=translation.target_locale_id, context_id__in=list(segments)).select_related(
        "translation_of", "last_translated_by"
    )

    live = defaultdict(set)
    orphans = defaultdict(list)
    for row in rows:
        strings_here = {segment.string_id for segment in segments[row.context_id]}
        if row.translation_of_id in strings_here:
            # An errored row still counts as the segment's current translation.
            live[row.context_id].add(row.translation_of_id)
        elif row.data and not is_do_not_translate(row):
            # A blank the editor chose on purpose, not a translation. We make
            # sure to avoid showing the marker itself to the user.
            orphans[row.context_id].append(row)

    if not orphans:
        return []

    source_instance = translation.source.get_source_instance()
    entries = []
    # segments was filled in `order`, so iterating it keeps the bar in page order.
    for context_id, context_segments in segments.items():
        candidates = orphans.get(context_id, [])
        if len(candidates) != 1:
            continue
        untranslated = [segment for segment in context_segments if segment.string_id not in live[context_id]]
        if len(untranslated) != 1:
            continue
        entries.append(_entry(untranslated[0], candidates[0], source_instance))

    return entries


def _entry(segment, previous, source_instance):
    return PreviousTranslation(
        field_path=_get_field_path(segment.context, source_instance),
        source_now=segment.string.data,
        source=previous.translation_of.data,
        value=previous.data,
        comment=previous.get_comment(),
        translated_by=_get_display_name(previous.last_translated_by),
    )


def _get_display_name(user):
    if user is None:
        return ""
    return user.get_full_name() or user.get_username()


def _get_field_path(context, source_instance):
    try:
        return context.get_field_path(source_instance)
    except (FieldDoesNotExist, ObjectDoesNotExist, KeyError, IndexError, TypeError):
        return context.path
