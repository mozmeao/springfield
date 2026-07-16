# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
RoutingRule model.

A rule answers one question: *"if a request looks like X, send them to variant
page Y instead of the canonical page."* Rules attach to a canonical page (via
``parent_page``) and target a variant page (via ``target_page``).

Conditions are stored as three structured fields (``signal_name``,
``operator``, ``expected_values``) and exposed as a synthesized
``condition`` dict for the rule engine and client-side resolver, which
both consume the shape ``{"signal": ..., "op": ..., "values": [...]}``.
Marketing never sees or types JSON — the admin form renders a signal
dropdown (grouped by server/browser), an operator dropdown (is / is not),
and a text area for one-or-more values.

See ``.research/wnp-dynamic-rendering-plan.md``.
"""

from django.core.exceptions import ValidationError
from django.db import models

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, PageChooserPanel

from springfield.cms.routing import ResolverType, SignalValueType, registry

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

RULE_STATUS_DRAFT = "draft"
RULE_STATUS_LIVE = "live"
RULE_STATUS_ARCHIVED = "archived"

RULE_STATUS_CHOICES = [
    (RULE_STATUS_DRAFT, "Draft"),
    (RULE_STATUS_LIVE, "Live"),
    (RULE_STATUS_ARCHIVED, "Archived"),
]

# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------
# Two operators only, both operating on a list of expected values:
#   is     — resolved signal value is IN the list
#   is_not — resolved signal value is NOT in the list
#
# Single-value equality is expressed as ``is`` with a length-1 list.
# Range / comparison operators (>=, <=) come with Level 2 (visual condition
# builder). See ``.research/wnp-dynamic-rendering-plan.md``.

RULE_OPERATOR_IS = "is"
RULE_OPERATOR_IS_NOT = "is_not"

RULE_OPERATOR_CHOICES = [
    (RULE_OPERATOR_IS, "is"),
    (RULE_OPERATOR_IS_NOT, "is not"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _signal_choices():
    """Callable choices for ``signal_name``, grouped by resolver type.

    Returns an optgroup-style structure that Django renders as visually
    separated sections in the dropdown:

        ── Server signals ──
           country
           lapsed_user
           …
        ── Browser signals ──
           default_browser
           ai_controls
           …

    Evaluated lazily (Django 5.0+ supports callable ``choices``) so the
    registry is guaranteed populated at admin-render time.
    """
    server, browser = [], []
    for signal in sorted(registry.all(), key=lambda s: s.name):
        entry = (signal.name, signal.name)
        if signal.resolver_type == ResolverType.SERVER_SIDE:
            server.append(entry)
        else:
            browser.append(entry)
    groups = []
    if server:
        groups.append(("Server signals", tuple(server)))
    if browser:
        groups.append(("Browser signals", tuple(browser)))
    return groups


def _parse_expected_value(value_str, value_type):
    """Coerce a single admin-input token into the signal's value type.

    Returns ``None`` if the input can't be parsed — that means the
    condition can never match, which ``clean()`` surfaces as a validation
    error before the rule can go Live.
    """
    if value_str is None:
        return None
    text = str(value_str).strip()
    if text == "":
        return None

    if value_type == SignalValueType.BOOL:
        lower = text.lower()
        if lower in ("true", "yes", "1"):
            return True
        if lower in ("false", "no", "0"):
            return False
        return None

    if value_type == SignalValueType.INT:
        try:
            return int(text)
        except (ValueError, TypeError):
            return None

    # STRING (including enum_values-constrained strings).
    return text


def _tokenize_values(raw):
    """Split marketing's free-text value input into individual tokens.

    Accepts newlines and commas as separators. Empty entries are dropped
    and each token is trimmed. Returns a list of raw strings — parsing to
    the signal's value type happens later, per-token.
    """
    if raw is None:
        return []
    tokens = []
    for line in str(raw).splitlines():
        for part in line.split(","):
            stripped = part.strip()
            if stripped:
                tokens.append(stripped)
    return tokens


def _stringify_value(value):
    """Format a Python value back to the string shape marketing entered."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class RoutingRule(models.Model):
    """Routes traffic from a canonical page to a variant when the condition matches."""

    # NOTE on parent_page: ParentalKey to a concrete Page subclass is what
    # Wagtail's InlinePanel machinery wants. Today WhatsNewPage2026 is the
    # only consumer of User Routing. When a second page type opts in, we
    # revisit — either broaden to Page (if Wagtail's cluster machinery
    # cooperates) or split RoutingRule per-parent-type. See
    # ``.research/wnp-dynamic-rendering-plan.md`` § Reusability.
    parent_page = ParentalKey(
        "cms.WhatsNewPage2026",
        on_delete=models.CASCADE,
        related_name="routing_rules",
        help_text="The canonical page this rule attaches to.",
    )

    target_page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.PROTECT,
        related_name="routing_rules_as_target",
        help_text="The variant page to route matching users to.",
    )

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name shown in the admin (e.g. 'Lapsed users → welcomeback').",
    )
    priority = models.IntegerField(
        default=100,
        help_text="Lower numbers evaluate first. Ties broken by rule ID.",
    )

    # --- Condition (three structured fields, synthesized into `condition`) ---

    signal_name = models.CharField(
        max_length=64,
        blank=True,
        choices=_signal_choices,
        help_text="Which browser or server signal this rule checks.",
    )
    operator = models.CharField(
        max_length=16,
        choices=RULE_OPERATOR_CHOICES,
        default=RULE_OPERATOR_IS,
        help_text="`is` matches when the signal is one of the values below; `is not` matches when it isn't.",
    )
    expected_values = models.TextField(
        blank=True,
        default="",
        help_text=(
            "One or more values, one per line (commas also accepted). "
            "For enum-valued signals, values must match the exact allowed set "
            "(check the signal's help entry). Booleans: 'true' or 'false'. "
            "Integers: a number."
        ),
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
        FieldPanel("signal_name"),
        FieldPanel("operator"),
        FieldPanel("expected_values"),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["parent_page", "priority", "id"]
        indexes = [
            models.Index(fields=["parent_page", "status", "priority"]),
        ]
        verbose_name = "User Routing rule"
        verbose_name_plural = "User Routing rules"

    def __str__(self):
        target = self.target_page.title if self.target_page_id else "(no target)"
        return f"{self.name} → {target}"

    # ------------------------------------------------------------------
    # Condition — synthesized from structured fields for the rule engine.
    # ------------------------------------------------------------------

    @property
    def condition(self):
        """The rule's condition as ``{"signal": ..., "op": ..., "values": [...]}``.

        Returns ``{}`` when the rule has no signal set — the "draft with
        nothing chosen yet" state, which the rule engine treats as
        unresolvable (safe: canonical serves).
        """
        if not self.signal_name:
            return {}
        signal = registry.get(self.signal_name)
        value_type = signal.value_type if signal else SignalValueType.STRING
        tokens = _tokenize_values(self.expected_values)
        parsed = []
        for token in tokens:
            parsed_value = _parse_expected_value(token, value_type)
            if parsed_value is not None:
                parsed.append(parsed_value)
        return {
            "signal": self.signal_name,
            "op": self.operator or RULE_OPERATOR_IS,
            "values": parsed,
        }

    @condition.setter
    def condition(self, value):
        """Accept both the legacy ``{signal, equals}`` shape and the new
        ``{signal, op, values}`` shape, decomposing either into the
        structured fields.

        Legacy support preserves the fluent ``RoutingRule(condition={...})``
        construction pattern the earlier tests were written against.
        """
        if not isinstance(value, dict):
            self.signal_name = ""
            self.operator = RULE_OPERATOR_IS
            self.expected_values = ""
            return

        self.signal_name = value.get("signal") or ""

        if "equals" in value:
            # Legacy shape → single-value `is`.
            self.operator = RULE_OPERATOR_IS
            equals_value = value["equals"]
            if equals_value is None:
                self.expected_values = ""
            else:
                self.expected_values = _stringify_value(equals_value)
            return

        # New shape.
        self.operator = value.get("op") or RULE_OPERATOR_IS
        values = value.get("values") or []
        self.expected_values = "\n".join(_stringify_value(v) for v in values)

    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        if self.parent_page_id and self.target_page_id and self.parent_page_id == self.target_page_id:
            raise ValidationError({"target_page": "A rule cannot target the same page it attaches to."})

        # Target page must be a descendant of the canonical (parent) page.
        # This matches the WNP convention (variants are children of the
        # canonical) and prevents accidental cross-linking to unrelated
        # pages. Only enforced when both sides are set — parent may be
        # unset during initial admin creation before Wagtail persists.
        if self.parent_page_id and self.target_page_id and self.parent_page_id != self.target_page_id:
            # treebeard's ``is_descendant_of`` is exclusive (excludes self);
            # we already handled the equal-page case above.
            if not self.target_page.is_descendant_of(self.parent_page):
                raise ValidationError(
                    {
                        "target_page": (
                            "Target page must be a descendant of the canonical page. "
                            "Move the variant under this page in the tree, or pick a different variant."
                        )
                    }
                )

        # Signal name and value validation kicks in only when a signal is
        # chosen — leaving the fields blank is a valid "draft not filled in
        # yet" state.
        if not self.signal_name:
            return

        signal = registry.get(self.signal_name)
        if signal is None:
            raise ValidationError({"signal_name": f"Unknown signal: {self.signal_name!r}."})

        tokens = _tokenize_values(self.expected_values)
        if not tokens:
            return  # empty draft state

        parsed_values = []
        for token in tokens:
            parsed = _parse_expected_value(token, signal.value_type)
            if parsed is None:
                type_label = signal.value_type.value
                raise ValidationError({"expected_values": f"Value {token!r} could not be parsed as {type_label}."})
            if signal.enum_values and parsed not in signal.enum_values:
                allowed = ", ".join(repr(v) for v in signal.enum_values)
                raise ValidationError({"expected_values": f"Value {parsed!r} must be one of: {allowed}."})
            parsed_values.append(parsed)
