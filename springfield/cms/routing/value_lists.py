# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Closed value sets for STRING signals whose domain is fully known.

Some STRING signals carry a **complete** set of legal values — every value the reader can
ever produce is in the set — so an off-list value is always a typo, never a legitimate
case the author knows better about. That makes membership enforceable: the admin JS blocks
it before submit and ``RoutingCondition.clean()`` rejects it on save.

They are STRING rather than ENUM for a purely mechanical reason: the sets are lazy and
data-backed, so declaring them as registry enums at import time would reintroduce the
app-init data access the framework avoids. They are enums in everything but declaration,
which is why the sets are resolved here, per request.

Two different domains are at work, and conflating them is a trap:

* ``locale`` / ``language`` describe **what we serve**, so the set is Springfield's own.
* ``browser_language`` describes **what the visitor speaks**, which is the whole reason
  the signal exists — it is the only way to see that, say, a Norwegian was served English
  because no Norwegian translation existed. Restricting it to languages we serve would
  leave it unable to say anything ``locale`` does not already say, so it is validated
  against the full CLDR language list instead.

Lives in its own module so both the admin payload and model validation can read it
without one importing the other.
"""

from functools import lru_cache

from django.conf import settings

from babel import Locale
from product_details import product_details


@lru_cache(maxsize=1)
def cldr_language_codes():
    """Every language code CLDR knows — 600-odd, two- and three-letter.

    This is the vocabulary browsers and operating systems draw their language lists from,
    so it is the right domain for a browser-reported language. Django's ``LANG_INFO`` and
    the product-details language list are both far narrower sets of *supported* languages
    and wrongly reject real values (Maltese, Dzongkha, Yoruba, the ``no`` macrolanguage).

    Cached: CLDR data is static, and this is read on every editor load and rule save.
    """
    return frozenset(code for code in Locale("en").languages if code.isalpha())


def known_value_lists():
    """Signal name -> the complete set of legal values, for validation.

    A signal absent from this mapping has no closed set and its values are unconstrained.
    """
    # Every locale Springfield serves. Deliberately NOT WAGTAIL_CONTENT_LANGUAGES: that is
    # the much smaller set of locales CMS *content* is translated into, while these signals
    # read what the *visitor* has, which can be any served locale.
    locales = [code for code, _label in settings.LANGUAGES]
    # The same set with the region dropped, so one condition covers every regional variant
    # of a language (`en` covers en-US, en-GB, en-CA).
    languages = sorted({code.split("-")[0] for code in locales})
    return {
        "locale": locales,
        "language": languages,
        # CLDR *plus* our own: a couple of Springfield locales (azz, skr) predate or sit
        # outside CLDR, and it would be absurd for `language is azz` to be authorable while
        # `browser_language is azz` is not.
        "browser_language": sorted(cldr_language_codes() | set(languages)),
        # Every region product_details knows, matching the uppercase ISO codes the geo
        # reader produces.
        "country": sorted({code.upper() for code in product_details.get_regions("en-US").keys()}),
    }


def suggested_value_lists():
    """Signal name -> a shorter set to *show* an author, where the legal set is unhelpful.

    Only ``browser_language`` needs this: listing 600-odd CLDR codes as guidance is noise,
    while the languages we actually publish in are the ones an author is realistically
    targeting. Anything else in the legal set still validates.
    """
    languages = sorted({code.split("-")[0] for code, _label in settings.LANGUAGES})
    return {"browser_language": languages}
