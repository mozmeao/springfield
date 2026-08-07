# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The routing adoption mixin.

``RoutingMixin`` is the whole adoption surface a consumer page type touches. It
declares exactly two overridable hooks — a **trigger** and an **eligibility predicate**
— and adapts the serve path onto them. It adds **no database fields** (all state lives in
the routing tables keyed to ``wagtailcore.Page``), so adopting it produces **no
migration**.

The admin authoring surface — the "User Routing" edit tab and its page form — reopens
this class in a later change; this one owns the declaration surface and dispatch.
"""

from django.db import models

import waffle

from springfield.cms.routing.dispatch import SERVE_PREVIEW, SERVE_RESOLVER, USER_ROUTING_SWITCH, decide_routing
from springfield.cms.routing.models import RoutingConfig
from springfield.cms.routing.params import LOOP_BREAKER_PARAM


class RoutingMixin(models.Model):
    """Abstract mixin a Wagtail page type mixes in to adopt routing.

    A consumer declares exactly two things by overriding the hooks below and adds
    no view code, no framework code, and no schema. List this mixin **before** the
    page base class so its ``get_edit_handler`` wins in the MRO.
    """

    class Meta:
        abstract = True

    # -- Adoption surface: the only two things a consumer declares --

    def get_routing_trigger(self):
        """This surface's trigger — the arming condition under which routing fires.

        Default **unset** (``None``): absent a trigger, dispatch never fires and
        organic traffic is untouched. A consumer overrides this to return its arming
        condition.
        """
        return None

    def is_routing_canonical(self):
        """Whether this page may *host* rules — the consumer's notion of "canonical".

        Framework default is **fail-closed** (``False``): a half-adopted
        consumer never routes and never shows the routing tab. Each consumer overrides
        this with a predicate over its own tree.
        """
        return False

    # -- Serve-path dispatch --

    def _routing_trigger_satisfied(self, request):
        """Whether this request arms routing for the surface (consumer trigger)."""
        trigger = self.get_routing_trigger()
        return bool(trigger is not None and trigger.is_satisfied(request))

    def _has_live_routing_rules(self):
        """Whether the page hosts at least one rule that could route a visitor.

        Asks the same question the serializer answers, through the same code, so the gate
        can never let a page serve a resolver the serializer then empties — or withhold
        one whose rules resolve perfectly well in this locale.
        """
        # Imported at call time for the same reason serve() does: keeps the resolver's
        # l10n import chain out of model loading.
        from springfield.cms.routing.resolver import usable_rules

        return bool(usable_rules(self))

    def serve(self, request, *args, **kwargs):
        """Thin adapter: map request/page state onto flags, then act on the decision.

        Routing *policy* lives in the pure ``decide_routing`` function; this method only
        reads the flags off the request and page and performs the chosen branch. The
        global ``user_routing`` waffle switch is the outermost gate — off ⇒ canonical
        exactly as today (the framework ships dark).
        """
        # Imported here (request time) to keep the resolver/preview + l10n import chain
        # out of model loading; dispatch only matters when a page is actually served.
        from springfield.cms.routing.preview import get_preview_response, is_preview_admin, is_preview_request
        from springfield.cms.routing.resolver import render_resolver

        decision = decide_routing(
            routing_enabled=waffle.switch_is_active(USER_ROUTING_SWITCH),
            has_loop_breaker=bool(request.GET.get(LOOP_BREAKER_PARAM)),
            is_preview_admin=is_preview_request(request) and is_preview_admin(request),
            is_paused=RoutingConfig.is_paused_for(self),
            trigger_satisfied=self._routing_trigger_satisfied(request),
            is_canonical=self.is_routing_canonical(),
            has_live_rules=self._has_live_routing_rules(),
        )

        if decision == SERVE_RESOLVER:
            return render_resolver(request, self)
        if decision == SERVE_PREVIEW:
            preview_response = get_preview_response(request, self)
            if preview_response is not None:
                return preview_response
        # SERVE_CANONICAL (and any preview that produced nothing) — serve as today.
        return super().serve(request, *args, **kwargs)
