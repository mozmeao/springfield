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
from typing import Any

from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse

from .evaluator import evaluate_rules, rule_needs_client_side
from .signals import registry as default_registry

RESOLVER_TEMPLATE = "cms/routing/resolver.html"


def dispatch_for_canonical(
    request,
    canonical,
    *,
    target_version: str | None = None,
    registry=default_registry,
):
    """Evaluate live routing rules for ``canonical`` and return a response.

    Args:
        request: The incoming HTTP request.
        canonical: The canonical Wagtail page hosting the rules.
        target_version: Optional context for signal resolvers (e.g. the
            WNP version being requested; used by ``lapsed_user``).
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

    context: dict[str, Any] = {}
    if target_version is not None:
        context["target_version"] = target_version

    server_signals = registry.resolve_server_signals(request, context=context)
    result = evaluate_rules(live_rules, server_signals)

    if result.matched is not None:
        return _redirect_to_variant(request, result.matched)

    client_rules = [r for r in result.unresolved if rule_needs_client_side(r, registry=registry)]
    if not client_rules:
        return None

    return _render_resolver_page(request, canonical, client_rules, registry=registry)


def _redirect_to_variant(request, matched_rule):
    """Build a 302 redirect to the matched rule's target, preserving the
    incoming querystring so downstream analytics keep working."""
    target_url = matched_rule.target_page.get_url(request=request)
    if not target_url:
        return None
    querystring = request.META.get("QUERY_STRING", "")
    if querystring:
        target_url = f"{target_url}?{querystring}"
    return HttpResponseRedirect(target_url)


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
    """
    canonical_url = canonical.get_url(request=request) or "/"
    querystring = request.META.get("QUERY_STRING", "")
    if querystring:
        canonical_url = f"{canonical_url}?{querystring}"

    serialized_rules = []
    required_signal_names: set[str] = set()

    for rule in client_rules:
        signal_name = (rule.condition or {}).get("signal")
        if signal_name:
            required_signal_names.add(signal_name)

        target_url = rule.target_page.get_url(request=request) or canonical_url
        # Preserve the incoming querystring on variant URLs too — the user's
        # utm_source, oldversion, etc. shouldn't be dropped by the resolver.
        if querystring and "?" not in target_url:
            target_url = f"{target_url}?{querystring}"

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

    return TemplateResponse(
        request,
        RESOLVER_TEMPLATE,
        {
            "canonical_url": canonical_url,
            "rules_json": json.dumps(serialized_rules),
            "signal_metadata_json": json.dumps(signal_metadata),
        },
    )
