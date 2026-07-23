# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Wagtail admin view: User Routing signals reference.

Auto-generates a reference table from the live ``SignalRegistry``. Never
goes stale: adding, changing, or removing a signal in
``springfield.cms.routing.__init__`` updates this page for free.

Intended audience is marketing operators who need to look up "what values
can I put in Expected values for signal X?" while authoring a User
Routing rule.
"""

from django.template.response import TemplateResponse

from .signals import registry


def signals_reference(request):
    """Render the signals reference table for the Wagtail admin.

    No authentication decorator needed here — the URL is registered under
    Wagtail's admin URL space via ``register_admin_urls``, which is
    already gated by Wagtail's admin login middleware.
    """

    # Sort so UITour signals (delayed) group at the bottom and everything
    # else (immediate) sorts by name up top — matches the mental model of
    # "fast on the top, slow on the bottom" without needing a separate
    # category column.
    def _sort_key(signal):
        return (signal.source == "UITour", signal.source, signal.name)

    signals = []
    for signal in sorted(registry.all(), key=_sort_key):
        signals.append(
            {
                "name": signal.name,
                "description": signal.description,
                "source": signal.source or "—",
                "is_uitour": signal.source == "UITour",
                "value_type": signal.value_type.value,
                "enum_values": list(signal.enum_values) if signal.enum_values else None,
            }
        )
    # Force the Django Templates backend — this template extends
    # ``wagtailadmin/base.html``, which is a Django template, not Jinja.
    # Without ``using=``, Django's template loader tries Jinja first and
    # fails because the Wagtail admin base isn't on Jinja's search path.
    return TemplateResponse(
        request,
        "cms/routing/admin/signals_reference.html",
        {"signals": signals},
        using="django",
    )
