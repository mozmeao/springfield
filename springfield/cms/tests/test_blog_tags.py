# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import IntegrityError

import pytest
from wagtail.models import Locale

from springfield.cms.models import BlogTag

pytestmark = [pytest.mark.django_db]


def test_same_tag_name_allowed_in_two_locales():
    """taggit's TagBase makes name and slug globally unique. BlogTag scopes both to the
    locale so one concept can exist once per language — the whole point of keeping tags
    translatable."""
    fr_locale = Locale.objects.get_or_create(language_code="fr")[0]

    en_tag = BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())
    fr_tag = BlogTag.objects.create(name="Privacy", slug="privacy", locale=fr_locale)

    assert en_tag.pk != fr_tag.pk


def test_duplicate_tag_name_in_one_locale_is_rejected():
    """Name uniqueness within a locale is what makes name-based tag resolution
    deterministic, so it must be enforced by the database, not only by the form."""
    BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())

    with pytest.raises(IntegrityError):
        BlogTag.objects.create(name="Privacy", slug="privacy-again", locale=Locale.get_default())
