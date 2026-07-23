# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Generic User Routing dispatcher.

Page-type-agnostic: any consumer that has a canonical Wagtail page with
attached ``RoutingRule`` instances can call :func:`dispatch_for_canonical`
and get back one of:

* an :class:`~django.http.HttpResponseRedirect` — a rule matched on
  server-resolvable signals; the caller should return this directly.
* a :class:`~django.template.response.TemplateResponse` — the resolver
  page, to be rendered when unresolved rules need client-side signals.
* ``None`` — no routing decision was made; the caller should render the
  canonical page normally.

**Policy is the caller's job.** This function evaluates rules
unconditionally — it does not check for Balrog-flow markers or any other
gating condition. Callers that want "only route in this circumstance"
semantics (e.g. WNP's "post-update flow only" policy) enforce that in
their wrapper before invoking this function. Other page types (landing
pages, downloads) may want routing on every request; that stays their
call.

WNP is the first consumer (see ``springfield.firefox.views.wnp_dispatch``).
"""

import json
import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse

from .signals import registry as default_registry

logger = logging.getLogger(__name__)

RESOLVER_TEMPLATE = "cms/routing/resolver.html"

# Analytics query params attached to redirect target URLs so downstream
# analytics (GA4, MarTech pipelines) can attribute matched-variant landings
# back to the rule and canonical page that routed them.
#
# Named descriptively (not cryptic) so they read cleanly in dashboards.
# Emitted on the URL the user's browser is sent to; the landing page reads
# them on load and fires whatever analytics event MarTech has configured.
ROUTED_FROM_PARAM = "routed_from"  # slug of the canonical page that routed
ROUTED_RULE_PARAM = "routed_rule"  # name of the rule that matched
ROUTED_MODE_PARAM = "routed_mode"  # "server", "client", or "none"
ROUTED_MODE_SERVER = "server"
ROUTED_MODE_CLIENT = "client"
# "none" tags the client-side fallback URL when the resolver evaluated
# rules and none matched. Same URL as canonical + the WNP trigger param,
# so the WNP wrapper needs an explicit check for ``routed_mode`` presence
# to break the resolver → canonical → resolver loop.
ROUTED_MODE_NONE = "none"

# Reserved query-param names the framework emits itself. Any pre-existing
# incoming values for these params are stripped before we append our own —
# otherwise a spoofed ``?routed_from=fake`` on the inbound request would
# shadow our attribution (most JS analytics readers take the first match).
_RESERVED_ROUTING_PARAMS = frozenset(
    {
        ROUTED_FROM_PARAM,
        ROUTED_RULE_PARAM,
        ROUTED_MODE_PARAM,
    }
)

# Admin-only preview URL params. Marketing authors paste preview URLs from
# the Wagtail admin to verify rules before publishing them Live.
#
# * ``preview_rule={id}`` — force-select a specific rule (bypasses the
#   evaluator entirely); redirect to that rule's target. Answers "does the
#   target page render correctly?"
# * ``preview_signal={name}:{value}`` (repeatable) — feed fake signal values
#   to the evaluator alongside (or overriding) real resolved signals.
#   Answers "would this rule actually match given these signals?"
#
# Both require Wagtail admin authentication (``request.user.is_staff``);
# unauthenticated requests silently ignore them. Preview responses set
# ``Cache-Control: no-store`` so authors see fresh evaluations, not stale
# cached responses.
PREVIEW_RULE_PARAM = "preview_rule"
PREVIEW_SIGNAL_PARAM = "preview_signal"


def _json_for_script(value) -> str:
    """Serialize ``value`` to JSON and escape sequences that would break out
    of a ``<script>`` tag when embedded via a template.

    Django and Jinja HTML-autoescape do NOT protect the raw-text content of a
    ``<script>`` element (browsers don't decode entities inside it), so
    admin-editable strings containing ``</script>`` would terminate the tag
    early and inject subsequent HTML. The HTML parser also transitions to
    "script data escaped" state on ``<!--``, which changes when a subsequent
    ``</script>`` closes the tag — so those sequences need to be broken up
    too, even inside ``<script type="application/json">``.

    Escapes are chosen so the OUTPUT REMAINS VALID JSON:

    * ``</`` → ``<\\/`` (``\\/`` is a legal JSON string escape per RFC 8259)
    * ``<!--`` → ``\\u003c!--`` (unicode-escape the ``<``)
    * ``-->`` → ``--\\u003e`` (unicode-escape the ``>``)

    In each case the JSON parser reconstructs the original string content, but
    the raw byte stream no longer contains the HTML-triggering sequence.
    """
    dumped = json.dumps(value)
    return dumped.replace("</", "<\\/").replace("<!--", "\\u003c!--").replace("-->", "--\\u003e")


def dispatch_for_canonical(
    request,
    canonical,
    *,
    registry=default_registry,
):
    """Return a routing response for ``canonical`` when the caller wants routing.

    **Client-side architecture.** The server does NO rule evaluation. If the
    canonical has any live rules attached, dispatch renders the resolver page
    which ships the full rule set + signal-metadata to the client. The client
    resolver reads signals from the DOM (server-rendered, e.g. country),
    from ``Mozilla.Client`` (UA-derived), and from UITour (browser state),
    then evaluates and navigates.

    Args:
        request: The incoming HTTP request.
        canonical: The canonical Wagtail page hosting the rules.
        registry: The signal registry, used to look up per-signal UITour
            keys for the resolver page's signal-metadata blob. Overridable
            for tests.

    Returns:
        ``HttpResponseRedirect`` when admin ``?preview_rule=`` short-circuits
        directly to a specific rule's target; ``TemplateResponse`` for the
        resolver page when routing is active; ``None`` when the caller
        should serve the canonical page (no rules, paused, etc.).
    """
    # Local import — the RoutingRule model lives in the CMS app; importing
    # it at module scope would create an import cycle since routing/ is
    # loaded via cms.models.__init__.
    from springfield.cms.models.routing import RULE_STATUS_LIVE

    # Track whether ANY preview URL param was supplied so responses are
    # never served from cache when an author is previewing.
    preview_signals = _parse_preview_signals(request)
    is_preview_request = _is_preview_authorized(request) and (bool(preview_signals) or request.GET.get(PREVIEW_RULE_PARAM))

    # ---- Admin preview: preview_rule server-side short-circuit --------------
    # ``?preview_rule={id}`` (admin-authenticated) forces a redirect to the
    # specified rule's target — bypasses the client-side evaluator entirely
    # so the admin can verify a variant page renders correctly without
    # needing signals to actually match on the current request. Preview
    # intentionally bypasses ``routing_paused`` so authors can verify while
    # production routing is halted.
    preview_rule = _get_preview_rule(request, canonical)
    if preview_rule is not None:
        response = _redirect_to_variant(request, canonical, preview_rule)
        _set_no_store(response)
        return response

    # ---- Emergency kill switch ---------------------------------------------
    # Marketing-editable field on the canonical page. When on, dispatch
    # short-circuits and canonical serves regardless of rule state.
    if getattr(canonical, "routing_paused", False) and not is_preview_request:
        return None

    # ``prefetch_related("conditions")`` avoids N+1: the resolver page render
    # iterates live_rules and calls rule.conditions_as_dicts() on each, which
    # otherwise fires a separate SELECT per rule on the hot Balrog path.
    live_rules = list(canonical.routing_rules.filter(status=RULE_STATUS_LIVE).select_related("target_page").prefetch_related("conditions"))
    if not live_rules:
        return None

    # ---- Client-side evaluation: hand off the full rule set ----------------
    # The client evaluator handles all signal types (DOM-read, UA-derived,
    # UITour). ``preview_signal`` overrides also flow through — the resolver
    # template embeds them alongside rules so the client can apply them
    # before evaluating.
    response = _render_resolver_page(
        request,
        canonical,
        live_rules,
        registry=registry,
        preview_signal_overrides=preview_signals if is_preview_request else None,
    )
    if is_preview_request:
        _set_no_store(response)
    return response


def _canonical_url_for(canonical, request) -> str:
    """Resolve the canonical page's URL for use in the ``Link: rel="canonical"``
    header. Prefers the absolute URL (scheme + host + path) because that's
    what SEO/AEO crawlers most reliably interpret for canonical link hints;
    falls back to the relative URL if Wagtail's Site config can't produce
    an absolute one, and finally to ``"/"``.
    """
    try:
        full_url = canonical.get_full_url(request=request)
    except Exception:
        # Wagtail can raise if Sites aren't configured or the page isn't
        # routable. Fall back to the relative URL rather than 500-ing.
        full_url = None
    if full_url:
        return full_url
    return canonical.get_url(request=request) or "/"


def _set_canonical_link_header(response, canonical_url: str) -> None:
    """Add a ``Link: <url>; rel="canonical"`` header to a router response.

    Router URLs return content (canonical fallback, resolver page) or redirects
    at the SAME path a user would organically visit — declaring the canonical
    URL tells search engines and AEO crawlers where the true content lives,
    so SEO signals consolidate on the canonical URL rather than fragmenting
    across router-marked variants.
    """
    response["Link"] = f'<{canonical_url}>; rel="canonical"'


def _is_preview_authorized(request) -> bool:
    """Preview URLs are for admin authors, not general public traffic.
    Gate on Wagtail admin's ``is_staff`` — anyone with a valid admin session
    is trusted to preview."""
    user = getattr(request, "user", None)
    return bool(user and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False))


def _get_preview_rule(request, canonical):
    """Look up the ``?preview_rule={id}`` rule for admin-authenticated requests.

    Only rules attached to the requested ``canonical`` are eligible — a
    rule ID from a different canonical would silently not-match. Returns the
    rule instance or ``None``.
    """
    if not _is_preview_authorized(request):
        return None
    raw_id = request.GET.get(PREVIEW_RULE_PARAM)
    if not raw_id:
        return None
    try:
        rule_id = int(raw_id)
    except (TypeError, ValueError):
        return None
    return canonical.routing_rules.filter(pk=rule_id).select_related("target_page").first()


def _parse_preview_signals(request) -> dict[str, Any]:
    """Parse repeated ``?preview_signal=name:value`` params into a
    ``{signal_name: value}`` dict.

    Values coerce best-effort:
    * ``true`` / ``false`` (case-insensitive) → bool
    * an integer string → int
    * otherwise → string as-is

    Silently returns ``{}`` for unauthenticated requests, so the same URL is
    inert (no preview effect) when shared or crawled.
    """
    if not _is_preview_authorized(request):
        return {}
    signals: dict[str, Any] = {}
    for raw in request.GET.getlist(PREVIEW_SIGNAL_PARAM):
        if not raw or ":" not in raw:
            continue
        name, _sep, value = raw.partition(":")
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        signals[name] = _coerce_preview_value(value)
    return signals


def _coerce_preview_value(text: str) -> Any:
    """Coerce a preview-signal string value to a Python type the evaluator
    understands.

    Strict bool vocabulary (``true``/``false``/``yes``/``no``, case-
    insensitive) coerces to Python bool. Numeric strings coerce to ``int``
    so preview URLs for INT signals like ``firefox_version:151`` behave
    correctly. Anything else stays a string.

    Design choice: ``"1"`` and ``"0"`` are treated as ints, NOT bools.
    Admin bool inputs use ``true``/``false``; a marketing author typing
    ``preview_signal=firefox_version:1`` reasonably expects the int 1, not
    True. Rules stored via the admin form persist bools via the
    ``true``/``false`` tokens, so preview URL semantics match.
    """
    lower = text.lower()
    if lower in ("true", "yes"):
        return True
    if lower in ("false", "no"):
        return False
    try:
        return int(text)
    except (TypeError, ValueError):
        return text


def _set_no_store(response) -> None:
    """Mark a response as uncacheable — used for preview responses so
    authors see fresh evaluations regardless of upstream cache state."""
    if response is not None:
        response["Cache-Control"] = "no-store"


def _strip_reserved_routing_params(querystring: str) -> str:
    """Remove any pre-existing ``routed_from`` / ``routed_rule`` / ``routed_mode``
    entries from an incoming querystring.

    The framework emits these itself on every redirect target. If a caller
    (or a hostile URL) already carries values for them, they would shadow
    the framework-emitted values in analytics — most ``URLSearchParams.get``
    implementations return the first match. Stripping incoming values first
    keeps attribution honest.
    """
    if not querystring:
        return ""
    filtered = [(k, v) for k, v in parse_qsl(querystring, keep_blank_values=True) if k not in _RESERVED_ROUTING_PARAMS]
    return urlencode(filtered)


def _redirect_to_variant(request, canonical, matched_rule):
    """Build a 302 redirect to the matched rule's target, preserving the
    incoming querystring and attaching analytics attribution params."""
    target_url = matched_rule.target_page.get_url(request=request)
    if not target_url:
        # Matched rule but the target page can't produce a URL (e.g. the
        # target is off any Wagtail Site's root, or unpublished). Falling
        # through to canonical is the safe behavior — but log it so
        # marketing can see WHY their variant didn't take effect.
        logger.warning(
            "user_routing: matched rule %r has target_page %r with no resolvable URL; falling back to canonical.",
            getattr(matched_rule, "name", "?"),
            getattr(matched_rule.target_page, "pk", None),
        )
        return None
    querystring = _strip_reserved_routing_params(request.META.get("QUERY_STRING", ""))
    if querystring:
        target_url = _append_qs(target_url, querystring)
    # Attach analytics attribution params. Additive to any existing query;
    # the landing page reads these to fire the routing event.
    target_url = _append_qs(
        target_url,
        urlencode(
            {
                ROUTED_FROM_PARAM: getattr(canonical, "slug", "") or "",
                ROUTED_RULE_PARAM: getattr(matched_rule, "name", "") or "",
                ROUTED_MODE_PARAM: ROUTED_MODE_SERVER,
            }
        ),
    )
    response = HttpResponseRedirect(target_url)
    _set_canonical_link_header(response, _canonical_url_for(canonical, request))
    return response


def _append_qs(url: str, querystring: str) -> str:
    """Attach a querystring to a URL, preserving any existing query and
    fragment components correctly.

    Uses :func:`urllib.parse.urlsplit` rather than naive string concat so
    ``/foo#hash`` + ``a=b`` correctly becomes ``/foo?a=b#hash`` (per RFC
    3986 the query precedes the fragment) rather than ``/foo#hash?a=b``
    (which browsers treat as fragment-with-embedded-question-mark and
    lose the query for). Also handles URLs that already carry a query.
    """
    if not querystring:
        return url
    parts = urlsplit(url)
    merged_query = f"{parts.query}&{querystring}" if parts.query else querystring
    return urlunsplit((parts.scheme, parts.netloc, parts.path, merged_query, parts.fragment))


def _render_resolver_page(request, canonical, live_rules, *, registry, preview_signal_overrides=None):
    """Serialize the full live rule set and render the resolver page.

    The template embeds four JSON blobs consumed by the client-side resolver:

    * ``rules_json`` — every live rule with a pre-resolved ``target_url``.
      Client evaluates them all using signals sourced from the DOM (geo),
      ``Mozilla.Client`` (UA-derived), and UITour (browser state).
    * ``signal_metadata_json`` — for each signal referenced by any rule:
      the UITour key (if UITour-resolved). Client uses this to decide
      whether to fire a UITour call and which config key to fetch.
    * ``canonical_url_json`` — the canonical URL (with querystring) for the
      client's fallback navigation when no rule matches.
    * ``preview_signals_json`` — admin preview_signal overrides for the
      client to apply on top of its own signal resolution. Empty in
      production traffic.

    Each rule's ``target_url`` includes analytics attribution params
    (``routed_from``, ``routed_rule``, ``routed_mode=client``) so the
    landing event fires with rule + canonical attribution.
    """
    canonical_url = canonical.get_url(request=request) or "/"
    querystring = _strip_reserved_routing_params(request.META.get("QUERY_STRING", ""))
    canonical_url_with_qs = _append_qs(canonical_url, querystring)

    canonical_slug = getattr(canonical, "slug", "") or ""

    # Client falls back to this URL when no rule matches. The URL still
    # carries whatever gated the router (e.g. WNP's ``utm_source=update``),
    # so appending ``routed_mode=none`` gives the WNP wrapper a marker to
    # short-circuit and skip re-entering the router — otherwise the
    # browser navigates back to the resolver page for another round in an
    # infinite loop. Also tags the canonical landing with an analytics
    # attribution so no-match traffic can be distinguished from organic.
    canonical_fallback_url = _append_qs(
        canonical_url_with_qs,
        urlencode(
            {
                ROUTED_FROM_PARAM: canonical_slug,
                ROUTED_MODE_PARAM: ROUTED_MODE_NONE,
            }
        ),
    )

    serialized_rules = []
    required_signal_names: set[str] = set()

    for rule in live_rules:
        target_url = rule.target_page.get_url(request=request)
        if not target_url:
            # Target page has no resolvable URL (unpublished, off-site,
            # or off any Wagtail Site root). Falling back to canonical_url
            # would create a JS-navigation loop: the resolver-page URL and
            # the canonical URL share the same path, so navigating there
            # from the resolver would re-enter dispatch, re-render the
            # resolver, and repeat. Drop the rule from the client payload
            # entirely and log the misconfiguration so marketing can see
            # WHY their rule isn't taking effect.
            logger.warning(
                "user_routing: rule %r has target_page %r with no resolvable URL; dropping from resolver page.",
                getattr(rule, "name", "?"),
                getattr(rule.target_page, "pk", None),
            )
            continue

        # AND-conditions: a rule has 1+ conditions. Collect all their signals.
        rule_conditions = rule.conditions_as_dicts()
        for condition in rule_conditions:
            signal_name = condition.get("signal")
            if signal_name:
                required_signal_names.add(signal_name)

        # Preserve the incoming querystring on variant URLs too — the user's
        # utm_source, oldversion, etc. shouldn't be dropped by the resolver.
        target_url = _append_qs(target_url, querystring)
        # Analytics attribution — client-side is now the only mode.
        target_url = _append_qs(
            target_url,
            urlencode(
                {
                    ROUTED_FROM_PARAM: canonical_slug,
                    ROUTED_RULE_PARAM: rule.name or "",
                    ROUTED_MODE_PARAM: ROUTED_MODE_CLIENT,
                }
            ),
        )

        serialized_rules.append(
            {
                "name": rule.name,
                # ``priority`` is the JSON-contract name the client-side
                # resolver uses to sort rules. Server-side field is
                # ``sort_order`` (Wagtail Orderable convention) — the JSON
                # payload keeps "priority" so marketing / analytics
                # consumers see the term they know.
                "priority": rule.sort_order if rule.sort_order is not None else 0,
                "conditions": rule_conditions,
                "target_url": target_url,
            }
        )

    # Signal metadata tells the client which UITour key each UITour-resolved
    # signal maps to. Signals resolved via DOM / UA / Mozilla.Client don't
    # need per-request metadata — the client has a static map for those.
    signal_metadata: dict[str, dict[str, str]] = {}
    # sorted() so the emitted JSON blob is byte-stable request-to-request —
    # a set's iteration order depends on PYTHONHASHSEED, which would defeat
    # any downstream ETag caching or byte-identical snapshot testing.
    for signal_name in sorted(required_signal_names):
        signal = registry.get(signal_name)
        if signal is None or not signal.uitour_key:
            continue
        signal_metadata[signal_name] = {"uitour_key": signal.uitour_key}

    response = TemplateResponse(
        request,
        RESOLVER_TEMPLATE,
        {
            # canonical_url is emitted as JSON (not raw text) so Jinja
            # autoescape can't corrupt ampersands into &amp;amp; inside the
            # <script> block — the client parses the JSON to get a clean URL.
            # Uses the fallback variant (with ``routed_mode=none`` appended)
            # so a no-match navigation carries a loop-breaker for the WNP
            # wrapper.
            "canonical_url_json": _json_for_script(canonical_fallback_url),
            # Same fallback URL, un-JSON-wrapped, for the <noscript>
            # meta-refresh fallback in the template. JS-disabled visitors
            # also need the loop-breaker.
            "canonical_url_raw": canonical_fallback_url,
            "rules_json": _json_for_script(serialized_rules),
            "signal_metadata_json": _json_for_script(signal_metadata),
            # Preview overrides (admin-only). Empty dict in production traffic.
            "preview_signals_json": _json_for_script(preview_signal_overrides or {}),
        },
    )
    _set_canonical_link_header(response, canonical_url)
    return response
