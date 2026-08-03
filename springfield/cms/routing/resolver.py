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

from collections import namedtuple

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


UsableRule = namedtuple("UsableRule", ["rule", "target"])


def usable_rules(page):
    """The page's rules that could actually route a visitor, in priority order.

    The single definition of "this page has routing", shared by the serve-path gate and
    the serializer so the two can never disagree. When they did, a page either served a
    resolver with no rules in it — a holding page and an immediate bounce back to where
    the visitor already was — or refused to route on rules that would have worked.

    Every floor lives here rather than at either caller:

    * the target resolved into the page's own locale (see ``localized_target``), which
      drops a rule whose target has no version in this locale
    * that resolved target must be published — never route to an unpublished page
    * a rule with neither conditions nor ``match_all`` is dropped: it would match every
      triggered visitor. Authoring one is blocked, but the ORM/API path has no such
      floor, so this is the backstop.

    Returns ``(rule, target)`` pairs in the model's position-then-id order; empty means
    the page has nothing to route with. Evaluating each rule's conditions here caches
    them on the rule instance, so the serializer's formatting pass is free.
    """
    usable = []
    for rule in page.routing_rules.all():
        target = localized_target(rule.target, page)
        if not target or not target.live:
            continue
        if not rule.conditions.all() and not rule.match_all:
            continue
        usable.append(UsableRule(rule, target))
    return usable


def serialize_rules(page, request=None):
    """Format the page's usable rules into the shape the client evaluator consumes.

    Pure formatting over ``usable_rules`` — every decision about which rules survive
    belongs there. Each condition carries the signal's value type from the registry so
    the evaluator can compare correctly, and a rule's ``matchAll`` flag is emitted so the
    client can route the whole triggered audience for an intentional match-all rule.
    """
    serialized = []
    for rule, target in usable_rules(page):
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


def patch_request_for_resolver(request, page):
    """Apply the request setup a normal page serve does, for the resolver path.

    Rendering the resolver skips ``AbstractSpringfieldCMSPage.serve()``, and with it both
    the ``is_preview`` flag and the page's own list of available locales. Without that list
    the Fluent render falls back to the resolver strings' activation state and redirects any
    visitor whose locale is missing from it — a German visitor asking for the German
    canonical is sent to ``/en-US/``. Every other CMS page resolves locales from the page
    tree; the resolver must not be the one exception.

    Called from the branches that render the resolver, so canonical traffic pays nothing
    for the locale queries.
    """
    request.is_preview = False
    return page._patch_request_for_springfield(request)


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
