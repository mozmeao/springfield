# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin-facing helpers for the routing framework.

``build_signal_payload`` serializes the registry into the payload the condition-help
admin JS consumes (spec §6.2). It is the *only* source of truth for the dynamic help
text, so the help can never drift from what the evaluator actually reads. Every human
string is pre-localized server-side from a ``gettext_lazy`` source (the registry's own
labels or the value-type hints below) — no raw English literals (spec §9.2).
"""

from django.utils.translation import gettext_lazy as _

from springfield.cms.routing.signals import SOURCE_LABELS, ValueType, registry

# Per-value-type hint shown beneath the expected-value field. All localizable.
VALUE_TYPE_HINTS = {
    ValueType.ENUM: _("Enter one of these values:"),
    ValueType.STRING: _("Free text. Available operators:"),
    ValueType.BOOLEAN: _("Enter “true” or “false”."),
    ValueType.VERSION: _("Compared as a version (e.g. 129 or 129.0.1). Available operators:"),
    ValueType.INTEGER: _("Compared as a whole number. Available operators:"),
}


def build_signal_payload():
    """Serialize the registry for the admin JS: signal name -> help metadata.

    Strings are resolved to the active admin locale here (server-side), so the JS only
    concatenates already-localized text.
    """
    payload = {}
    for signal in registry:
        entry = {
            "valueType": signal.value_type.value,
            "hint": str(VALUE_TYPE_HINTS[signal.value_type]),
            "operators": [{"value": operator.value, "label": str(operator.label)} for operator in signal.operators],
            "enumValues": [],
        }
        if signal.value_type is ValueType.ENUM:
            entry["enumValues"] = [{"value": enum_value.value, "label": str(enum_value.label)} for enum_value in signal.enum_values]
        payload[signal.name] = entry
    return payload


def build_signal_reference():
    """Rows for the auto-generated Signals reference page (spec §4.5).

    Generated straight from the registry — one row per registered signal — so the
    reference can never drift from the values the evaluator actually reads. Strings are
    left lazy so the template localizes them; the honest descriptions (spec §4.4) come
    through unchanged.
    """
    rows = []
    for signal in registry:
        rows.append(
            {
                "name": signal.name,
                "description": signal.description,
                "source": SOURCE_LABELS[signal.source],
                "value_type": signal.value_type.value,
                "operators": [operator.label for operator in signal.operators],
                "enum_values": [{"value": enum_value.value, "label": enum_value.label} for enum_value in signal.enum_values],
                "browser_state_key": signal.browser_state_key,
            }
        )
    return rows
