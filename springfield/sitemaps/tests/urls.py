# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from lib import l10n_utils
from springfield.base.i18n import springfield_i18n_patterns


def page(request):
    return l10n_utils.render(request, "page.html")


def locale_selection(request):
    return l10n_utils.locale_selection(request)


urlpatterns = springfield_i18n_patterns(
    path("page/", page),
    path("locale-selection/", locale_selection),
)
