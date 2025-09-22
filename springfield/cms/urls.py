# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from .views import TranslationsListView

app_name = "cms"

urlpatterns = [
    path("pages-list/", TranslationsListView.as_view(), name="translations_list"),
]
