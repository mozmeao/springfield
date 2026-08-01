# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin-facing helpers for the routing framework.

``build_signal_payload`` serializes the registry into the payload the condition-help
admin JS consumes. It is the *only* source of truth for the dynamic help
text, so the help can never drift from what the evaluator actually reads. Every human
string is pre-localized server-side from a ``gettext_lazy`` source (the registry's own
labels or the value-type hints below) — no raw English literals.
"""

from django.utils.translation import gettext_lazy as _

from springfield.cms.routing.signals import SOURCE_LABELS, Source, ValueType, registry
from springfield.cms.routing.value_lists import known_value_lists

# "What to type" hint shown beneath the expected-value field. Value-focused only — the
# operator dropdown already lists the legal operators, so hints never restate them.
VALUE_TYPE_HINTS = {
    ValueType.ENUM: _("Enter one of these values:"),
    ValueType.STRING: _("Free text."),
    ValueType.BOOLEAN: _("Enter “true” or “false”."),
    ValueType.VERSION: _("Enter a version, e.g. 129 or 130.0.1."),
    ValueType.INTEGER: _("Enter a whole number."),
}

# Appended to the help only when a set-membership operator (in / not in) is selected.
COMMA_HINT = _("Separate multiple values with commas.")

# Prepended to the help when a value fails client-side validation, so the flagged field
# reads as an error and not just a red outline.
INVALID_HINT = _("That value isn’t valid.")

# Lead-in for STRING signals that carry a known value list (locale / country).
VALUE_LIST_HINT = _("Enter one of these values:")

# Short, editor-facing "what to type" hint shown in the reference page's Values column for
# signals that have no fixed set (enum values / locale / country are shown as the values
# themselves instead). Localized.
VALUE_TYPE_EXAMPLES = {
    ValueType.STRING: _("Free text"),
    ValueType.BOOLEAN: _("true or false"),
    ValueType.VERSION: _("e.g. 129 or 130.0.1"),
    ValueType.INTEGER: _("e.g. 30"),
}


def build_signal_payload():
    """Serialize the registry for the admin JS: signal name -> help metadata.

    Strings are resolved to the active admin locale here (server-side), so the JS only
    concatenates already-localized text.
    """
    value_lists = known_value_lists()
    comma_hint = str(COMMA_HINT)
    invalid_hint = str(INVALID_HINT)
    payload = {}
    for signal in registry:
        entry = {
            "valueType": signal.value_type.value,
            # Short signal description leads the help so editors know what it means.
            "description": str(signal.description),
            "hint": str(VALUE_TYPE_HINTS[signal.value_type]),
            "commaHint": comma_hint,
            "invalidHint": invalid_hint,
            "operators": [{"value": operator.value, "label": str(operator.label)} for operator in signal.operators],
            "enumValues": [],
            "values": [],
        }
        if signal.value_type is ValueType.ENUM:
            entry["enumValues"] = [{"value": enum_value.value, "label": str(enum_value.label)} for enum_value in signal.enum_values]
        if signal.name in value_lists:
            # A known value set surfaced as the primary help line, with a
            # values-oriented lead-in instead of the generic STRING "available operators".
            entry["values"] = value_lists[signal.name]
            entry["hint"] = str(VALUE_LIST_HINT)
        payload[signal.name] = entry
    return payload


def build_signal_reference():
    """Rows for the auto-generated Signals reference page.

    Generated straight from the registry — one row per registered signal — so the
    reference can never drift from the values the evaluator actually reads. Strings are
    left lazy so the template localizes them; the honest descriptions come
    through unchanged.
    """
    value_lists = known_value_lists()
    rows = []
    for signal in registry:
        rows.append(
            {
                "name": signal.name,
                "description": signal.description,
                "source": SOURCE_LABELS[signal.source],
                # Stable source enum value for the per-source badge CSS class + the UITour
                # note; the human label stays localized in ``source`` above.
                "source_key": signal.source.value,
                "is_uitour": signal.source is Source.UITOUR,
                "value_type": signal.value_type.value,
                "operators": [operator.label for operator in signal.operators],
                "enum_values": [{"value": enum_value.value, "label": enum_value.label} for enum_value in signal.enum_values],
                # Request-time value list for known-set STRING signals (locale / country),
                # shown collapsed on the reference page; empty for free-text signals.
                "values": value_lists.get(signal.name, []),
                # "What to type" hint for signals with no fixed set (true/false, version
                # examples, whole number, free text); enums/known-sets show their values.
                "value_example": VALUE_TYPE_EXAMPLES.get(signal.value_type),
                "browser_state_key": signal.browser_state_key,
            }
        )
    return rows
