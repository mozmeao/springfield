# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Request a selection of pages that are populat on www.f.c from your local
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
    "/en-US/thanks/",
    "/en-US/thanks/?s=direct",
    "/pt-BR/thanks/",
    "/zh-TW/download/all/",
    "/en-US/download/all/",
    "/en-US/firefox/123.0/system-requirements/",
    "/en-US/firefox/android/123.0/releasenotes/",
    "/en-US/channel/desktop/",
    "/en-US/channel/desktop/?reason=manual-update",
    "/en-US/channel/desktop/developer/",
    "/de/",
    "/sv-SE/browsers/mobile/get-app/",
    "/en-US/browsers/mobile/get-app/",
    "/en-US/browsers/mobile/android/",
    "/en-US/browsers/mobile/focus/",
    "/en-US/browsers/mobile/",
    "/en-US/browsers/desktop/windows/",
    "/en-US/browsers/desktop/linux/",
    "/en-US/browsers/desktop/mac/",
    "/en-US/browsers/desktop/chromebook/",
    "/en-US/browsers/desktop/",
    "/en-US/browsers/enterprise/",
    "/en-US/browsers/enterprise/?reason=manual-update",
    "/en-US/download/installer-help/?channel=release&installer_lang=en-US",
    "/en-US/releases/",
    "/en-US/features/",
    "/ja/features/",
    "/en-US/landing/set-as-default/thanks/",
    "/en-US/more/what-is-a-browser/",
    "/en-US/more/windows-64-bit/",
    "/en-US/newsletter/",
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
