# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import Sequence

from django.utils.translation import gettext_lazy

from wagtail.admin.ui.side_panels import BaseSidePanel

from springfield.cms.previous_translations import PreviousTranslation


class PreviousTranslationsSidePanel(BaseSidePanel):
    """
    The translations left behind by segments whose source text has since changed,
    shown beside the translation editor.

    Locale codes are passed in rather than read from the translation: the panel renders
    what it is given.

    Note: the editor view collects the side panels' media before this panel is
    appended to them, so a Media declaration here would be dropped without warning.
    """

    class SidePanelToggle(BaseSidePanel.SidePanelToggle):
        aria_label = gettext_lazy("Toggle previous translations")
        icon_name = "history"

        def get_context_data(self, parent_context):
            context = super().get_context_data(parent_context)
            context["count"] = len(self.panel.entries)
            return context

    name = "previous-translations"
    title = gettext_lazy("Previous translations")
    template_name = "wagtail_localize/admin/previous_translations_panel.html"

    def __init__(
        self,
        *args,
        entries: Sequence[PreviousTranslation],
        source_locale: str,
        target_locale: str,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.entries = entries
        self.source_locale = source_locale
        self.target_locale = target_locale

    def get_context_data(self, parent_context):
        context = super().get_context_data(parent_context)
        context["entries"] = self.entries
        context["source_locale"] = self.source_locale
        context["target_locale"] = self.target_locale
        return context
