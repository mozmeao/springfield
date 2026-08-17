# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Server-side rendering of the client resolver page.

A triggered request to a live canonical with rules gets this lightweight page instead of
final content. It ships the rules and their signals' metadata as ``data-*`` attributes
(CSP-clean, no inline script), plus the server-rendered country and localized strings.
**All matching happens on the client** — the server never evaluates a rule.

Responses are CDN-cacheable and state their own lifetime via
``ROUTING_RESOLVER_CACHE_SECONDS``: how long frozen target URLs, pause state and country
may be stale, since nothing purges this page. Preview flows send ``no-store`` instead.
"""

from collections import namedtuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from lib import l10n_utils
from springfield.cms.routing.models import localized_target
from springfield.cms.routing.params import LOOP_BREAKER_PARAM, RESERVED_ROUTING_PARAMS
from springfield.cms.routing.signals import registry

RESOLVER_TEMPLATE = "cms/routing/resolver.html"
RESOLVER_FTL = "cms-routing-resolver"


def url_in_requested_locale(page, request):
    """The page's URL carrying the locale prefix the visitor actually asked for.

    For an alias locale (es-AR served from es-MX, pt-PT from pt-BR, en-GB from en-US) the
    content comes from the fallback locale while the URL keeps the requested one. Raw
    ``get_url`` returns the *page's* prefix, which would move the visitor out of the locale
    they asked for on the one navigation this page exists to perform.

    Rule targets are stored as base ``Page``, so the specific instance is what carries the
    helper. A target whose type isn't a springfield CMS page falls back to ``get_url``: the
    ORM/API path can attach any page, and an un-rewritten prefix beats a 500 for a
    triggered visitor.
    """
    specific = page.specific
    active_locale_url = getattr(specific, "get_active_locale_url", None)
    return active_locale_url(request) if active_locale_url else specific.get_url(request)


def fallback_url(page, request):
    """Where a visitor goes when the client never redirects them.

    The canonical URL, keeping the visitor's own query string so their attribution survives —
    minus the framework's control params, plus the loop-breaker. The loop-breaker is not
    optional: this URL still carries whatever armed routing in the first place, so without it
    the destination would serve the resolver again.

    Mirrors what ``preserveQueryString`` plus ``appendLoopBreaker`` do on the client, for the
    two paths the client never reaches — the ``<noscript>`` refresh and the escape link.

    **Depends on the CDN keying on the full URL, query string included.** That is what makes it
    safe to render per-request data into a cacheable body: the response can only ever be served
    to a request whose query string is the one rendered into it. If that ever stops being true,
    this has to go back to a bare canonical URL.
    """
    url = url_in_requested_locale(page, request)
    parts = urlsplit(url)
    kept = parse_qsl(parts.query, keep_blank_values=True)
    seen = {name for name, _value in kept}
    if request is not None:
        for name, value in parse_qsl(request.META.get("QUERY_STRING", ""), keep_blank_values=True):
            if name in RESERVED_ROUTING_PARAMS or name in seen:
                continue
            kept.append((name, value))
    kept.append((LOOP_BREAKER_PARAM, "1"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


UsableRule = namedtuple("UsableRule", ["rule", "target"])


def usable_rules(page):
    """The page's rules that could actually route a visitor, in priority order.

    The single definition of "this page has routing", shared by the serve-path gate and
    the serializer so the two cannot disagree — when they did, a page either served an
    empty resolver (a holding page, then a bounce straight back) or refused to route on
    rules that would have worked.

    Every floor lives here rather than at either caller. A rule is dropped when:

    * its target has no version in this page's locale (see ``localized_target``)
    * that resolved target is unpublished
    * the target is not a strict descendant of the hosting page — copying a page copies
      its rules, whose targets still point into the source subtree, and a self-target
      would re-render the resolver with no loop-breaker to stop the cycle
    * it has neither conditions nor ``match_all``, which would match every triggered
      visitor. Authoring one is blocked; this is the backstop for the ORM/API path.

    Returns ``(rule, target)`` pairs in position-then-id order.
    """
    # Memoized for the life of this page *instance* — one request, where the gate asks and
    # then the serializer asks again. It makes the two share a single answer rather than two
    # that merely ought to agree. A caller that mutates rules and re-asks the same instance
    # would see the stale list, so re-fetch the page instead (which is what a request does).
    cached = getattr(page, "_usable_rules_cache", None)
    if cached is not None:
        return cached

    usable = []
    # Reuse an already-prefetched relation if the caller set one up (e.g. the admin listing,
    # which prefetches target/conditions once for many pages up front) — chaining
    # select_related/prefetch_related onto the manager below always issues a fresh query,
    # bypassing that cache, so check for it first. Otherwise pull targets in the same query
    # and conditions in one more, so the loop below adds no query per rule.
    prefetched = getattr(page, "_prefetched_objects_cache", {}).get("routing_rules")
    rules = prefetched if prefetched is not None else page.routing_rules.select_related("target").prefetch_related("conditions")
    for rule in rules:
        target = localized_target(rule.target, page)
        if not target or not target.live:
            continue
        # Strict descendant, so a rule targeting its own page is dropped here too — a page
        # is not its own descendant.
        if not target.is_descendant_of(page):
            continue
        if not rule.conditions.all() and not rule.match_all:
            continue
        usable.append(UsableRule(rule, target))

    page._usable_rules_cache = usable
    return usable


RuleProblem = namedtuple("RuleProblem", ["message", "pending"])


def rule_problems(page):
    """Why each of ``page``'s rules cannot route a visitor: ``{rule pk: RuleProblem}``.

    Rules that *can* route are absent from the map. Which rules are unusable is decided by
    ``usable_rules`` — the same answer the serve path acts on — so an authoring surface can
    report what visitors get without forming its own opinion. The checks below only choose
    the wording.

    ``pending`` separates the two states that clear themselves through work already under
    way — the target is translated or published later — from the ones that stay broken until
    somebody changes the rule. Without that distinction the whole report is noise: an
    ordinary staged translation would light up exactly like a page-copy mistake, and authors
    would learn to ignore both.
    """
    usable_ids = {usable.rule.pk for usable in usable_rules(page)}
    problems = {}
    for rule in page.routing_rules.all():
        if rule.pk in usable_ids:
            continue
        problems[rule.pk] = _rule_problem(rule, page)
    return problems


def _rule_problem(rule, page):
    if rule.target is None:
        return RuleProblem(_("No target page"), pending=False)
    target = localized_target(rule.target, page)
    if target is None:
        return RuleProblem(_("Target not translated into this language yet"), pending=True)
    if not target.live:
        return RuleProblem(_("Target not published yet"), pending=True)
    if not target.is_descendant_of(page):
        return RuleProblem(_("Target is not part of this page"), pending=False)
    return RuleProblem(_("No conditions, and not set to match all"), pending=False)


def serialize_rules(page, request=None):
    """Format the page's usable rules into the shape the client evaluator consumes.

    Pure formatting over ``usable_rules`` — every decision about which rules survive
    belongs there. Each condition carries the signal's value type from the registry so
    the evaluator can compare correctly, and a rule's ``matchAll`` flag is emitted so the
    client can route the whole triggered audience for an intentional match-all rule.

    A match-all rule is emitted **without** its conditions. The client matches such a rule
    outright, so any conditions stored against it are inert; shipping them anyway would
    make the payload contradict itself, and invite a later reader to "fix" the client into
    honouring conditions the author was told were ignored. The editor says so too — see
    ``match_all``'s help text and the conditions panel's.
    """
    serialized = []
    for rule, target in usable_rules(page):
        conditions = []
        for condition in [] if rule.match_all else rule.conditions.all():
            signal = registry.get(condition.signal) if condition.signal in registry else None
            conditions.append(
                {
                    "signal": condition.signal,
                    "operator": condition.operator,
                    "expected": condition.expected_value,
                    "valueType": signal.value_type.value if signal else None,
                }
            )
        serialized.append({"target": url_in_requested_locale(target, request), "matchAll": rule.match_all, "conditions": conditions})
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

    Called by ``render_resolver`` itself, deliberately: a caller that has to remember this
    reintroduces that redirect the moment one forgets, and the failure is invisible — the
    page renders, the suite stays green, and only non-English visitors are affected. Since
    nothing renders the resolver without going through ``render_resolver``, the locale
    queries land on the resolver path only, never on canonical traffic.
    """
    request.is_preview = False
    return page._patch_request_for_springfield(request)


