#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

set -exo pipefail

rm -rf ./static

# We need to build statics with certain env vars temporarily enabled, so that we
# get all the files collected that are needed when those env vars are enabled
# at runtime. Without this, we'll be missing static assets and Django will 500.
# Specificially: django.contrb.admin is added to INSTALLED_APPS in CMS mode
# (WAGTAIL_ENABLE_ADMIN) which is needed for django-rq's management UI and the
# main Django Admin; ENABLE_DJANGO_PATTERN_LIBRARY is needed for django-pattern-library


if [[ "$1" == "--nolink" ]]; then
    WAGTAIL_ENABLE_ADMIN=True ENABLE_DJANGO_PATTERN_LIBRARY=True python manage.py collectstatic --noinput -v 0
else
    WAGTAIL_ENABLE_ADMIN=True ENABLE_DJANGO_PATTERN_LIBRARY=True python manage.py collectstatic -l --noinput -v 0
    docker/bin/softlinkstatic.py
fi
