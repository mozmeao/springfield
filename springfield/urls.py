# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.utils.module_loading import import_string

import wagtaildraftsharing.urls as wagtaildraftsharing_urls
from rest_framework.authtoken.views import obtain_auth_token
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from watchman import views as watchman_views

from springfield.base import views as base_views
from springfield.base.i18n import springfield_i18n_patterns

# The default django 404 and 500 handler doesn't run the ContextProcessors,
# which breaks the base template page. So we replace them with views that do!
handler500 = "springfield.base.views.server_error_view"
handler404 = "springfield.base.views.page_not_found_view"
locale404 = "lib.l10n_utils.locale_selection"

# Paths that should have a locale prefix
urlpatterns = springfield_i18n_patterns(
    # Main pages
    path("", include("springfield.firefox.urls")),
    path("privacy/", include("springfield.privacy.urls")),
    path("", include("springfield.newsletter.urls")),
)

# Paths that must not have a locale prefix
urlpatterns += (
    path("", include("springfield.base.nonlocale_urls")),
    path("healthz/", watchman_views.ping, name="watchman.ping"),
    path("readiness/", watchman_views.status, name="watchman.status"),
    path("healthz-cron/", base_views.cron_health_check),
    path("_documents/", include(wagtaildocs_urls)),
)

if settings.DEV:
    urlpatterns += springfield_i18n_patterns(
        # Add /404-locale/ for localizers.
        path("404-locale/", import_string(locale404)),
    )

if settings.DEBUG:
    urlpatterns += springfield_i18n_patterns(
        path("404/", import_string(handler404)),
        path("500/", import_string(handler500)),
    )
    urlpatterns += (path("csrf_403/", base_views.csrf_failure, {}),)

if settings.WAGTAIL_ENABLE_ADMIN:
    # If adding new a new path here, you must also add an entry to
    # settings.SUPPORTED_NONLOCALES in the `if WAGTAIL_ENABLE_ADMIN` block so
    # that springfield doesn't try to prepend a locale onto requests for the path
    urlpatterns += (
        path("oidc/", include("mozilla_django_oidc.urls")),
        path("cms-admin/", include(wagtailadmin_urls)),
        path("django-admin/", admin.site.urls),  # needed to show django-rq UI
        path("django-rq/", include("django_rq.urls")),  # task queue management
        path("_internal_draft_preview/", include(wagtaildraftsharing_urls)),  # ONLY available in CMS mode
        path("api-token-auth/", obtain_auth_token),
        path("releasenotes-admin/", include("springfield.releasenotes.urls")),
    )

if settings.ENABLE_DJANGO_SILK:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if settings.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage":
    # Serve media files from Django itself - production won't use this
    from django.urls import re_path
    from django.views.static import serve

    urlpatterns += (
        re_path(
            r"^custom-media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    )
    # Note that statics are handled via Whitenoise's middleware

# Wagtail is the catch-all route, and it will raise a 404 if needed.
# Note that we're also using localised URLs here
urlpatterns += springfield_i18n_patterns(
    path("", include(wagtail_urls)),
)
