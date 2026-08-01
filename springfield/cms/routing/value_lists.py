# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Closed value sets for STRING signals whose domain is fully known.

``locale`` and ``country`` are STRING signals carrying a **complete** set of legal
values — every value the reader can ever produce is in the set — so an off-list value is
always a typo, never a legitimate case the author knows better about. That makes
membership enforceable: the admin JS blocks it before submit and
``RoutingCondition.clean()`` rejects it on save.

They are STRING rather than ENUM for a purely mechanical reason: both sets are lazy and
data-backed, so declaring them as registry enums at import time would reintroduce the
app-init data access the framework avoids. They are enums in everything but declaration,
which is why the sets are resolved here, per request.

Lives in its own module so both the admin payload and model validation can read it
without one importing the other.
"""

from django.conf import settings

from product_details import product_details


def known_value_lists():
    """Signal name -> its complete set of legal values.

    A signal absent from this mapping has no closed set and its values are unconstrained.
    """
    return {
        # Every locale Springfield serves. Deliberately NOT WAGTAIL_CONTENT_LANGUAGES: that
        # is the much smaller set of locales CMS *content* is translated into, while this
        # signal reads the *visitor's* page locale, which can be any served locale.
        "locale": [code for code, _label in settings.LANGUAGES],
        # Every region product_details knows, matching the uppercase ISO codes the geo
        # reader produces.
        "country": sorted({code.upper() for code in product_details.get_regions("en-US").keys()}),
    }
