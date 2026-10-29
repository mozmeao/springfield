# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Isolation fixtures for every test under lib/ and springfield/. They matter most when the
# suite runs in parallel, because each worker runs the tests in a different order from the
# serial run and so inherits different leftover state from its predecessor.

from django.core.cache import cache
from django.utils import translation

import pytest


@pytest.fixture(autouse=True)
def clear_django_cache():
    """Start each test with an empty cache.

    Wagtail keeps the site root paths in the cache and waffle keeps switch state there. A
    test's database rollback does not invalidate either, so without this a later test can
    build URLs from root pages that no longer exist or see switch overrides from an earlier
    test."""
    cache.clear()
    yield


@pytest.fixture(autouse=True)
def reset_active_language():
    """Deactivate whatever language a test left active.

    Requests to locale-prefixed URLs (e.g. /pt-PT/...) call translation.activate() inside
    the URL resolver, and page.localized resolves against the active language."""
    yield
    translation.deactivate()
