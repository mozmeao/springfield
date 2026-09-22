# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib
import json

from django.apps import apps
from django.conf import settings

import pytest
from wagtail.models import Locale, Site

from springfield.cms.models.images import SpringfieldImage
from springfield.cms.models.pages import ArticleDetailPage
from springfield.cms.tests.factories import ArticleDetailPageFactory

backfill_migration = importlib.import_module("springfield.cms.migrations.0158_backfill_image_alt_text")
backfill_stream_alt_text = backfill_migration.backfill_stream_alt_text


def test_backfill_fills_a_blank_alt_from_the_image_description():
    stream_data = [
        {
            "type": "icon_list_with_image",
            "id": "aaa",
            "value": {"image": settings.PLACEHOLDER_IMAGE_ID, "image_alt": "", "list_items": []},
        }
    ]
    assert backfill_stream_alt_text(stream_data, descriptions_by_image_id={settings.PLACEHOLDER_IMAGE_ID: "A purple fox"}) == [
        {
            "type": "icon_list_with_image",
            "id": "aaa",
            "value": {"image": settings.PLACEHOLDER_IMAGE_ID, "image_alt": "A purple fox", "list_items": []},
        }
    ]


def test_backfill_leaves_a_filled_alt_alone():
    stream_data = [
        {
            "type": "icon_list_with_image",
            "id": "aaa",
            "value": {"image": settings.PLACEHOLDER_IMAGE_ID, "image_alt": "An editor wrote this", "list_items": []},
        }
    ]
    backfilled = backfill_stream_alt_text(stream_data, descriptions_by_image_id={settings.PLACEHOLDER_IMAGE_ID: "A purple fox"})
    assert backfilled[0]["value"]["image_alt"] == "An editor wrote this"


def test_backfill_leaves_a_decorative_image_blank():
    stream_data = [
        {
            "type": "icon_list_with_image",
            "id": "aaa",
            "value": {"image": settings.PLACEHOLDER_IMAGE_ID, "image_alt": "", "list_items": []},
        }
    ]
    assert backfill_stream_alt_text(stream_data, descriptions_by_image_id={})[0]["value"]["image_alt"] == ""


def test_backfill_renames_the_comparison_header_alt_key():
    stream_data = [
        {
            "type": "browser_comparison_table",
            "id": "aaa",
            "value": {
                "header_row": [
                    {
                        "type": "image_header",
                        "id": "bbb",
                        "value": {"image": settings.PLACEHOLDER_IMAGE_ID, "alt": "Firefox logo", "label": "Firefox"},
                    }
                ]
            },
        }
    ]
    header = backfill_stream_alt_text(stream_data, descriptions_by_image_id={})[0]["value"]["header_row"][0]["value"]
    assert header["image_alt"] == "Firefox logo"
    assert "alt" not in header


def test_backfill_fills_a_nested_image_block():
    stream_data = [
        {
            "type": "image_caption",
            "id": "aaa",
            "value": {
                "caption": "",
                "image": {"image": settings.PLACEHOLDER_IMAGE_ID, "settings": {"mobile_image": None, "dark_mode_image": None}},
            },
        }
    ]
    image = backfill_stream_alt_text(stream_data, descriptions_by_image_id={settings.PLACEHOLDER_IMAGE_ID: "A purple fox"})[0]["value"]["image"]
    assert image["image_alt"] == "A purple fox"


def test_backfill_leaves_images_without_an_alt_field_untouched():
    """Badge artwork and the dark mode and mobile variants of an image have no alt field of their own."""
    stream_data = [
        {
            "type": "badge",
            "id": "aaa",
            "value": {"image": settings.PLACEHOLDER_IMAGE_ID, "number": 1, "singular_label": "person", "plural_label": "people"},
        },
        {
            "type": "image",
            "id": "bbb",
            "value": {
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "settings": {"mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID, "dark_mode_image": None},
            },
        },
    ]
    backfilled = backfill_stream_alt_text(
        stream_data,
        descriptions_by_image_id={settings.PLACEHOLDER_IMAGE_ID: "A purple fox", settings.PLACEHOLDER_MOBILE_IMAGE_ID: "A purple fox on a phone"},
    )
    assert "image_alt" not in backfilled[0]["value"]
    assert "mobile_image_alt" not in backfilled[1]["value"]["settings"]


def comparison_table_with_image_header(image_id):
    """A stored table whose header still carries the alt key that became image_alt."""
    return [
        {
            "type": "browser_comparison_table",
            "id": "cccc0001-0000-0000-0000-000000000001",
            "value": {
                "header_row": [
                    {
                        "type": "image_header",
                        "id": "cccc0002-0000-0000-0000-000000000002",
                        "value": {"image": image_id, "alt": "", "label": "Firefox", "dark_mode_image": None},
                    }
                ],
                "content_rows": [],
            },
        }
    ]


@pytest.mark.django_db
def test_backfill_fills_source_locale_objects_and_their_revisions(monkeypatch, placeholder_images):
    """The whole backfill: source locale only, revision JSON strings included, editor text kept."""
    monkeypatch.setattr(backfill_migration, "is_skipped_environment", lambda: False)

    image = placeholder_images[0]
    SpringfieldImage.objects.filter(pk=image.pk).update(description="A purple fox")
    root_page = Site.objects.get(is_default_site=True).root_page
    french_locale, _ = Locale.objects.get_or_create(language_code="fr")

    english_page = ArticleDetailPageFactory(
        parent=root_page,
        slug="english-article",
        featured_image=image,
        content=comparison_table_with_image_header(image.pk),
    )
    edited_page = ArticleDetailPageFactory(parent=root_page, slug="edited-article", featured_image=image, featured_image_alt="An editor wrote this")
    french_page = ArticleDetailPageFactory(parent=root_page, slug="french-article", locale=french_locale, featured_image=image)
    # Content saved before the alt fields existed has them blank, which page validation now refuses.
    ArticleDetailPage.objects.filter(pk__in=(english_page.pk, french_page.pk)).update(featured_image_alt="")
    english_page.refresh_from_db()
    revision = english_page.save_revision(clean=False)

    backfill_migration.backfill_alt_text(apps, "cms")

    english_page.refresh_from_db()
    edited_page.refresh_from_db()
    french_page.refresh_from_db()
    revision.refresh_from_db()

    assert english_page.featured_image_alt == "A purple fox"
    assert edited_page.featured_image_alt == "An editor wrote this"
    assert french_page.featured_image_alt == ""

    header = list(english_page.content.raw_data)[0]["value"]["header_row"][0]["value"]
    assert header["image_alt"] == "A purple fox"
    assert "alt" not in header

    assert revision.content["featured_image_alt"] == "A purple fox"
    revised_header = json.loads(revision.content["content"])[0]["value"]["header_row"][0]["value"]
    assert revised_header["image_alt"] == "A purple fox"
    assert "alt" not in revised_header
