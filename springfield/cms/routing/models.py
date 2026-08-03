# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Framework-owned, Page-keyed routing schema.

Three models, all keyed to ``wagtailcore.Page`` so a single generic table set is
shared by every consumer page type — there is no per-consumer model, and adopting
the framework adds no migration:

* ``RoutingRule`` — an ordered rule hosted by a canonical page, resolving to a
  target page that must be a descendant of that canonical.
* ``RoutingCondition`` — one ``<signal> <operator> <expected-value>`` clause; a
  rule's conditions form an ordered conjunction (AND).
* ``RoutingConfig`` — a per-page 0-or-1 record carrying the ``routing_paused`` kill
  switch, with headroom for future per-page routing settings.

Save-time validation lives in ``clean()`` — server-side, not just admin
JS: the operator must be legal for the signal's value type, an enum expected value
must be a member of the enum set, and a rule's target must be a descendant of its
canonical.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.admin.widgets import AdminPageChooser
from wagtail.models import Orderable

from springfield.cms.routing.signals import OPERATORS, SOURCE_LABELS, Source, ValueType, registry
from springfield.cms.routing.value_lists import known_value_lists

# Operators that carry a comma-separated list of expected values (set membership).
_SET_MEMBERSHIP_OPERATORS = ("in", "not_in")


def signal_choices():
    """Signal choices for admin selects, grouped into optgroups by source.

    Returns Django's grouped-choices shape — ``[(source_label, [(name, name), …]), …]``
    — ordered by the ``Source`` enum, so the signal dropdown is organized by where each
    signal is read from (CDN geo / User-Agent / UITour / URL) instead of one flat list.

    A callable so choices stay in lockstep with the registry and adding a signal never
    generates a migration (Django serializes the reference, not the result).
    """
    grouped = {}
    for signal in registry:
        grouped.setdefault(signal.source, []).append((signal.name, signal.name))
    return [(SOURCE_LABELS[source], grouped[source]) for source in Source if source in grouped]


class ExcludingSelect(forms.Select):
    """A ``Select`` that always withholds one option value.

    Filtering on *assignment* rather than once at construction is deliberate:
    ``ChoiceField`` pushes its own choices onto its widget whenever they are set, so
    choices passed to the constructor are overwritten before the field ever renders.
    Optgroups left empty are dropped rather than rendered as bare headings.
    """

    def __init__(self, *args, excluded=None, **kwargs):
        self.excluded = excluded
        super().__init__(*args, **kwargs)

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        narrowed = []
        for choice_value, label in value:
            if isinstance(label, (list, tuple)):
                kept = [option for option in label if option[0] != self.excluded]
                if kept:
                    narrowed.append((choice_value, kept))
            elif choice_value != self.excluded:
                narrowed.append((choice_value, label))
        self._choices = narrowed


def condition_panels(arming_param=None):
    """The per-condition panels, optionally withholding the surface's arming param.

    A surface that arms on a query param only ever reaches the resolver with that param
    at its arming value, so a condition testing it is always true (or, for any other
    value, always false) and quietly does nothing. Withholding it from the dropdown keeps
    authors out of that trap; ``RoutingPageForm`` enforces it on save, since a narrowed
    widget is presentation only.
    """
    if not arming_param:
        return None
    return [
        FieldPanel("signal", widget=ExcludingSelect(excluded=arming_param)),
        FieldPanel("operator"),
        FieldPanel("expected_value"),
    ]


def rule_panels(target_page_types=None, arming_param=None):
    """The per-rule inline panels, optionally restricting the target chooser.

    Framework-generic: a consumer narrows the target chooser to its own page type(s) by
    setting ``RoutingMixin.routing_target_page_types``; the descendant/self-target guards
    (model ``clean()`` + ``RoutingPageForm``) remain the correctness backstop. The
    condition panels are narrowed from the consumer's own trigger — see
    ``condition_panels``.
    """
    if target_page_types:
        target_panel = FieldPanel("target", widget=AdminPageChooser(target_models=target_page_types))
    else:
        target_panel = FieldPanel("target")
    return [
        FieldPanel("name"),
        FieldPanel("match_all"),
        target_panel,
        InlinePanel(
            "conditions",
            panels=condition_panels(arming_param),
            heading=_("Conditions (all must match — AND)"),
            label=_("Condition"),
            help_text=_("Ignored while “Match all triggered visitors” is ticked above."),
        ),
    ]


