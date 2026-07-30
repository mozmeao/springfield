# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The routing adoption mixin (spec §2.2).

``RoutingMixin`` is the whole adoption surface a consumer page type touches. It
declares exactly three overridable hooks — a **trigger**, an **eligibility
predicate**, and a **signal subset** — and wires a "User Routing" edit tab holding
the rules and kill-switch panels. It adds **no database fields** (all state lives in
the C3 tables keyed to ``wagtailcore.Page``), so adopting it produces **no
migration**. The serve-path dispatch is wired later (C10); this mixin only owns the
declaration surface and the admin tab.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import InlinePanel, ObjectList, TabbedInterface
from wagtail.utils.decorators import cached_classmethod

from springfield.cms.routing.signals import registry


def routing_tab_is_shown(instance):
    """Whether the "User Routing" tab should render for ``instance``.

    The tab is shown only on canonical instances (plan C4): a routing-enabled page
    *type* can have non-canonical instances (e.g. a variant nested under a canonical)
    whose rules would never fire at dispatch, so presenting a fully-functional-looking
    routing tab there would be dead config. Evaluated from the page's own eligibility
    predicate, which reads its tree position.
    """
    predicate = getattr(instance, "is_routing_canonical", None)
    return bool(instance is not None and callable(predicate) and predicate())


class RoutingObjectList(ObjectList):
    """An edit-tab that renders only on canonical instances (plan C4)."""

    class BoundPanel(ObjectList.BoundPanel):
        def is_shown(self):
            return routing_tab_is_shown(self.instance)


class RoutingMixin(models.Model):
    """Abstract mixin a Wagtail page type mixes in to adopt routing (spec §2.2).

    A consumer declares exactly three things by overriding the hooks below and adds
    no view code, no framework code, and no schema. List this mixin **before** the
    page base class so its ``get_edit_handler`` wins in the MRO.
    """

    class Meta:
        abstract = True

    # -- Adoption surface: the only three things a consumer declares (spec §2.2) --

    def get_routing_trigger(self):
        """This surface's trigger — the arming condition under which routing fires.

        Default **unset** (``None``): absent a trigger, dispatch never fires and
        organic traffic is untouched. A consumer overrides this to return its arming
        condition (the query-param realization lands in C7; WNP wires it in C14).
        """
        return None

    def is_routing_canonical(self):
        """Whether this page may *host* rules — the consumer's notion of "canonical".

        Framework default is **fail-closed** (``False``, plan §0.4-A): a half-adopted
        consumer never routes and never shows the routing tab. Each consumer overrides
        this with a predicate over its own tree (WNP does so in C14).
        """
        return False

    def get_routing_signal_names(self):
        """The registry signals this consumer's authors may test (spec §2.2).

        Defaults to the whole registry; a consumer narrows it to the subset that makes
        sense for its audience (e.g. WNP's version-centric set in C14).
        """
        return tuple(registry.names())

    # -- Admin wiring: the framework-owned "User Routing" tab (spec §6.1) --

    routing_panels = [
        InlinePanel("routing_rules", label=_("Rules")),
        InlinePanel("routing_config", label=_("Kill switch"), max_num=1),
    ]

    @classmethod
    def get_routing_tab(cls):
        """The "User Routing" tab: the rules panel and the single kill-switch panel."""
        return RoutingObjectList(cls.routing_panels, heading=_("User Routing"))

    @cached_classmethod
    def get_edit_handler(cls):
        """Extend Wagtail's default page tabs with the "User Routing" tab.

        Mirrors Wagtail's default ``TabbedInterface`` (Content / Promote / Settings)
        and appends the routing tab. A consumer that defines its own ``edit_handler``
        is left untouched (it can add the tab itself).
        """
        if hasattr(cls, "edit_handler"):
            return cls.edit_handler.bind_to_model(cls)

        tabs = []
        if cls.content_panels:
            tabs.append(ObjectList(cls.content_panels, heading=_("Content")))
        if cls.promote_panels:
            tabs.append(ObjectList(cls.promote_panels, heading=_("Promote")))
        if cls.settings_panels:
            tabs.append(ObjectList(cls.settings_panels, heading=_("Settings")))
        tabs.append(cls.get_routing_tab())

        edit_handler = TabbedInterface(tabs, base_form_class=cls.base_form_class)
        return edit_handler.bind_to_model(cls)
