# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Rule matching on the server, for organic pages.

The server matches a signal only when the CDN cache key includes it, so a cached response
can only reach visitors it was decided for. Anything else is matched in the browser.
"""

from springfield.base.geo import get_country_from_request

# What the server can match, with its reader. The admin dropdown and save guard use this too.
SERVER_SIGNALS = {"country": get_country_from_request}

_POSITIVE_OPERATORS = ("is", "in")
_NEGATED_OPERATORS = ("is_not", "not_in")


def condition_matches(condition, value):
    """Whether one condition holds for ``value``. An unknown value (``None``) never matches."""
    if value is None:
        return False
    if condition.operator in _POSITIVE_OPERATORS:
        return value in condition.expected_values()
    if condition.operator in _NEGATED_OPERATORS:
        return value not in condition.expected_values()
    return False


def matched_target(page, request):
    """The target of the first rule whose conditions all match on the server, else ``None``.

    Match-all rules and rules on a signal the server can't read are skipped. Saving either is
    blocked on organic pages; this covers the ORM/API path.
    """
    # Imported at call time to keep the resolver's l10n import chain out of model loading.
    from springfield.cms.routing.resolver import usable_rules

    values = {}

    def read(signal):
        if signal not in values:
            values[signal] = SERVER_SIGNALS[signal](request)
        return values[signal]

    for rule, target in usable_rules(page):
        conditions = rule.conditions.all()
        if rule.match_all or any(condition.signal not in SERVER_SIGNALS for condition in conditions):
            continue
        if all(condition_matches(condition, read(condition.signal)) for condition in conditions):
            return target
    return None