def operator_choices():
    """All operator choices; per-signal legality is enforced in ``clean()``."""
    return [(operator.value, operator.label) for operator in OPERATORS.values()]


class RoutingRule(ClusterableModel, Orderable):
    """An ordered routing rule hosted by a canonical page.

    ``ParentalKey`` to ``wagtailcore.Page`` means any consumer page type can host
    rules without its own model or migration. Priority is the ``sort_order``
    position; ties break by ascending id (older rule wins) so ordering is
    deterministic across database engines. There is no draft/status field — a rule
    exists iff its parent page is published.
    """

    page = ParentalKey("wagtailcore.Page", on_delete=models.CASCADE, related_name="routing_rules")
    target = models.ForeignKey(
        "wagtailcore.Page",
        # PROTECT (not CASCADE): deleting a targeted page must be blocked, never
        # silently take its rule with it.
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("Target page"),
        help_text=_("The page to route matching users to. Must be a descendant of this page."),
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Rule name"),
        help_text=_("Optional label for this rule, shown in listings. Falls back to a summary of its conditions."),
    )
    match_all = models.BooleanField(
        default=False,
        verbose_name=_("Match all triggered visitors"),
        help_text=_(
            "Route every triggered visitor to the target. Any conditions on this rule are "
            "ignored while this is ticked. Matches before any rule below it."
        ),
    )

    class Meta(Orderable.Meta):
        ordering = ["sort_order", "pk"]
        verbose_name = _("Routing rule")
        verbose_name_plural = _("Routing rules")

    # Fields shown for each rule inside the "User Routing" tab. Conditions are
    # authored as a nested inline conjunction. The framework rebuilds these
    # per-consumer to scope the target chooser; this is the unrestricted default.
    panels = rule_panels()

    def __str__(self):
        if self.name:
            return self.name
        if self.match_all:
            summary = _("all triggered visitors")
        else:
            summary = ", ".join(str(condition) for condition in self.conditions.all()) or _("no conditions")
        return f"{summary} → target {self.target_id}"

    def clean(self):
        super().clean()
        errors = {}

        # The condition-floor (block an accidental empty match-everyone rule)
        # is enforced on the page form (RoutingPageForm), not here: modelcluster attaches
        # a rule's nested conditions only at save time, so a count check in this model
        # clean() can't see them during a Wagtail save and would reject valid rules.

        # Rules only fire on a canonical page; one attached to a variant is dead
        # config. Reuse the consumer's own canonical predicate via the
        # specific instance; page types without the hook are unaffected (defensive
        # getattr).
        if self.page_id:
            is_routing_canonical = getattr(self.page.specific, "is_routing_canonical", None)
            if callable(is_routing_canonical) and not is_routing_canonical():
                errors["page"] = _("Attach rules to the canonical page, not a variant.")

        # Target must be a strict descendant of the canonical the rule attaches to, judged on
        # the version of the target that would actually be served from this page — the same
        # resolution the serve path performs. Translating a page copies its rules with the
        # source locale's target still stored, so checking the raw target here would reject
        # every translated page's own rules: an error on a target the author never chose,
        # blocking a save they made for unrelated reasons.
        #
        # A target with no counterpart in this locale is left alone. The rule simply does not
        # fire on this page, which is the fail-safe outcome, and it starts working by itself
        # once the target is translated.
        #
        # Imported at call time to keep the resolver's l10n import chain out of model loading.
        from springfield.cms.routing.resolver import localized_target

        if self.page_id and self.target_id:
            target = localized_target(self.target, self.page)
            # Self-targeting gets its own message rather than the generic descendant one.
            if target is not None and target.pk == self.page_id:
                errors["target"] = _("A rule cannot target its own page.")
            elif target is not None and not target.is_descendant_of(self.page):
                errors["target"] = _("The target page must be a descendant of the page this rule is attached to.")

        if errors:
            raise ValidationError(errors)


