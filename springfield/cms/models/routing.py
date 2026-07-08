# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
RoutingRule model.

A rule answers one question: *"if a request looks like X, send them to variant
page Y instead of the canonical page."* Rules attach to a canonical page (via
``parent_page``) and target a variant page (via ``target_page``). The condition
is a structured JSON object referencing signals from
:mod:`springfield.cms.routing.signals`.

Not yet wired to any consumer view — Step 2 of Phase 1. See
``.research/wnp-dynamic-rendering-plan.md``.
"""

from django.core.exceptions import ValidationError
from django.db import models

from wagtail.admin.panels import FieldPanel, HelpPanel, PageChooserPanel
from wagtail.models import Page

from springfield.cms.routing import registry

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

RULE_STATUS_DRAFT = "draft"
RULE_STATUS_LIVE = "live"
RULE_STATUS_RETIRED = "retired"

RULE_STATUS_CHOICES = [
    (RULE_STATUS_DRAFT, "Draft"),
    (RULE_STATUS_LIVE, "Live"),
    (RULE_STATUS_RETIRED, "Retired"),
]


# ---------------------------------------------------------------------------
# Condition schema
# ---------------------------------------------------------------------------
#
# Kept intentionally minimal for Step 2. Composite matchers (all_of / any_of /
# not) come in a later step. Current shape:
#
#     {"signal": "<name>", "equals": <value>}
#
# The client-side rule evaluator and server-side matcher both understand this
# same shape.

CONDITION_ALLOWED_KEYS = {"signal", "equals"}


def _validate_condition(condition, *, registry_=registry):
    if not isinstance(condition, dict):
        raise ValidationError({"condition": "Condition must be a JSON object."})

    unknown_keys = set(condition) - CONDITION_ALLOWED_KEYS
    if unknown_keys:
        raise ValidationError({"condition": f"Unknown keys in condition: {sorted(unknown_keys)}"})

    signal_name = condition.get("signal")
    if not signal_name:
        raise ValidationError({"condition": 'Condition must include a "signal" key.'})

    if "equals" not in condition:
        raise ValidationError({"condition": 'Condition must include an "equals" key (may be null).'})

    signal = registry_.get(signal_name)
    if signal is None:
        raise ValidationError({"condition": f"Unknown signal: {signal_name!r}. Not registered in the signal registry."})


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class RoutingRule(models.Model):
    """Routes traffic from a canonical page to a variant when the condition matches."""

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name shown in the admin (e.g. 'Lapsed users → welcomeback').",
    )
    priority = models.IntegerField(
        default=100,
        help_text="Lower numbers evaluate first. Ties broken by rule ID.",
    )

    parent_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="routing_rules_as_parent",
        help_text="The canonical page this rule attaches to.",
    )
    target_page = models.ForeignKey(
        Page,
        on_delete=models.PROTECT,
        related_name="routing_rules_as_target",
        help_text="The variant page to route matching users to.",
    )

    condition = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured rule condition, e.g. {"signal": "lapsed_user", "equals": true}.',
    )

    status = models.CharField(
        max_length=16,
        choices=RULE_STATUS_CHOICES,
        default=RULE_STATUS_DRAFT,
        help_text="Only 'Live' rules are evaluated by the resolver.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("priority"),
        PageChooserPanel("parent_page"),
        PageChooserPanel("target_page"),
        HelpPanel(
            content=(
                "<p>Structured condition JSON. For now, use the shape "
                "<code>{&quot;signal&quot;: &quot;&lt;name&gt;&quot;, &quot;equals&quot;: &lt;value&gt;}</code>. "
                "The signal name must match one registered in "
                "<code>springfield.cms.routing</code>.</p>"
            ),
        ),
        FieldPanel("condition"),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["parent_page", "priority", "id"]
        indexes = [
            models.Index(fields=["parent_page", "status", "priority"]),
        ]
        verbose_name = "Routing Rule"
        verbose_name_plural = "Routing Rules"

    def __str__(self):
        target = self.target_page.title if self.target_page_id else "(no target)"
        return f"{self.name} → {target}"

    def clean(self):
        super().clean()
        if self.condition:
            _validate_condition(self.condition)

        if self.parent_page_id and self.target_page_id and self.parent_page_id == self.target_page_id:
            raise ValidationError({"target_page": "A rule cannot target the same page it attaches to."})
