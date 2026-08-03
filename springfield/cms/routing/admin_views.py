# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin views for the "User Routing" submenu."""

from django.views.generic import TemplateView

from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from springfield.cms.routing.admin import build_signal_reference
from springfield.cms.routing.models import RoutingRule
from springfield.cms.routing.resolver import rule_problems


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
        rules = RoutingRule.objects.select_related("page", "target").prefetch_related("conditions").order_by("page_id", "sort_order", "pk")
        context["rows"] = _rows_with_status(rules)
        return context


def _rows_with_status(rules):
    """Pair each rule with why it cannot route anyone, or ``None`` if it can.

    A rule that is dropped at serve time looks completely healthy in a plain listing: the
    target column shows a real page, the condition count looks right, and nothing says the
    rule is inert. Several of the ways that happens are invisible in the row itself — the
    target belongs to a different page's subtree, or has no version in this page's language.

    Rules arrive ordered by page, so the per-page lookup runs once per page rather than once
    per rule.
    """
    rows = []
    problems = {}
    current_page_id = None
    for rule in rules:
        if rule.page_id != current_page_id:
            current_page_id = rule.page_id
            problems = rule_problems(rule.page)
        rows.append({"rule": rule, "problem": problems.get(rule.pk)})
    return rows


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
