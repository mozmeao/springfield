# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict

from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from wagtail.models import Locale

from lib.l10n_utils import RequireSafeMixin
from springfield.base.decorators import cache_control_expires
from springfield.sitemaps.models import NO_LOCALE, SitemapURL


@method_decorator(cache_control_expires(1), name="dispatch")
class SitemapView(RequireSafeMixin, TemplateView):
    content_type = "text/xml"

    def _get_locale(self):
        if "is_global" in self.kwargs:
            # is_global here refers to the all-urls-global.xml URL. the value of that kwarg
            # when on that URL will be "_none" and will be None if not on that URL.
            # For that page we set the locale to the special value as that is what the entries
            # in the DB have recorded for locale for URLs that don't have a locale.
            locale = NO_LOCALE
        else:
            # can come back as empty string
            # should be None here if not a real locale because
            # None will mean that we should show the index of sitemaps
            # instead of a sitemap for a locale.
            locale = getattr(self.request, "locale", None)

        return locale

    def get_template_names(self):
        if self._get_locale():
            return ["sitemap.xml"]
        else:
            return ["sitemap_index.xml"]

    def _get_supported_locales(self):
        """Return the set of language codes Mozilla actively supports.

        Source of truth: Wagtail's Locale model, managed via the Wagtail admin
        under Settings > Languages. As Mozilla adds/removes paid-translation
        locales there, this set stays in sync without code changes.
        """
        return set(Locale.objects.values_list("language_code", flat=True))

    def _build_alternates(self, locale, supported_locales):
        """Build the {path: [locale_list]} hreflang alternates map.

        Returns an empty dict for:
        - NO_LOCALE (global URLs have no language alternates)
        - Locales not in the supported set (legacy locales emit no hreflang
          annotations, since their content has drifted from the supported
          translations and declaring them as alternates would misuse hreflang)

        Otherwise returns the alternates grouped from SitemapURL rows, filtered
        to supported locales only.
        """
        if locale == NO_LOCALE or locale not in supported_locales:
            return {}

        alternates = defaultdict(list)
        rows = SitemapURL.objects.filter(locale__in=supported_locales).order_by("path", "locale").values("path", "locale")
        for row in rows:
            alternates[row["path"]].append(row["locale"])
        return dict(alternates)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        locale = self._get_locale()
        if locale:
            ctx["paths"] = SitemapURL.objects.all_for_locale(locale)
            supported_locales = self._get_supported_locales()
            ctx["alternates"] = self._build_alternates(locale, supported_locales)
        else:
            ctx["locales"] = SitemapURL.objects.all_locales()
            ctx["NO_LOCALE"] = NO_LOCALE

        return ctx
