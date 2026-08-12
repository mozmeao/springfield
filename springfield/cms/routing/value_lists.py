# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Closed value sets for STRING signals whose domain is fully known.

An off-list value for these can never match at runtime, so membership is enforced — in the
admin before submit, and in ``RoutingCondition.clean()`` on save.

STRING rather than ENUM because the sets are lazy and data-backed: declaring them as
registry enums would move that data access to app startup.

The two domains must not be conflated. ``locale``/``language`` are what Springfield
*serves*; ``browser_language`` is what the *visitor speaks*, validated against the full CLDR
list so it can still report a Norwegian who was served English.
"""

from functools import lru_cache

from django.conf import settings

from babel import Locale
from product_details import product_details


@lru_cache(maxsize=1)
def cldr_language_codes():
    """Every language code CLDR knows — the vocabulary browsers draw their language lists from.

    Django's ``LANG_INFO`` and the product-details list are narrower sets of *supported*
    languages and wrongly reject real values (Maltese, Dzongkha, Yoruba, the ``no``
    macrolanguage). Cached because the data is static and this is read on every editor load.
    """
    return frozenset(code for code in Locale("en").languages if code.isalpha())


# Named explicitly so "no value list by design" is distinguishable from "the value list came
# back empty". Every set below is derived from settings or product data, so an upstream rename
# can empty one — and an empty set read as "unconstrained" would switch validation off silently.
CLOSED_SET_SIGNALS = frozenset({"locale", "language", "browser_language", "country"})


def known_value_lists():
    """Signal name -> the complete set of legal values, for validation.

    A signal absent from this mapping has no closed set and its values are unconstrained.
    Every name in ``CLOSED_SET_SIGNALS`` must be present with a non-empty set.
    """
    # NOT WAGTAIL_CONTENT_LANGUAGES: that is the smaller set of locales CMS *content* is
    # translated into, while these signals read what the *visitor* has.
    locales = [code for code, _label in settings.LANGUAGES]
    # Region dropped, so one condition covers every variant (`en` covers en-US, en-GB, en-CA).
    languages = sorted({code.split("-")[0] for code in locales})
    return {
        "locale": locales,
        "language": languages,
        # CLDR plus our own: a couple of Springfield locales (azz, skr) sit outside CLDR, and
        # `language is azz` being authorable while `browser_language is azz` is not would be odd.
        "browser_language": sorted(cldr_language_codes() | set(languages)),
        # Uppercase ISO codes, matching what the geo reader produces.
        "country": sorted({code.upper() for code in product_details.get_regions("en-US").keys()}),
    }


def suggested_value_lists():
    """Signal name -> a shorter set to *show* an author, where the legal set is unhelpful.

    Only ``browser_language`` needs it: 600-odd CLDR codes are noise as guidance. Anything
    else in the legal set still validates.
    """
    languages = sorted({code.split("-")[0] for code, _label in settings.LANGUAGES})
    return {"browser_language": languages}
