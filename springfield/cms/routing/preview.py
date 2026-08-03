# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin-only routing preview flows.

Two flows let authors verify routing, including while a page is paused — both are
**admin-authenticated only**, both respond ``Cache-Control: no-store``, and both
**bypass the kill switch**:

* ``preview_rule={id}`` — a server-side 302 straight to the rule's target, skipping
  signal evaluation entirely. The target is resolved the way the serve path resolves it, and
  a rule that could not route a visitor is *reported as such* rather than redirected to:
  preview exists to say what visitors get, so it must never flatter a broken rule.
* ``preview_signal=name:value`` (repeatable) — renders the resolver with *fake* signal
  values injected via a ``data-*`` blob (the same attribute-on-the-page convention as
  the rest of the resolver), so the author exercises the real client evaluation path:
  faked signals resolve immediately, un-faked signals still read live.

The serve-path dispatcher calls :func:`get_preview_response` before the kill
switch and the trigger checks; a ``None`` return means "no preview — fall through".
"""

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from springfield.cms.routing.params import PREVIEW_RULE_PARAM, PREVIEW_SIGNAL_PARAM
from springfield.cms.routing.resolver import (
    localized_target,
    patch_request_for_resolver,
    render_resolver,
    url_in_requested_locale,
    usable_rules,
)
from springfield.cms.routing.signals import registry


def is_preview_request(request) -> bool:
    """Whether the request carries either preview param (regardless of auth)."""
    return PREVIEW_RULE_PARAM in request.GET or PREVIEW_SIGNAL_PARAM in request.GET


def is_preview_admin(request) -> bool:
    """Whether the requester may use the preview flows (a signed-in staff user)."""
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


def parse_fake_signals(values):
    """Parse repeated ``name:value`` preview params into a ``{name: value}`` map.

    Unknown signal names and malformed items are ignored.
    """
    fakes = {}
    for item in values:
        name, separator, value = item.partition(":")
        if separator and name in registry:
            fakes[name] = value
    return fakes


def _no_store(response):
    response["Cache-Control"] = "no-store"
    return response


def _inert(message):
    """Report a rule that will not fire, instead of redirecting to a page visitors never see."""
    return _no_store(HttpResponse(message, content_type="text/plain; charset=utf-8"))


def _why_the_rule_never_fires(rule, page):
    """Why ``rule`` cannot route a visitor on ``page``, or ``None`` if it can.

    The decision comes from the serve path itself, so preview can never disagree with what
    visitors get — that agreement is the whole value of the flow. The per-floor checks below
    only pick the wording for a rule already known to be unusable.
    """
    if any(usable.rule.pk == rule.pk for usable in usable_rules(page)):
        return None
    if rule.target is None:
        return _("This rule has no target, so it never fires.")
    target = localized_target(rule.target, page)
    if target is None:
        return _("This rule's target has no version in this locale, so it never fires here.")
    if not target.live:
        return _("This rule's target is not published, so it never fires.")
    if not target.is_descendant_of(page):
        return _("This rule's target is not part of this page, so it never fires.")
    return _("This rule cannot match anyone as configured, so it never fires.")


def _preview_rule(request, page):
    rule_id = request.GET.get(PREVIEW_RULE_PARAM)
    if not rule_id or not rule_id.isdigit():
        return None
    rule = page.routing_rules.filter(pk=int(rule_id)).first()
    if not rule:
        return None
    never_fires = _why_the_rule_never_fires(rule, page)
    if never_fires:
        return _inert(never_fires)
    # Resolved exactly as the resolver resolves it: this locale's version of the target,
    # carrying the locale prefix the requester asked for.
    url = url_in_requested_locale(localized_target(rule.target, page), request)
    if not url:
        # An unroutable page (no site) has no URL, and redirect(None) would 500.
        return _inert(_("This rule's target has no URL, so it never fires."))
    # Straight 302 to the target; signal evaluation is skipped entirely.
    return _no_store(redirect(url))


def _preview_signal(request, page):
    fakes = parse_fake_signals(request.GET.getlist(PREVIEW_SIGNAL_PARAM))
    # A live request from an author, not a Wagtail preview, so it needs the same request
    # setup as the serve path — including the page's locales, or the author is redirected
    # out of the locale they are trying to check.
    return _no_store(render_resolver(patch_request_for_resolver(request, page), page, fake_signals=fakes))


def get_preview_response(request, page):
    """Return an admin preview response, or ``None`` to fall through to normal serve.

    Non-admin requests carrying preview params fall through (the params are ignored).
    Both flows bypass the page kill switch by construction — they never consult it.
    """
    if not is_preview_admin(request):
        return None
    if PREVIEW_RULE_PARAM in request.GET:
        return _preview_rule(request, page)
    if PREVIEW_SIGNAL_PARAM in request.GET:
        return _preview_signal(request, page)
    return None
