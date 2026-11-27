# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib

from django.apps import apps as django_apps

import pytest
from taggit.models import Tag

pytestmark = pytest.mark.django_db

migration = importlib.import_module("springfield.cms.migrations.0170_tag_image_aspect_ratios")


def test_backfill_tags_existing_images(make_image):
    image = make_image()

    migration.tag_aspect_ratios(django_apps, None)

    assert list(image.tags.names()) == ["4:3"]


def test_backfill_is_idempotent_and_survives_a_slug_clash(make_image):
    Tag.objects.create(name="Forty three", slug="43")
    image = make_image()

    migration.tag_aspect_ratios(django_apps, None)
    migration.tag_aspect_ratios(django_apps, None)

    assert list(image.tags.names()) == ["4:3"]
    assert Tag.objects.get(name="4:3").slug != "43"
