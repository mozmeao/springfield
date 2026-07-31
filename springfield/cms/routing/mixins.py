# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The routing adoption mixin (spec §2.2).

``RoutingMixin`` is the whole adoption surface a consumer page type touches. It
declares exactly three overridable hooks — a **trigger**, an **eligibility
predicate**, and a **signal subset** — and wires a "User Routing" edit tab holding
the rules and kill-switch panels. It adds **no database fields** (all state lives in
the C3 tables keyed to ``wagtailcore.Page``), so adopting it produces **no
migration**. The serve-path dispatch is wired later (C10); this mixin only owns the
declaration surface and the admin tab.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

import waffle
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import InlinePanel, ObjectList, TabbedInterface
from wagtail.utils.decorators import cached_classmethod

from springfield.cms.routing.dispatch import SERVE_PREVIEW, SERVE_RESOLVER, USER_ROUTING_SWITCH, decide_routing
from springfield.cms.routing.models import RoutingConfig
from springfield.cms.routing.params import LOOP_BREAKER_PARAM
from springfield.cms.routing.signals import registry


class RoutingPageForm(WagtailAdminPageForm):
    """Page form enforcing the rule condition-floor across the nested routing formsets.

    A rule with no conditions matches every triggered visitor, so it must opt in via
    ``match_all`` (plan P0-2). The model's ``clean()`` can't enforce this during a
    Wagtail save: modelcluster attaches a rule's conditions to the rule instance only
    at *save* time, after validation, so a model-level count check would reject a
    perfectly valid rule (its conditions aren't visible yet). The floor therefore lives
    here — where the nested ``conditions`` formset is inspectable — and the error lands
    on the offending rule's ``match_all`` field.
    """

    def clean(self):
        cleaned_data = super().clean()
        rules_formset = self.formsets.get("routing_rules")
        if rules_formset is not None:
            # Force nested validation now: ClusterForm validates child formsets only
            # after this form's clean() runs, so the conditions aren't populated yet.
            rules_formset.is_valid()
            for rule_form in rules_formset.forms:
                self._enforce_condition_floor(rule_form)
        return cleaned_data

    @staticmethod
    def _enforce_condition_floor(rule_form):
        data = getattr(rule_form, "cleaned_data", None)
        # Skip blank extra rows, rows marked for deletion, and explicit match-all rules.
        if not data or data.get("DELETE") or data.get("match_all"):
            return
        conditions_formset = rule_form.formsets.get("conditions")
        condition_forms = conditions_formset.forms if conditions_formset is not None else []
        has_condition = any(
            getattr(condition_form, "cleaned_data", None) and not condition_form.cleaned_data.get("DELETE") for condition_form in condition_forms
        )
        if not has_condition:
            rule_form.add_error("match_all", _("Add at least one condition, or enable “Match all triggered visitors”."))


def routing_tab_is_shown(instance):
    """Whether the "User Routing" tab should render for ``instance``.

    The tab is shown only on canonical instances (plan C4): a routing-enabled page
    *type* can have non-canonical instances (e.g. a variant nested under a canonical)
    whose rules would never fire at dispatch, so presenting a fully-functional-looking
    routing tab there would be dead config. Evaluated from the page's own eligibility
    predicate, which reads its tree position.
    """
    predicate = getattr(instance, "is_routing_canonical", None)
    return bool(instance is not None and callable(predicate) and predicate())


class RoutingObjectList(ObjectList):
    """An edit-tab that renders only on canonical instances (plan C4)."""

    class BoundPanel(ObjectList.BoundPanel):
        def is_shown(self):
            return routing_tab_is_shown(self.instance)


