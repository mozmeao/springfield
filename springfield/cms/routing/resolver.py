# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Server-side rendering of the client resolver page (spec §7).

When a triggered request reaches a live canonical with rules (wired in C10), the page
serves this lightweight resolver instead of final content. The resolver ships the data
the client needs — the page's rules and the metadata for the signals they test — as
``data-*`` attributes (CSP-clean, no inline script), plus the server-rendered country
attribute and localized status strings via Fluent. All rule evaluation happens on the
client (C5/C6); the server does no matching.

Resolver responses are CDN-cacheable (spec §7.6): this function sets no cache-busting
headers. The preview flows (C9) add ``no-store`` themselves.
"""

from lib import l10n_utils
from springfield.cms.routing.params import LOOP_BREAKER_PARAM
from springfield.cms.routing.signals import registry

RESOLVER_TEMPLATE = "cms/routing/resolver.html"
RESOLVER_FTL = "cms-routing-resolver"


def serialize_rules(page, request=None):
    """Serialize a page's live rules into the shape the client evaluator consumes.

    Rules are emitted in priority order (the model's position-then-id ordering). Rules
    whose target is not live are skipped — the client should never route to an
    unpublished page. Each condition carries the signal's value type from the registry
    so the evaluator can compare correctly.
    """
    serialized = []
    for rule in page.routing_rules.all():
        target = rule.target
        if not target or not target.live:
            continue
        conditions = []
        for condition in rule.conditions.all():
            signal = registry.get(condition.signal) if condition.signal in registry else None
            conditions.append(
                {
                    "signal": condition.signal,
                    "operator": condition.operator,
                    "expected": condition.expected_value,
                    "valueType": signal.value_type.value if signal else None,
                }
            )
        serialized.append({"target": target.get_url(request), "conditions": conditions})
    return serialized


def serialize_manifest(rules):
    """Signal metadata the client provider needs, for every signal the rules reference.

    Maps signal name -> {source, browserStateKey, valueType}. Serialized from the
    registry so the client reads each signal from the correct source with the correct
    per-key budget.
    """
    manifest = {}
    for rule in rules:
        for condition in rule["conditions"]:
            name = condition["signal"]
            if name in manifest or name not in registry:
                continue
            signal = registry.get(name)
            manifest[name] = {
                "source": signal.source.value,
                "browserStateKey": signal.browser_state_key,
                "valueType": signal.value_type.value,
            }
    return manifest


def render_resolver(request, page):
    """Render the resolver page for ``page`` and its live rules.

    A framework function against a page + its rules; not yet invoked by ``serve()``
    (that is wired in C10).
    """
    rules = serialize_rules(page, request)
    context = {
        "page": page,
        "routing_rules": rules,
        "routing_manifest": serialize_manifest(rules),
        "canonical_url": page.get_url(request),
        "loop_breaker_param": LOOP_BREAKER_PARAM,
    }
    return l10n_utils.render(request, RESOLVER_TEMPLATE, context, ftl_files=[RESOLVER_FTL])
