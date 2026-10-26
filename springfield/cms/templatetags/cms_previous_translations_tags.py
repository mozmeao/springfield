# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import template
from django.conf import settings

from springfield.cms.previous_translations import get_previous_translations

register = template.Library()


@register.inclusion_tag("wagtail_localize/admin/previous_translations_bar.html")
def previous_translations_bar(translation):
    """The bar of recoverable translations shown above the translation editor."""
    if not settings.CMS_PREVIOUS_TRANSLATIONS_ENABLED:
        return {"entries": []}

    return {
        "entries": get_previous_translations(translation),
        "source_locale": translation.source.locale.language_code,
        "target_locale": translation.target_locale.language_code,
    }
