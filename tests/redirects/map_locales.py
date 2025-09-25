# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import requests

from .base import flatten, url_test

# supported locales
LOCALES = [
    "an",
    "ar",
    "ast",  # / then redirects to fallback
    "be",
    "bg",  # / then redirects to fallback
    "bs",
    "ca",
    "cak",
    "cs",
    "cy",
    "da",
    "de",
    "dsb",
    "el",
    "en-CA",
    "en-GB",
    "en-US",
    "es-AR",
    "es-CL",
    "es-ES",
    "es-MX",
    "fi",
    "fr",
    "fy-NL",
    "gd",  # / then redirects to fallback
    "gl",
    "gn",
    "he",
    "hi-IN",
    "hr",
    "hsb",
    "hu",
    "ia",
    "id",
    "is",
    "it",
    "ja",
    "ka",
    "kab",
    "ko",
    "lo",
    "ms",
    "nb-NO",
    "nl",
    "nn-NO",
    "pa-IN",
    "pl",
    "pt-BR",
    "pt-PT",
    "rm",
    "ru",
    "sco",
    "si",
    "sk",
    "skr",
    "sl",
    "sq",
    "sr",
    "sv-SE",
    "ta",  # / then redirects to fallback
    "tg",
    "th",
    "tr",
    "uk",
    "vi",
    "zh-CN",
    "zh-TW",
]

# List of some locale name variants including ambiguous short names, BCP47
# tags with a mix of ISO 639, ISO 15924, ISO 3166-1 and UN M.49 codes, and
# historic ab-CD-encoding values, which could be included in the visitors'
# Accept-Language HTTP header and should be redirected to the respective
# canonical locales
LOCALE_VARIANTS = {
    # Default en-US is used for any unknown English locale. Every partially
    # translated en-* locale is treated as fully active, see bug 1457959
    # We currently have en-{US,CA,GB}.
    "en-US": ["en", "en-XX", "en-GB-cockney"],  # No BCP47 (sub)tag parsing
    "ca": ["ca-ES-valencia"],
    "es-ES": ["es", "es-419"],
    "fr": ["fr-FR"],
    "ja": ["ja-JP-mac"],
    "nb-NO": ["no"],
    "pt-BR": ["pt"],
    "rm": ["rm-sursilv"],
    "sr": ["sr-Cyrl"],
    "ta": ["ta-LK"],
    "zh-TW": ["zh-Hant", "zh-Hant-TW"],  # Bug 1263193
}

_urls = []
for locale in LOCALES:
    variants = [locale]
    variants.extend(LOCALE_VARIANTS.get(locale, []))
    for variant in variants:
        # check the landing page redirects for each locale variant
        _urls.append(url_test("/", f"/{locale}/", req_headers={"Accept-Language": variant}, status_code=requests.codes.found))

URLS = flatten(_urls)
