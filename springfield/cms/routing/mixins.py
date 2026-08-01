# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The routing adoption mixin.

``RoutingMixin`` is the whole adoption surface a consumer page type touches. It
declares exactly two overridable hooks — a **trigger** and an **eligibility predicate**
— and wires a "User Routing" edit tab holding the rules and kill-switch panels. The tab's
condition signals are narrowed from the trigger itself, so nothing extra is declared for
that. It adds **no database fields** (all state lives in
the routing tables keyed to ``wagtailcore.Page``), so adopting it produces **no
migration**. The serve-path dispatch is wired later; this mixin only owns the
declaration surface and the admin tab.
"""

from contextlib import contextmanager

from django.db import models
from django.utils.translation import gettext_lazy as _

import waffle
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import HelpPanel, InlinePanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.utils.decorators import cached_classmethod

from springfield.cms.routing.dispatch import SERVE_PREVIEW, SERVE_RESOLVER, USER_ROUTING_SWITCH, decide_routing
from springfield.cms.routing.models import RoutingConfig, rule_panels
from springfield.cms.routing.params import LOOP_BREAKER_PARAM
from springfield.cms.routing.signals import registry

# Consumer-agnostic guidance shown at the top of the "User Routing" tab. Kept
# generic (no per-consumer specifics) and localized; HTML is allowed in a HelpPanel.
ROUTING_TAB_HELP = _(
    "<p>Rules are checked <strong>top to bottom, first match wins</strong> — drag to reorder. "
    "A visitor is routed to the first rule whose conditions all match; if none match, they stay "
    "on this page.</p>"
    "<p>Each rule needs at least one condition, or “Match all triggered visitors” to route everyone. "
    "The <strong>kill switch</strong> in Options pauses routing without deleting any rules.</p>"
)


class RoutingPageForm(WagtailAdminPageForm):
    """Page form owning the admin-side routing validation.

    Two things live here rather than on the models, both because of *when* Wagtail runs
    things during a save:

    * **Condition-floor.** A rule with no conditions matches every triggered
      visitor, so it must opt in via ``match_all``. ``RoutingRule.clean()`` can't enforce
      this — modelcluster attaches a rule's nested conditions to the instance only at
      *save* time, after validation, so a model-level count check sees zero conditions
      and rejects valid rules. The floor is checked here, where the nested ``conditions``
      formset is inspectable, and the error lands on the rule's ``match_all`` field.

    * **Hidden-tab formsets.** The routing tab is hidden on non-canonical
      instances (``RoutingObjectList.is_shown``), so its ``routing_rules`` /
      ``routing_config`` formsets aren't rendered there — nor on the *add* form, where a
      new page isn't yet canonical. Their management forms are therefore absent from the
      POST, and validating/saving them would block the page entirely with ManagementForm
      errors. So they are excluded from validation/save on non-canonical instances.
      ``self.formsets`` is left intact outside that window so panel binding (which reads
      ``self.form.formsets[name]``) still works when the form re-renders.

    * **Kill-switch record.** ``__init__`` auto-creates the ``RoutingConfig`` for
      canonical instances so the pause checkbox always renders (no "Add" step) — see
      ``__init__``; this replaces a panel ``min_num``, which can't be satisfied by an
      unchanged empty form.
    """

    # Formsets owned by the routing tab (hidden on non-canonical instances).
    ROUTING_FORMSETS = ("routing_rules", "routing_config")

    def __init__(self, *args, **kwargs):
        # Ensure a canonical page always shows its kill-switch checkbox with no "Add" step.
        # Add an (unsaved) RoutingConfig to the instance's in-memory cluster BEFORE
        # the formsets are built, so the checkbox renders on the very first load and the
        # record is persisted only when the page is saved. Done here rather than via a
        # panel ``min_num`` (an unchanged empty form can't satisfy ``validate_min``) and via
        # the cluster rather than a DB write (which a same-request formset can miss).
        instance = kwargs.get("instance")
        if instance is not None and getattr(instance, "pk", None):
            predicate = getattr(instance, "is_routing_canonical", None)
            if callable(predicate) and predicate() and not instance.routing_config.all():
                instance.routing_config.add(RoutingConfig())
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
                self._enforce_signal_scope(rule_form)
        return cleaned_data

    def _enforce_signal_scope(self, rule_form):
        # A condition on the surface's own arming param can never be useful: the
        # resolver only runs once that param already holds its arming value, so the
        # condition is always true (or, for any other value, always false). The narrowed
        # dropdown keeps authors away from it; this makes it an actual rejection rather
        # than a hidden <option>, and also covers the ORM/API path into the admin.
        param = type(self.instance).get_routing_arming_param()
        if not param:
            return
        conditions_formset = rule_form.formsets.get("conditions")
        if conditions_formset is None:
            return
        for condition_form in conditions_formset.forms:
            data = getattr(condition_form, "cleaned_data", None)
            if not data or data.get("DELETE") or data.get("signal") != param:
                continue
            condition_form.add_error(
                "signal",
                _("“%(name)s” is what triggers routing on this page, so a condition on it always matches.") % {"name": param},
            )

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
        # Admin-side counterpart of RoutingRule.clean()'s target guards:
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

    The tab is shown only on canonical instances: a routing-enabled page
    *type* can have non-canonical instances (e.g. a variant nested under a canonical)
    whose rules would never fire at dispatch, so presenting a fully-functional-looking
    routing tab there would be dead config. Evaluated from the page's own eligibility
    predicate, which reads its tree position.
    """
    predicate = getattr(instance, "is_routing_canonical", None)
    return bool(instance is not None and callable(predicate) and predicate())


