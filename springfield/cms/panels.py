# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from wagtail.admin.panels import Panel


class PartnerRepackTestLinksPanel(Panel):
    """A read-only list of a partner's download links, built from the last save."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtailadmin/panels/partner_repack_test_links.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["test_links"] = self.instance.test_links()
            return context
