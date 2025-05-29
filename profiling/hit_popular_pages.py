# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Request a selection of pages that are populat on www.m.o from your local
runserver, so  that django-silk can capture performance info on them.

Usage:

    1. In your .env set ENABLE_DJANGO_SILK=True
    2. Start your runserver on port 8000
    3. python profiling/hit_popular_pages.py
    3. View results at http://localhost:8000/silk/

"""

import sys
import time

import requests

paths = [
    "/en-US/",
    "/en-US/121.0/system-requirements/",
    "/en-US/download/all/",
    "/en-US/android/124.0/releasenotes/",
    "/en-US/channel/desktop/",
    "/en-US/channel/desktop/?reason=manual-update",
    "/en-US/channel/desktop/developer/",
    "/en-US/download/",
    "/en-US/thanks/",
    "/en-US/thanks/?s=direct",
    "/en-US/browsers/enterprise/",
    "/en-US/features/",
    "/en-US/download/installer-help/?channel=release&installer_lang=en-US",
    "/en-US/releases/",
    "/en-US/default/thanks/",
]


def _log(*args):
    sys.stdout.write("\n".join(args))


def hit_pages(paths, times=3):
    _base_url = "http://localhost:8000"

    for path in paths:
        for _ in range(times):
            time.sleep(0.5)
            url = f"{_base_url}{path}"
            requests.get(url)

    _log("All done")


if __name__ == "__main__":
    hit_pages(paths)
