# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin views for the "User Routing" submenu (spec §6.1, §4.5)."""

from django.views.generic import TemplateView

from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from springfield.cms.routing.models import RoutingRule


class RoutingRulesIndexView(WagtailAdminTemplateMixin, TemplateView):
    """A read/browse aggregation of routing rules across pages (spec §6.1).

    Purely a listing: rules are only ever authored inline on their canonical page, so
    there is deliberately **no add affordance** here.
    """

    template_name = "wagtailadmin/routing/rules_index.html"
    page_title = "User Routing rules"
    header_icon = "list-ul"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rules"] = RoutingRule.objects.select_related("page", "target").prefetch_related("conditions").order_by("page_id", "sort_order", "pk")
        return context
