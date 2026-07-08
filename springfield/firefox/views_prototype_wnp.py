# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Prototype 1 for the WNP Dynamic Rendering plan.

Answers: what are P50/P95/P99 timings for UITour.ping() and getConfiguration()
on real Firefox users, on real hardware and networks?

The number decides whether the resolver-page pattern (see
.research/wnp-dynamic-rendering-plan.md) is viable at the 800ms timeout we've
been designing around.

This file is expected to be removed once Prototype 1 completes and its findings
are recorded. It is deliberately not integrated with the main WNP flow.
"""

import json
import logging
import re

from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lib.l10n_utils import L10nTemplateView
from springfield.base import metrics

logger = logging.getLogger(__name__)

METRIC_NAMESPACE = "wnp_uitour_prototype"

ALLOWED_OUTCOMES = {"success", "ping_timeout", "config_timeout", "config_error", "no_uitour", "unknown"}
TIMING_FIELDS = ("ping_ms", "appinfo_ms", "sync_ms", "total_ms")
MAX_TIMING_MS = 60_000  # anything larger is nonsense; drop it

# ---------------------------------------------------------------------------
# Prototype 2: end-to-end resolver flow.
#
# Proves the full pattern in Springfield's real middleware stack:
#   1. Server evaluates rules with server-resolvable signals (oldversion, geo,
#      UA). Full match → 302 to variant.
#   2. Otherwise, if utm_source=update (Balrog flow) and unresolved rules
#      reference client-side signals → serve the resolver page.
#   3. Otherwise → 302 to canonical.
#
# Uses a hardcoded fake ruleset — no CMS models yet. Two rules exercise both
# server-side (lapsed_user via oldversion) and client-side (sync-setup via
# UITour) resolution paths.
# ---------------------------------------------------------------------------

# The fake ruleset for prototype 2. Rules are ordered by priority (lower first).
# Signals declared as required_signals let the resolver page know which UITour
# keys to fetch.
PROTO_RULES = [
    {
        "name": "lapsed-users",
        "priority": 100,
        "required_signals": ["lapsed_user"],
        "condition": {"signal": "lapsed_user", "equals": True},
        "variant": "lapsed",
    },
    {
        "name": "signed-in-users",
        "priority": 200,
        "required_signals": ["sync_setup"],
        "condition": {"signal": "sync_setup", "equals": True},
        "variant": "signed-in",
    },
]

# Signals we can resolve server-side without any UITour interaction. Anything
# not in this set is a client-side signal and needs the resolver page.
PROTO_SERVER_SIDE_SIGNALS = {"lapsed_user"}

# Minimum "major version gap" between the user's oldversion and the target
# version that qualifies as "lapsed". Chosen arbitrarily for the prototype.
LAPSED_MIN_GAP = 5


def _resolve_server_signals(request, version):
    """Compute the server-resolvable signal values for this request.

    Returns a dict of {signal_name: value}. Signals we can't resolve
    are simply absent from the dict — the rule evaluator treats them as
    'unknown' and skips rules that depend on them.
    """
    signals = {}

    oldversion_raw = request.GET.get("oldversion", "")
    old_major_match = re.match(r"^(rv:)?(\d{1,3})", oldversion_raw)
    if old_major_match:
        old_major = int(old_major_match.group(2))
        try:
            new_major = int(version)
        except (TypeError, ValueError):
            new_major = None
        if new_major is not None:
            signals["lapsed_user"] = (new_major - old_major) >= LAPSED_MIN_GAP

    return signals


def _rule_matches(rule, resolved_signals):
    """Return ``True`` if the rule fully matches with the signals we have,
    ``False`` if it definitively fails, ``None`` if we can't tell yet
    (a required signal is not present)."""
    condition = rule["condition"]
    signal_name = condition["signal"]
    if signal_name not in resolved_signals:
        return None
    return resolved_signals[signal_name] == condition["equals"]


def _evaluate_rules(rules, resolved_signals):
    """Evaluate rules in priority order against the resolved signals.

    Returns a tuple of ``(matched_rule, unresolved_rules)``:
      - matched_rule: the first rule that fully matches, or ``None``.
      - unresolved_rules: rules whose outcome we couldn't decide with the
        signals we have (they need client-side resolution).
    """
    unresolved = []
    for rule in sorted(rules, key=lambda r: r["priority"]):
        match = _rule_matches(rule, resolved_signals)
        if match is True:
            return rule, []
        if match is None:
            unresolved.append(rule)
    return None, unresolved


def _client_side_rules(rules):
    """Return only rules whose required_signals include any client-side signal."""
    return [rule for rule in rules if any(sig not in PROTO_SERVER_SIDE_SIGNALS for sig in rule["required_signals"])]


def _proto_url(version, kind):
    """Build a prototype URL (canonical or variant) with the version baked in."""
    return f"/en-US/whatsnew/dispatch/proto/{version}/{kind}/"


class WNPProtoDispatchView(L10nTemplateView):
    """The prototype dispatch endpoint.

    URL: /{lang}/whatsnew/dispatch/proto/<version>/

    Represents what `/whatsnew/{version}/` will do in the real design: server
    evaluates rules first, resolver page for client-side signals, canonical
    otherwise.
    """

    template_name = "firefox/whatsnew/dispatch-proto-resolver.html"

    def get(self, request, *args, **kwargs):
        version = kwargs.get("version") or ""
        utm_source = request.GET.get("utm_source", "")

        server_signals = _resolve_server_signals(request, version)
        matched, unresolved = _evaluate_rules(PROTO_RULES, server_signals)

        if matched is not None:
            # Full match on server signals — direct 302 to variant.
            logger.info(
                "wnp_proto dispatch=server-match version=%s rule=%s",
                version,
                matched["name"],
            )
            return HttpResponseRedirect(_proto_url(version, matched["variant"]))

        # Any unresolved rule needing client-side signals AND the request came
        # from a Balrog update → serve the resolver page.
        client_rules = _client_side_rules(unresolved)
        if client_rules and utm_source == "update":
            logger.info(
                "wnp_proto dispatch=resolver-page version=%s rules=%s",
                version,
                [r["name"] for r in client_rules],
            )
            self.extra_context = {
                "proto_version": version,
                "proto_rules_json": json.dumps(client_rules),
                "proto_canonical_url": _proto_url(version, "canonical"),
            }
            return super().get(request, *args, **kwargs)

        # No match, no eligible client-side path → canonical.
        logger.info("wnp_proto dispatch=canonical version=%s", version)
        return HttpResponseRedirect(_proto_url(version, "canonical"))


class WNPProtoCanonicalView(L10nTemplateView):
    """Stub canonical page for prototype 2."""

    template_name = "firefox/whatsnew/dispatch-proto-canonical.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proto_version"] = self.kwargs.get("version", "")
        return ctx


class WNPProtoVariantView(L10nTemplateView):
    """Stub variant page for prototype 2. Handles /lapsed/ and /signed-in/."""

    template_name = "firefox/whatsnew/dispatch-proto-variant.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proto_version"] = self.kwargs.get("version", "")
        ctx["proto_variant"] = self.kwargs.get("variant", "")
        return ctx


class WNPTimingTestView(L10nTemplateView):
    """Renders the UITour-timing measurement page.

    URL: /{lang}/whatsnew/dispatch/timing-test/

    Uses ``L10nTemplateView`` for the Fluent/l10n context the base-protocol
    template expects, even though this prototype has no localized strings —
    saves us reimplementing the context boilerplate for one throwaway page.
    """

    template_name = "firefox/whatsnew/dispatch-timing-test.html"


@csrf_exempt
@require_http_methods(["POST"])
def wnp_timing_report(request):
    """Accepts timing telemetry from the test page and forwards to metrics.

    Expected JSON payload (all fields optional; missing/invalid fields are dropped):
        {
          "ping_ms": int,             # 0..MAX_TIMING_MS
          "ping_success": bool,
          "appinfo_ms": int,
          "appinfo_success": bool,
          "aicontrols_ms": int,
          "aicontrols_success": bool,
          "total_ms": int,
          "outcome": str,             # one of ALLOWED_OUTCOMES
        }

    Deliberately does not accept any state values (AI Controls status, default
    browser bool, etc.) — only timings and outcome flags. See Privacy section
    of the plan.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    if not isinstance(payload, dict):
        return HttpResponse(status=400)

    outcome = str(payload.get("outcome", "unknown"))[:32]
    if outcome not in ALLOWED_OUTCOMES:
        outcome = "unknown"

    metrics.incr(f"{METRIC_NAMESPACE}.result", tags=[f"outcome:{outcome}"])

    logged_timings = {}
    for field in TIMING_FIELDS:
        value = payload.get(field)
        if isinstance(value, (int, float)) and 0 <= value <= MAX_TIMING_MS:
            metrics.timing(f"{METRIC_NAMESPACE}.{field}", value=int(value))
            logged_timings[field] = int(value)

    # Optional debug log for the dogfood collection period.
    logger.info(
        "wnp_uitour_prototype outcome=%s %s",
        outcome,
        " ".join(f"{k}={v}" for k, v in logged_timings.items()),
    )
    return HttpResponse(status=204)
