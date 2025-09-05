# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import logging
import urllib.parse

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import NoReverseMatch
from django.utils.encoding import smart_str

import jinja2
from django_jinja import library
from markupsafe import Markup

from lib.l10n_utils import get_translations_native_names
from springfield.base import waffle
from springfield.utils import expand_locale_groups

from ..urlresolvers import reverse

CSS_TEMPLATE = '<link href="%s" rel="stylesheet" type="text/css">'
CSS_TEMPLATE_IE = '<link href="%s" rel="stylesheet" type="text/css" media="all and (-ms-high-contrast: none)">'
JS_TEMPLATE = '<script src="%s"></script>'
log = logging.getLogger(__name__)


@library.global_function
@jinja2.pass_context
def switch(cxt, name, locales=None):
    """
    A template helper around `base.waffle.switch`. See docs there for details.

    If the `locales` argument is a list of locales then it will only check the switch in those
    locales, and return False otherwise. The `locales` argument could also contain a "locale group",
    which is a list of locales for a prefix (e.g. "en" expands to "en-US, en-GB").
    """
    if locales:
        if cxt["LANG"] not in expand_locale_groups(locales):
            return False

    return waffle.switch(name)


@library.global_function
def thisyear():
    """The current year."""
    return Markup(datetime.date.today().year)


@library.global_function
def url(viewname, *args, **kwargs):
    """Helper for Django's ``reverse`` in templates."""

    try:
        # First, look for URLs which only exist in the CMS - these are solely defined
        # in springfield/cms/cms_only_urls.py. These URLs are not listed in
        # the main URLConf because they aren't served by the Django views in
        # Springfield, but they will/must have matching routes set up in the CMS.
        return reverse(
            viewname,
            urlconf="springfield.cms.cms_only_urls",
            args=args,
            kwargs=kwargs,
        )
    except NoReverseMatch:
        return reverse(viewname, args=args, kwargs=kwargs)


@library.filter
def urlparams(url_, hash=None, **query):
    """Add a fragment and/or query paramaters to a URL.

    New query params will be appended to exising parameters, except duplicate
    names, which will be replaced.
    """
    url = urllib.parse.urlparse(url_)
    fragment = hash if hash is not None else url.fragment

    # Use dict(parse_qsl) so we don't get lists of values.
    q = url.query
    query_dict = dict(urllib.parse.parse_qsl(smart_str(q))) if q else {}
    query_dict.update((k, v) for k, v in query.items())

    query_string = _urlencode([(k, v) for k, v in query_dict.items() if v is not None])
    new = urllib.parse.ParseResult(url.scheme, url.netloc, url.path, url.params, query_string, fragment)
    return new.geturl()


def _urlencode(items):
    """A Unicode-safe URLencoder."""
    try:
        return urllib.parse.urlencode(items)
    except UnicodeEncodeError:
        return urllib.parse.urlencode([(k, smart_str(v)) for k, v in items])


@library.filter
def mailtoencode(txt):
    """Url encode a string using %20 for spaces."""
    if isinstance(txt, str):
        txt = txt.encode("utf-8")
    return urllib.parse.quote(txt)


@library.filter
def urlencode(txt):
    """Url encode a string using + for spaces."""
    if isinstance(txt, str):
        txt = txt.encode("utf-8")
    return urllib.parse.quote_plus(txt)


@library.global_function
def static(path):
    if settings.DEBUG and path.startswith("/"):
        raise ValueError("Static paths must not begin with a slash")

    try:
        return staticfiles_storage.url(path)
    except ValueError as e:
        log.warning(str(e))
        return path


@library.global_function
def js_bundle(name):
    """Include a JS bundle in the template.

    Bundles are defined in the "media/static-bundles.json" file.
    """
    path = f"js/{name}.js"
    path = staticfiles_storage.url(path)
    return Markup(JS_TEMPLATE % path)


@library.global_function
def css_bundle(name, target_old_ie=False):
    """Include a CSS bundle in the template.

    Bundles are defined in the "media/static-bundles.json" file.

    Args:
        name: The bundle name as defined in static-bundles.json
        target_old_ie: If True, adds media="all and (-ms-high-contrast: none)" for IE10/11
                  and wraps in conditional comments for IE9 and lower
    """
    path = f"css/{name}.css"
    path = staticfiles_storage.url(path)

    if target_old_ie:
        # For IE10/11 with media query
        ie_link = CSS_TEMPLATE_IE % path
        # For IE9 and lower with conditional comment
        ie9_link = f'<!--[if IE]>\n    {CSS_TEMPLATE % path}\n<![endif]-->'
        return Markup(f'{ie9_link}\n    {ie_link}')
    else:
        return Markup(CSS_TEMPLATE % path)


@library.global_function
def alternate_url(path, locale):
    alt_paths = settings.ALT_CANONICAL_PATHS
    path = path.lstrip("/")
    if path in alt_paths and locale in alt_paths[path]:
        return alt_paths[path][locale]

    return None


@library.global_function
def get_locale_options(request, translations):
    # For purely Django-rendered pages, or purely CMS-backed pages, we can just
    # rely on the `translations` var in the render context to know what locales
    # are viable for the page being rendered. Great! \o/
    available_locales = translations

    # However, if a URL route is decorated with springfield.cms.decorators.prefer_cms
    # that means that a page could come from the CMS or from Django depending on
    # the locale being requested. In this situation _locales_available_via_cms
    # and _locales_for_django_fallback_view are annotated onto the request.
    # We need to use these to create a more accurate view of what locales are
    # available. Also note that being decorated with prefer_cms doesn't guarantee
    # that the annotated lists of locales contain any values, so we must also count
    # them to be sure they are viable lists.

    cms_locale_count = len(getattr(request, "_locales_available_via_cms", []))
    django_fallback_locale_count = len(getattr(request, "_locales_for_django_fallback_view", []))

    if cms_locale_count > 0 and django_fallback_locale_count > 0:
        available_locales = get_translations_native_names(sorted(set(request._locales_available_via_cms + request._locales_for_django_fallback_view)))

    return available_locales
