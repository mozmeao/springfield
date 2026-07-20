# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from pattern_library import register_context_modifier

from lib.l10n_utils import fluent_l10n, get_locale


@register_context_modifier
def add_fluent_context(context, request):
    """Add Fluent localization context to pattern library rendering context
    for CMS pages.
    This ensures that Fluent strings render correctly in pattern library
    previews of CMS pages.
    """
    locale = get_locale(request)

    context["fluent_l10n"] = fluent_l10n([locale, "en"], settings.FLUENT_DEFAULT_FILES)
    return context


def pattern_library_l10n_context(request):
    """Add localization context to pattern library requests. The `add_fluent_context` modifier
    only applies to the context used for the pattern rendering, not the surrounding page context.
    """

    if request.path.startswith("/pattern-library/"):
        locale = get_locale(request)
        return {
            "fluent_l10n": fluent_l10n([locale, "en"], settings.FLUENT_DEFAULT_FILES),
        }
    return {}