class RoutingMixin(models.Model):
    """Abstract mixin a Wagtail page type mixes in to adopt routing (spec §2.2).

    A consumer declares exactly three things by overriding the hooks below and adds
    no view code, no framework code, and no schema. List this mixin **before** the
    page base class so its ``get_edit_handler`` wins in the MRO.
    """

    class Meta:
        abstract = True

    # -- Adoption surface: the only three things a consumer declares (spec §2.2) --

    def get_routing_trigger(self):
        """This surface's trigger — the arming condition under which routing fires.

        Default **unset** (``None``): absent a trigger, dispatch never fires and
        organic traffic is untouched. A consumer overrides this to return its arming
        condition (the query-param realization lands in C7; WNP wires it in C14).
        """
        return None

    def is_routing_canonical(self):
        """Whether this page may *host* rules — the consumer's notion of "canonical".

        Framework default is **fail-closed** (``False``, plan §0.4-A): a half-adopted
        consumer never routes and never shows the routing tab. Each consumer overrides
        this with a predicate over its own tree (WNP does so in C14).
        """
        return False

    def get_routing_signal_names(self):
        """The registry signals this consumer's authors may test (spec §2.2).

        Defaults to the whole registry; a consumer narrows it to the subset that makes
        sense for its audience (e.g. WNP's version-centric set in C14).
        """
        return tuple(registry.names())

    # -- Admin wiring: the framework-owned "User Routing" tab (spec §6.1) --

    # The condition-floor validation (plan P0-2) lives on the page form, not the rule
    # model, because modelcluster only attaches nested conditions at save time — see
    # RoutingPageForm. Consumers inherit this; one with its own base_form_class should
    # subclass RoutingPageForm to keep the floor.
    base_form_class = RoutingPageForm

    routing_panels = [
        InlinePanel("routing_rules", label=_("Rules")),
        InlinePanel("routing_config", label=_("Kill switch"), max_num=1),
    ]

    @classmethod
    def get_routing_tab(cls):
        """The "User Routing" tab: the rules panel and the single kill-switch panel."""
        return RoutingObjectList(cls.routing_panels, heading=_("User Routing"))

    @cached_classmethod
    def get_edit_handler(cls):
        """Extend Wagtail's default page tabs with the "User Routing" tab.

        Mirrors Wagtail's default ``TabbedInterface`` (Content / Promote / Settings)
        and appends the routing tab. A consumer that defines its own ``edit_handler``
        is left untouched (it can add the tab itself).
        """
        if hasattr(cls, "edit_handler"):
            return cls.edit_handler.bind_to_model(cls)

        tabs = []
        if cls.content_panels:
            tabs.append(ObjectList(cls.content_panels, heading=_("Content")))
        if cls.promote_panels:
            tabs.append(ObjectList(cls.promote_panels, heading=_("Promote")))
        if cls.settings_panels:
            tabs.append(ObjectList(cls.settings_panels, heading=_("Settings")))
        tabs.append(cls.get_routing_tab())

        edit_handler = TabbedInterface(tabs, base_form_class=cls.base_form_class)
        return edit_handler.bind_to_model(cls)

    # -- Serve-path dispatch (spec §2.3, plan §0.5, wired in C10) --

    def _routing_trigger_satisfied(self, request):
        """Whether this request arms routing for the surface (consumer trigger)."""
        trigger = self.get_routing_trigger()
        return bool(trigger is not None and trigger.is_satisfied(request))

    def _has_live_routing_rules(self):
        """Whether the page hosts at least one rule with a live target page."""
        return self.routing_rules.filter(target__live=True).exists()

    def serve(self, request, *args, **kwargs):
        """Thin adapter: map request/page state onto flags, then act on the decision.

        Routing *policy* lives in the pure ``decide_routing`` function; this method only
        reads the flags off the request and page and performs the chosen branch. The
        global ``user_routing`` waffle switch is the outermost gate — off ⇒ canonical
        exactly as today (the framework ships dark).
        """
        # Imported here (request time) to keep the resolver/preview + l10n import chain
        # out of model loading; dispatch only matters when a page is actually served.
        from springfield.cms.routing.preview import get_preview_response, is_preview_admin, is_preview_request
        from springfield.cms.routing.resolver import render_resolver

        decision = decide_routing(
            routing_enabled=waffle.switch_is_active(USER_ROUTING_SWITCH),
            has_loop_breaker=bool(request.GET.get(LOOP_BREAKER_PARAM)),
            is_preview_admin=is_preview_request(request) and is_preview_admin(request),
            is_paused=RoutingConfig.is_paused_for(self),
            trigger_satisfied=self._routing_trigger_satisfied(request),
            is_canonical=self.is_routing_canonical(),
            has_live_rules=self._has_live_routing_rules(),
        )

        if decision == SERVE_RESOLVER:
            return render_resolver(request, self)
        if decision == SERVE_PREVIEW:
            preview_response = get_preview_response(request, self)
            if preview_response is not None:
                return preview_response
        # SERVE_CANONICAL (and any preview that produced nothing) — serve as today.
        return super().serve(request, *args, **kwargs)
