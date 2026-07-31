# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin views for the "User Routing" submenu."""

from django.views.generic import TemplateView

from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from springfield.cms.routing.admin import build_signal_reference
from springfield.cms.routing.models import RoutingRule


class RoutingRulesIndexView(WagtailAdminTemplateMixin, TemplateView):
    """A read/browse aggregation of routing rules across pages.

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


class RoutingSignalsReferenceView(WagtailAdminTemplateMixin, TemplateView):
    """The auto-generated Signals reference page.

    Renders the whole registry as a table, generated from the registry so it never
    drifts from what the evaluator reads.
    """

    template_name = "wagtailadmin/routing/signals_reference.html"
    page_title = "Routing signals reference"
    header_icon = "help"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["signals"] = build_signal_reference()
        return context
