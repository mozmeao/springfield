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

from contextlib import contextmanager

from django.db import models
from django.utils.translation import gettext_lazy as _

import waffle
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import HelpPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.utils.decorators import cached_classmethod

from springfield.cms.routing.dispatch import SERVE_PREVIEW, SERVE_RESOLVER, USER_ROUTING_SWITCH, decide_routing
from springfield.cms.routing.models import RoutingConfig, rule_panels
from springfield.cms.routing.params import LOOP_BREAKER_PARAM
from springfield.cms.routing.signals import registry

# Consumer-agnostic guidance shown at the top of the "User Routing" tab (ED-7). Kept
# generic (no per-consumer specifics) and localized; HTML is allowed in a HelpPanel.
ROUTING_TAB_HELP = _(
    "<p>Rules are checked <strong>top to bottom, first match wins</strong> — drag to reorder. "
    "A visitor is routed to the first rule whose conditions all match; if none match, they stay "
    "on this page.</p>"
    "<p>Each rule needs at least one condition, or “Match all triggered visitors” to route everyone. "
    "Use the <strong>kill switch</strong> below to pause routing without deleting any rules.</p>"
)


class RoutingPageForm(WagtailAdminPageForm):
    """Page form owning the admin-side routing validation.

    Two things live here rather than on the models, both because of *when* Wagtail runs
    things during a save:

    * **Condition-floor (plan P0-2).** A rule with no conditions matches every triggered
      visitor, so it must opt in via ``match_all``. ``RoutingRule.clean()`` can't enforce
      this — modelcluster attaches a rule's nested conditions to the instance only at
      *save* time, after validation, so a model-level count check sees zero conditions
      and rejects valid rules. The floor is checked here, where the nested ``conditions``
      formset is inspectable, and the error lands on the rule's ``match_all`` field.

    * **Hidden-tab formsets (ED-1).** The routing tab is hidden on non-canonical
      instances (``RoutingObjectList.is_shown``), so its ``routing_rules`` /
      ``routing_config`` formsets aren't rendered there — nor on the *add* form, where a
      new page isn't yet canonical. Their management forms are therefore absent from the
      POST, and validating/saving them would block the page entirely with ManagementForm
      errors. So they are excluded from validation/save on non-canonical instances.
      ``self.formsets`` is left intact outside that window so panel binding (which reads
      ``self.form.formsets[name]``) still works when the form re-renders.

    * **Kill-switch record (ED-1).** ``__init__`` auto-creates the ``RoutingConfig`` for
      canonical instances so the pause checkbox always renders (no "Add" step) — see
      ``__init__``; this replaces a panel ``min_num``, which can't be satisfied by an
      unchanged empty form.
    """

    # Formsets owned by the routing tab (hidden on non-canonical instances).
    ROUTING_FORMSETS = ("routing_rules", "routing_config")

    def __init__(self, *args, **kwargs):
        # Ensure a canonical page always has its kill-switch record, so the pause
        # checkbox renders on the routing tab with no "Add" step (ED-1). Created here —
        # before the formsets are built from the instance's relations — rather than via
        # a panel ``min_num``, which would block saving a page that has no record yet
        # (an unchanged empty form doesn't satisfy ``validate_min``). Idempotent and
        # scoped to saved canonical instances.
        instance = kwargs.get("instance")
        if instance is not None and getattr(instance, "pk", None):
            predicate = getattr(instance, "is_routing_canonical", None)
            if callable(predicate) and predicate():
                RoutingConfig.objects.get_or_create(page=instance)
        super().__init__(*args, **kwargs)

    def _is_routing_canonical(self):
        predicate = getattr(self.instance, "is_routing_canonical", None)
        return bool(callable(predicate) and predicate())

    @contextmanager
    def _routing_formsets_scoped(self):
        """Temporarily drop the routing formsets on non-canonical instances."""
        if self._is_routing_canonical():
            yield
            return
        original = self.formsets
        self.formsets = {name: formset for name, formset in original.items() if name not in self.ROUTING_FORMSETS}
        try:
            yield
        finally:
            self.formsets = original

    def is_valid(self):
        with self._routing_formsets_scoped():
            return super().is_valid()

    def save(self, commit=True):
        with self._routing_formsets_scoped():
            return super().save(commit=commit)

    def clean(self):
        cleaned_data = super().clean()
        # On non-canonical instances the routing formsets are scoped out (above), so this
        # is a no-op there; on canonical instances it enforces the condition-floor.
        rules_formset = self.formsets.get("routing_rules")
        if rules_formset is not None:
            # Force nested validation now: ClusterForm validates child formsets only
            # after this form's clean() runs, so the conditions aren't populated yet.
            rules_formset.is_valid()
            for rule_form in rules_formset.forms:
                self._enforce_condition_floor(rule_form)
                self._enforce_target_scope(rule_form)
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

    def _enforce_target_scope(self, rule_form):
        # Admin-side counterpart of RoutingRule.clean()'s target guards (plan P1-3a):
        # modelcluster leaves the rule's ``page`` unset at model-clean time during a save,
        # so those guards fire for the ORM path only. Enforce them here, where the page
        # instance and the chosen target are both known, so a bad target is caught inline
        # (the type-scoped chooser narrows the choices, this guarantees correctness).
        data = getattr(rule_form, "cleaned_data", None)
        if not data or data.get("DELETE"):
            return
        target = data.get("target")
        if target is None:
            return
        if target.pk == self.instance.pk:
            rule_form.add_error("target", _("A rule cannot target its own page."))
        elif not target.is_descendant_of(self.instance):
            rule_form.add_error("target", _("The target page must be a descendant of the page this rule is attached to."))


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

    # Page type(s) a rule's target chooser is scoped to (ED-9). ``None`` = any page; a
    # consumer sets this to its own type(s) — model class(es) or "app.Model" string(s) —
    # so authors aren't offered unrelated pages. Correctness is still enforced by the
    # descendant/self-target guards, so this is a usability narrowing, not the guard.
    routing_target_page_types = None

    @classmethod
    def get_routing_tab(cls):
        """The "User Routing" tab: guidance, the rules panel, and the kill-switch panel."""
        panels = [
            # Consumer-agnostic guidance on how matching works (ED-7).
            HelpPanel(content=ROUTING_TAB_HELP),
            # Rules, with the target chooser scoped to the consumer's page type(s) (ED-9).
            InlinePanel("routing_rules", panels=rule_panels(cls.routing_target_page_types), label=_("Rules")),
            # max_num=1 (0-or-1 kill switch per page). The pause checkbox always renders
            # with no "Add" step (ED-1) because RoutingPageForm auto-creates the record for
            # canonical pages — not via min_num, which would block saving a page with no
            # record yet.
            InlinePanel("routing_config", label=_("Routing kill switch"), max_num=1),
        ]
        return RoutingObjectList(panels, heading=_("User Routing"))

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
