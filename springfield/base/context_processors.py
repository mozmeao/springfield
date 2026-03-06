# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from datetime import datetime

from django.conf import settings

from lib.l10n_utils import translation
from springfield.base.geo import get_country_from_request


def geo(request):
    return {"country_code": get_country_from_request(request)}


def i18n(request):
    url_locale = translation.get_language()
    lang = dict(settings.LANGUAGE_URL_MAP).get(url_locale) or url_locale
    # Normally, CANONICAL_LANG == LANG, but sometimes, a user requests a page
    # that does not exist, but the locale has a fallback locale, so the user is
    # served the content from the fallback locale at the requested URL (for
    # example, the user requests /es-AR/somepage, which does not exist, so the
    # user gets /es-MX/somepage content at the /es-AR/somepage/ URL). In this
    # case, es-AR is the LANG, and es-MX is the CANONICAL_LANG.
    content_locale = getattr(request, "content_locale", None)
    return {
        "LANGUAGES": settings.LANGUAGES,
        "LANG": lang,
        "CANONICAL_LANG": content_locale or lang,
        "DIR": "rtl" if translation.get_language_bidi() else "ltr",
    }


def globals(request):
    return {
        "request": request,
        "settings": settings,
    }


def canonical_path(request):
    """
    The canonical path can be overridden with a template variable like
    l10n_utils.render(request, template_name, {'canonical_path': '/android/'})
    """
    lang = getattr(request, "locale", settings.LANGUAGE_CODE)
    url = getattr(request, "path", "/")
    return {"canonical_path": re.sub(r"^/" + lang, "", url) if lang else url}


def current_year(request):
    return {"current_year": datetime.today().year}
