# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Server-side rendering of the client resolver page.

When a triggered request reaches a live canonical with rules, the page
serves this lightweight resolver instead of final content. The resolver ships the data
the client needs — the page's rules and the metadata for the signals they test — as
``data-*`` attributes (CSP-clean, no inline script), plus the server-rendered country
attribute and localized status strings via Fluent. All rule evaluation happens on the
client; the server does no matching.

Resolver responses are CDN-cacheable: this function sets no cache-busting
headers. The preview flows add ``no-store`` themselves.
"""

from lib import l10n_utils
from springfield.cms.routing.params import LOOP_BREAKER_PARAM
from springfield.cms.routing.signals import registry

RESOLVER_TEMPLATE = "cms/routing/resolver.html"
RESOLVER_FTL = "cms-routing-resolver"


def localized_target(target, page):
    """The version of ``target`` that belongs in ``page``'s locale, or ``None``.

    Translating a page copies its rules, but the copied ``target`` foreign key still
    points at the *source* locale's page — so without this a German canonical's rule
    would route German visitors to the English variant. Resolving against the hosting
    page's locale fixes rules that have already been copied as well as future ones.

    Returns ``None`` when the target has no counterpart in this locale, which drops the
    rule and leaves the visitor on the canonical — in their own language. Falling back to
    the stored target instead would route them to content they may not read, and would
    also produce a cross-tree target that the descendant guard rejects.
    """
    if target is None or target.locale_id == page.locale_id:
        return target
    return target.get_translation_or_none(page.locale)


def serialize_rules(page, request=None):
    """Serialize a page's live rules into the shape the client evaluator consumes.

    Rules are emitted in priority order (the model's position-then-id ordering). Rules
    whose target is not live are skipped — the client should never route to an
    unpublished page. Each condition carries the signal's value type from the registry
    so the evaluator can compare correctly. A rule's ``matchAll`` flag is emitted so the
    client can route the whole triggered audience for an intentional match-all rule.

    Targets are resolved into the page's own locale — see ``localized_target``.
    """
    serialized = []
    for rule in page.routing_rules.all():
        target = localized_target(rule.target, page)
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
        # Defensive floor (mirrors clean()'s): a rule with neither
        # conditions nor match_all would match every triggered visitor on the client.
        # Authoring one is blocked, but never emit one even if the DB somehow holds it.
        if not conditions and not rule.match_all:
            continue
        serialized.append({"target": target.get_url(request), "matchAll": rule.match_all, "conditions": conditions})
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


def render_resolver(request, page, fake_signals=None):
    """Render the resolver page for ``page`` and its live rules.

    A framework function against a page + its rules; not yet invoked by ``serve()``.
    ``fake_signals`` (a ``{name: value}`` map, used by the preview_signal flow) is
    serialized into a ``data-*`` blob so the client
    resolves those signals immediately while reading the rest live.
    """
    rules = serialize_rules(page, request)
    context = {
        "page": page,
        "routing_rules": rules,
        "routing_manifest": serialize_manifest(rules),
        "canonical_url": page.get_url(request),
        "loop_breaker_param": LOOP_BREAKER_PARAM,
        "routing_fake_signals": fake_signals or None,
    }
    return l10n_utils.render(request, RESOLVER_TEMPLATE, context, ftl_files=[RESOLVER_FTL])
