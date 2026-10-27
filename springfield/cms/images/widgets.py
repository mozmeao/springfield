# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from wagtail.admin.widgets import AdminTagWidget


class AdminTagNoHelpWidget(AdminTagWidget):
    """Remove hard-coded help text from the widget. The help text is
    displayed in the column header instead. See
    `cms.images.views.InlineTagsColumn`."""

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["help_text"] = ""
        return context
