# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Isolation fixtures for every test under springfield/. They matter most when the suite runs in
# parallel, because each worker runs the tests in a different order from the serial run and so
# inherits different leftover state from its predecessor.

import shutil
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.urls import clear_url_caches
from django.utils import translation

import pytest

from springfield.cms.fixtures.base_fixtures import (
    PLACEHOLDER_DARK_IMAGE_TITLE,
    PLACEHOLDER_DARK_MOBILE_IMAGE_TITLE,
    PLACEHOLDER_IMAGE_TITLE,
    PLACEHOLDER_MOBILE_IMAGE_TITLE,
)
from springfield.cms.models.images import SpringfieldImage


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
def reset_url_resolvers():
    """Start each test with unpopulated URL resolvers.

    Django caches reversed URLs per language, keyed on its own get_language(). The locale
    prefix in those URLs comes from LocalePrefixPattern, which reads the language through
    lib.l10n_utils.translation instead. A test that mocks django.utils.translation.get_language
    while a URL is reversed fills the cache entry for the real language with the mocked
    language's prefix, and every later test in the process reverses wrong URLs."""
    clear_url_caches()
    yield


@pytest.fixture(autouse=True)
def reset_active_language():
    """Deactivate whatever language a test left active.

    Requests to locale-prefixed URLs (e.g. /pt-PT/...) call translation.activate() inside
    the URL resolver, and page.localized resolves against the active language."""
    yield
    translation.deactivate()


@pytest.fixture(scope="session", autouse=True)
def remove_test_media_root():
    """Delete the temporary MEDIA_ROOT the test settings create, once the run finishes."""
    yield
    shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def skip_placeholder_rendition_pregeneration(request):
    """Save the shared placeholder images without pre-generating their renditions.

    SpringfieldImage.save() builds 14 renditions per image, which is most of the cost of every
    test that uses the placeholders. Rendering an image still creates the renditions it needs,
    but it inserts them during the render. Mark a query-count test that renders a placeholder
    image with `pregenerated_renditions` so it counts only the queries production makes."""
    if request.node.get_closest_marker("pregenerated_renditions"):
        yield
        return

    placeholder_titles = {
        PLACEHOLDER_IMAGE_TITLE,
        PLACEHOLDER_DARK_IMAGE_TITLE,
        PLACEHOLDER_MOBILE_IMAGE_TITLE,
        PLACEHOLDER_DARK_MOBILE_IMAGE_TITLE,
    }
    pre_generate = SpringfieldImage._pre_generate_expected_renditions

    def pre_generate_unless_placeholder(image):
        if image.title not in placeholder_titles:
            pre_generate(image)

    with patch.object(SpringfieldImage, "_pre_generate_expected_renditions", pre_generate_unless_placeholder):
        yield