class RoutingObjectList(ObjectList):
    """An edit-tab that renders only on canonical instances."""

    class BoundPanel(ObjectList.BoundPanel):
        def is_shown(self):
            return routing_tab_is_shown(self.instance)


class RoutingMixin(models.Model):
    """Abstract mixin a Wagtail page type mixes in to adopt routing.

    A consumer declares exactly two things by overriding the hooks below and adds
    no view code, no framework code, and no schema. List this mixin **before** the
    page base class so its ``get_edit_handler`` wins in the MRO.
    """

    class Meta:
        abstract = True

    # -- Adoption surface: the only two things a consumer declares --

    def get_routing_trigger(self):
        """This surface's trigger — the arming condition under which routing fires.

        Default **unset** (``None``): absent a trigger, dispatch never fires and
        organic traffic is untouched. A consumer overrides this to return its arming
        condition.
        """
        return None

    def is_routing_canonical(self):
        """Whether this page may *host* rules — the consumer's notion of "canonical".

        Framework default is **fail-closed** (``False``): a half-adopted
        consumer never routes and never shows the routing tab. Each consumer overrides
        this with a predicate over its own tree.
        """
        return False

    @classmethod
    def get_routing_arming_param(cls):
        """The query param this surface arms on, if it is also a registry signal.

        Derived from the trigger rather than declared separately, so it can never drift
        from what actually arms the surface. Read from a bare instance because the panels
        are built per class: a trigger describes the *surface*, so it must not depend on
        one page's saved state. Returns ``None`` for a surface with no trigger, a
        non-param trigger, or a param that isn't a signal — in every case there is
        nothing to withhold.
        """
        # The mixin itself is abstract and so can't be instantiated; it also declares no
        # trigger, so there is nothing to derive until a concrete consumer adopts it.
        if cls._meta.abstract:
            return None
        trigger = cls().get_routing_trigger()
        param = getattr(trigger, "param_name", None)
        return param if param in registry else None

    # -- Admin wiring: the framework-owned "User Routing" tab --

    # The condition-floor validation lives on the page form, not the rule
    # model, because modelcluster only attaches nested conditions at save time — see
    # RoutingPageForm. Consumers inherit this; one with its own base_form_class should
    # subclass RoutingPageForm to keep the floor.
    base_form_class = RoutingPageForm

    # Page type(s) a rule's target chooser is scoped to. ``None`` = any page; a
    # consumer sets this to its own type(s) — model class(es) or "app.Model" string(s) —
    # so authors aren't offered unrelated pages. Correctness is still enforced by the
    # descendant/self-target guards, so this is a usability narrowing, not the guard.
    routing_target_page_types = None

    @classmethod
    def get_routing_tab(cls):
        """The "User Routing" tab: guidance, page-level options, then the rules."""
        panels = [
            # Consumer-agnostic guidance on how matching works.
            HelpPanel(content=ROUTING_TAB_HELP),
            # Page-level routing options, grouped so future per-page settings nest here.
            # For now it holds the kill switch (0-or-1 per page); its pause checkbox always
            # renders with no "Add" step because RoutingPageForm auto-adds the record
            # for canonical pages — not via min_num, which would block saving a page with no
            # record yet.
            MultiFieldPanel(
                [InlinePanel("routing_config", label=_("Kill switch"), max_num=1)],
                heading=_("Options"),
            ),
            # Rules, with the target chooser scoped to the consumer's page type(s) and
            # the condition signals narrowed by the consumer's own trigger.
            InlinePanel(
                "routing_rules",
                panels=rule_panels(cls.routing_target_page_types, cls.get_routing_arming_param()),
                label=_("Rules"),
            ),
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

    # -- Serve-path dispatch --

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
