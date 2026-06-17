# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import re_path

from springfield.sitemaps.views import SitemapView

urlpatterns = (
    # Backward-compatible alias: Google has indexed /all-urls.xml; keep working.
    re_path(r"all-urls(?P<is_global>-global)?.xml", SitemapView.as_view()),
    # Canonical sitemap path; referenced from robots.txt and sitemap_index.xml.
    re_path(r"sitemap(?P<is_global>-global)?.xml", SitemapView.as_view()),
)
