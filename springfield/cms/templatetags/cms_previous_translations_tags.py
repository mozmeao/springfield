# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import template

from wagtail_localize.models import Translation

from springfield.cms.previous_translations import get_previous_translations
from springfield.cms.side_panels import PreviousTranslationsSidePanel

register = template.Library()


@register.simple_tag(takes_context=True)
def side_panels_with_previous_translations(context, translation: Translation, instance) -> list:
    """The editor's side panels, plus one for segments whose source text has changed."""
    side_panels = context["side_panels"]
    entries = get_previous_translations(translation)
    if not entries:
        return side_panels

    panel = PreviousTranslationsSidePanel(
        instance,
        context["request"],
        entries=entries,
        source_locale=translation.source.locale.language_code,
        target_locale=translation.target_locale.language_code,
    )
    return [*side_panels, panel]