class RoutingCondition(Orderable):
    """One condition in a rule's conjunction.

    Tests one signal with one operator against an expected value. Negation is the
    operator's paired form ("is not", "not in", negated comparisons) — there is no
    rule-level NOT or OR.
    """

    rule = ParentalKey(RoutingRule, on_delete=models.CASCADE, related_name="conditions")
    signal = models.CharField(max_length=100, choices=signal_choices, verbose_name=_("Signal"))
    operator = models.CharField(max_length=20, choices=operator_choices, verbose_name=_("Operator"))
    expected_value = models.TextField(
        verbose_name=_("Expected value"),
        # TextField (not a capped CharField) so long in/not_in lists get a roomy,
        # multi-line textarea — the FieldPanel renders one automatically. No static
        # help_text: the dynamic per-signal help (condition-help.es6.js) is the primary
        # guidance and a static line here would compete with it.
        help_text="",
    )

    class Meta(Orderable.Meta):
        verbose_name = _("Condition")
        verbose_name_plural = _("Conditions")

    # Fields shown for each condition inside a rule's inline form.
    panels = [
        FieldPanel("signal"),
        FieldPanel("operator"),
        FieldPanel("expected_value"),
    ]

    def __str__(self):
        return f"{self.signal} {self.operator} {self.expected_value}"

    def expected_values(self):
        """The expected value(s) as a list.

        Set-membership operators accept a list entered one-per-line and/or comma-separated,
        so split on both newlines and commas (strip, drop empties). Single-value operators
        read the trimmed whole string.
        """
        if self.operator in _SET_MEMBERSHIP_OPERATORS:
            return [value.strip() for value in self.expected_value.replace("\n", ",").split(",") if value.strip()]
        value = self.expected_value.strip()
        return [value] if value else []

    def clean(self):
        super().clean()
        # The signal must be one the registry knows.
        if self.signal not in registry:
            raise ValidationError({"signal": _("Unknown signal “%(name)s”.") % {"name": self.signal}})
        signal = registry.get(self.signal)

        # The operator must be legal for the signal's value type.
        if not signal.allows_operator(self.operator):
            raise ValidationError(
                {"operator": _("Operator “%(operator)s” is not valid for the “%(name)s” signal.") % {"operator": self.operator, "name": self.signal}}
            )

        # An enum condition's expected value(s) must be members of the enum set.
        if signal.value_type is ValueType.ENUM:
            members = {enum_value.value for enum_value in signal.enum_values}
        else:
            # A STRING signal whose domain is fully known (locale / country) is an enum in
            # all but declaration — see value_lists. Its set is complete, so an off-list
            # value can never match at runtime and would leave the rule silently dead.
            members = set(known_value_lists().get(self.signal, ()))

        if members:
            invalid = [value for value in self.expected_values() if value not in members]
            if invalid:
                raise ValidationError(
                    {
                        "expected_value": _("“%(value)s” is not a valid value for the “%(name)s” signal.")
                        % {"value": ", ".join(invalid), "name": self.signal}
                    }
                )


class RoutingConfig(models.Model):
    """Per-page routing settings — a 0-or-1 record keyed to the page.

    Holds the ``routing_paused`` kill switch and leaves headroom for future per-page
    routing settings. Keeping the kill switch here (not on the routing mixin) is what
    keeps the mixin field-free and the whole PR at a single migration.
    The 0-or-1 cardinality is enforced by the admin panel's ``max_num=1``; a
    missing record reads as *not paused*.
    """

    page = ParentalKey("wagtailcore.Page", on_delete=models.CASCADE, related_name="routing_config")
    routing_paused = models.BooleanField(
        default=False,
        verbose_name=_("Pause routing"),
        help_text=_("When enabled, routing is bypassed and canonical content is served directly. Previews still work."),
    )

    class Meta:
        verbose_name = _("Routing configuration")
        verbose_name_plural = _("Routing configurations")

    def __str__(self):
        return f"RoutingConfig for page {self.page_id} (paused={self.routing_paused})"

    @classmethod
    def is_paused_for(cls, page):
        """Whether routing is paused for ``page``. A missing record reads as not paused."""
        config = cls.objects.filter(page=page).first()
        return bool(config and config.routing_paused)
