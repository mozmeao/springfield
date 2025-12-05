# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path, re_path

from pattern_library import get_pattern_template_suffix, views

from springfield.cms.pattern_library_views import RenderPatternView

app_name = "pattern_library"
urlpatterns = [
    # UI
    path("", views.IndexView.as_view(), name="index"),
    re_path(
        r"^pattern/(?P<pattern_template_name>[\w./\-]+%s)$" % (get_pattern_template_suffix()),
        views.IndexView.as_view(),
        name="display_pattern",
    ),
    # iframe rendering - using our custom view
    re_path(
        r"^render-pattern/(?P<pattern_template_name>[\w./\-]+%s)$" % (get_pattern_template_suffix()),
        RenderPatternView.as_view(),  # Our custom view
        name="render_pattern",
    ),
    # API rendering
    path("api/v1/render-pattern", views.render_pattern_api, name="render_pattern_api"),
]
