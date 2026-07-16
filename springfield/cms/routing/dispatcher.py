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

from .evaluator import evaluate_rules, rule_needs_client_side
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
ROUTED_MODE_PARAM = "routed_mode"  # "server" or "client"
ROUTED_MODE_SERVER = "server"
ROUTED_MODE_CLIENT = "client"

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
    signal_context: dict[str, Any] | None = None,
    registry=default_registry,
):
    """Evaluate live routing rules for ``canonical`` and return a response.

    Args:
        request: The incoming HTTP request.
        canonical: The canonical Wagtail page hosting the rules.
        signal_context: Optional per-page-type context passed through to
            signal resolvers. WNP populates ``{"target_version": "156"}``
            so ``lapsed_user`` can derive the version delta; landing pages
            might populate campaign-slug context; downloads might pass
            nothing. Kept as an opaque dict so new consumers don't grow
            the dispatcher's kwarg surface.
        registry: The signal registry to resolve against. Defaults to the
            module-level singleton; overridable for tests.

    Returns:
        ``HttpResponseRedirect`` on a matched rule, ``TemplateResponse``
        for the resolver page, or ``None`` when no routing action is
        warranted.
    """
    # Local import — the RoutingRule model lives in the CMS app; importing
    # it at module scope would create an import cycle since routing/ is
    # loaded via cms.models.__init__.
    from springfield.cms.models.routing import RULE_STATUS_LIVE

    live_rules = list(canonical.routing_rules.filter(status=RULE_STATUS_LIVE).select_related("target_page"))
    if not live_rules:
        return None

    server_signals = registry.resolve_server_signals(request, context=signal_context or {})
    result = evaluate_rules(live_rules, server_signals)

    if result.matched is not None:
        return _redirect_to_variant(request, canonical, result.matched)

    client_rules = [r for r in result.unresolved if rule_needs_client_side(r, registry=registry)]
    if not client_rules:
        # Log unresolved-but-not-client-side rules so marketing has a signal
        # when live rules can't be evaluated for a request (e.g. a Firefox-
        # only signal on a Chrome UA). Silent no-op with observability.
        if result.unresolved:
            logger.info(
                "user_routing: %d live rules unresolvable for canonical=%r; canonical will serve. Rules: %s",
                len(result.unresolved),
                getattr(canonical, "pk", None),
                [getattr(r, "name", "?") for r in result.unresolved],
            )
        return None

    return _render_resolver_page(request, canonical, client_rules, registry=registry)


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


def _render_resolver_page(request, canonical, client_rules, *, registry):
    """Serialize the client-side rule set and render the resolver page.

    The template embeds two JSON blobs:

    * ``rules_json`` — the rules the client must evaluate, each with a
      pre-resolved ``target_url`` (so the client doesn't need to know how
      to build variant URLs).
    * ``signal_metadata_json`` — for each signal referenced by any client
      rule: the UITour key to fetch. The client-side resolver library
      has a hardcoded map of signal name → extractor function that
      converts the UITour response into the signal value.

    Each rule's serialized ``target_url`` includes analytics attribution
    params (``routed_from``, ``routed_rule``, ``routed_mode=client``) so
    when the resolver JS navigates to a variant, the landing event fires
    with the same attribution as a server-side redirect.
    """
    canonical_url = canonical.get_url(request=request) or "/"
    querystring = _strip_reserved_routing_params(request.META.get("QUERY_STRING", ""))
    canonical_url_with_qs = _append_qs(canonical_url, querystring)

    canonical_slug = getattr(canonical, "slug", "") or ""

    serialized_rules = []
    required_signal_names: set[str] = set()

    for rule in client_rules:
        signal_name = (rule.condition or {}).get("signal")
        if signal_name:
            required_signal_names.add(signal_name)

        target_url = rule.target_page.get_url(request=request) or canonical_url
        # Preserve the incoming querystring on variant URLs too — the user's
        # utm_source, oldversion, etc. shouldn't be dropped by the resolver.
        target_url = _append_qs(target_url, querystring)
        # Attach analytics attribution — mode is "client" here because the
        # resolver JS is what will navigate the user, not the server.
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
                "priority": rule.priority,
                "condition": rule.condition,
                "target_url": target_url,
            }
        )

    signal_metadata: dict[str, dict[str, str]] = {}
    for signal_name in required_signal_names:
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
            "canonical_url_json": _json_for_script(canonical_url_with_qs),
            "rules_json": _json_for_script(serialized_rules),
            "signal_metadata_json": _json_for_script(signal_metadata),
        },
    )
    _set_canonical_link_header(response, canonical_url)
    return response