def render_resolver(request, page, fake_signals=None):
    """Render the resolver page for ``page`` and its live rules.

    ``fake_signals`` (a ``{name: value}`` map, used by the preview_signal flow) is
    serialized into a ``data-*`` blob so the client
    resolves those signals immediately while reading the rest live.

    States its own cache lifetime rather than inheriting the site-wide default, because this
    page freezes state into a cacheable body that nothing purges — see
    ``ROUTING_RESOLVER_CACHE_SECONDS``. The preview flows overwrite this with ``no-store``.
    """
    request = patch_request_for_resolver(request, page)
    rules = serialize_rules(page, request)
    context = {
        "page": page,
        "routing_rules": rules,
        "routing_manifest": serialize_manifest(rules),
        "canonical_url": url_in_requested_locale(page, request),
        # Where a stranded visitor goes: canonical, attribution intact, loop-breaker attached.
        "fallback_url": fallback_url(page, request),
        "loop_breaker_param": LOOP_BREAKER_PARAM,
        "routing_fake_signals": fake_signals or None,
    }
    response = l10n_utils.render(request, RESOLVER_TEMPLATE, context, ftl_files=[RESOLVER_FTL])
    if response.status_code == 200:
        # Setting this here also stops the site-wide cache middleware stamping its own value:
        # it defers to any response that already carries Cache-Control.
        response["Cache-Control"] = f"max-age={settings.ROUTING_RESOLVER_CACHE_SECONDS}"
    return response
