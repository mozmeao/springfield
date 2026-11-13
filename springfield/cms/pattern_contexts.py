# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict

from django.conf import settings

from pattern_library import register_context_modifier

from lib.l10n_utils import fluent_l10n, get_locale
from springfield.cms.blocks import icon_display_label
from springfield.cms.icon_utils import icon_value_fn

ICON_DIR = settings.ROOT_PATH / "media/img/firefox/flare/icons"


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


@register_context_modifier(template="pattern-library/base-styles/icons/icons.html")
def add_icon_groups(context, request):
    """List every icon SVG, grouped by its platform-size folder (e.g. "desktop-16")."""
    icons_by_folder = defaultdict(list)
    for svg_path in ICON_DIR.rglob("*.svg"):
        icon_path = svg_path.relative_to(ICON_DIR).with_suffix("")
        if any(part.startswith(".") for part in icon_path.parts):
            continue
        folder = icon_path.parts[0] if len(icon_path.parts) > 1 else "other"
        icons_by_folder[folder].append({"name": icon_display_label(icon_path.name), "icon_name": icon_value_fn(icon_path.as_posix())})

    def folder_sort_key(folder):
        platform, _, size = folder.partition("-")
        return (folder == "other", platform, int(size or 0))

    context["icon_groups"] = [
        {"title": folder.replace("-", " ").title(), "icons": sorted(icons_by_folder[folder], key=lambda icon: icon["name"])}
        for folder in sorted(icons_by_folder, key=folder_sort_key)
    ]


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
