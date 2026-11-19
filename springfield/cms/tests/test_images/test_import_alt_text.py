# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
from io import StringIO

from django.core.management import call_command

import pytest

from springfield.cms.models.images import SpringfieldImage

pytestmark = [pytest.mark.django_db]

COLUMNS = ("image_id", "file", "title", "description", "tags", "is_decorative", "changed_fields")


@pytest.fixture
def write_csv(tmp_path):
    """Write one CSV in the shape the import expects and return its path."""

    def build(*rows):
        path = tmp_path / "image-alt-text.csv"
        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({"tags": "", "is_decorative": "false", **row})
        return path

    return build


def run_import(csv_path, **options):
    """Run the import and return everything it printed."""
    output = StringIO()
    call_command("import_image_alt_text", csv=str(csv_path), stdout=output, **options)
    return output.getvalue()


def test_applies_only_the_fields_named_in_changed_fields(make_image, write_csv):
    image = make_image(title="hero-image.png", description="A hero image")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": "Firefox on a laptop",
            "description": "Rewritten description that must not be applied",
            "changed_fields": "title",
        }
    )

    run_import(csv_path)

    image.refresh_from_db()
    assert image.title == "Firefox on a laptop"
    assert image.description == "A hero image"


def test_applies_the_decorative_flag(make_image, write_csv):
    image = make_image(title="Swirl", description="A purple swirl", is_decorative=False)
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": "Swirl",
            "description": "",
            "is_decorative": "true",
            "changed_fields": "description is_decorative",
        }
    )

    run_import(csv_path)

    image.refresh_from_db()
    assert image.is_decorative is True
    assert image.description == ""


def test_replaces_the_tags_with_the_ones_in_the_row(make_image, write_csv):
    image = make_image()
    image.tags.add("de", "wnp-144")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": image.title,
            "description": image.description,
            "tags": "German, wnp-144",
            "changed_fields": "tags",
        }
    )

    output = run_import(csv_path)

    assert sorted(tag.name for tag in image.tags.all()) == ["German", "wnp-144"]
    assert f"Image {image.pk} tags: ['de', 'wnp-144'] -> ['German', 'wnp-144']" in output


def test_keeps_the_tags_of_a_row_that_does_not_name_them(make_image, write_csv):
    image = make_image(title="hero-image.png")
    image.tags.add("wnp-144")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": "Firefox on a laptop",
            "tags": "",
            "changed_fields": "title",
        }
    )

    run_import(csv_path)

    image.refresh_from_db()
    assert image.title == "Firefox on a laptop"
    assert [tag.name for tag in image.tags.all()] == ["wnp-144"]


def test_leaves_a_row_whose_file_does_not_match_the_image(make_image, write_csv):
    image = make_image(title="Firefox logo")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": "original_images/a-different-image.png",
            "title": "Something else entirely",
            "changed_fields": "title",
        }
    )

    output = run_import(csv_path)

    image.refresh_from_db()
    assert image.title == "Firefox logo"
    assert "1 skipped, file does not match" in output
    assert str(image.pk) in output


def test_leaves_a_row_whose_image_is_missing(write_csv):
    csv_path = write_csv(
        {
            "image_id": 999999,
            "file": "original_images/gone.png",
            "title": "No such image",
            "changed_fields": "title",
        }
    )

    output = run_import(csv_path)

    assert "1 skipped, no such image" in output


def test_dry_run_leaves_every_image_unchanged(make_image, write_csv):
    image = make_image(title="Firefox logo")
    image.tags.add("wnp-144")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": "Firefox on a laptop",
            "tags": "wnp-159",
            "changed_fields": "title tags",
        }
    )

    output = run_import(csv_path, dry_run=True)

    image.refresh_from_db()
    assert image.title == "Firefox logo"
    assert [tag.name for tag in image.tags.all()] == ["wnp-144"]
    assert "1 image to change" in output


def test_a_second_run_changes_nothing(make_image, write_csv):
    image = make_image(title="hero-image.png")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": "Firefox on a laptop",
            "changed_fields": "title",
        }
    )
    run_import(csv_path)

    output = run_import(csv_path)

    assert "0 images changed" in output
    assert "1 already correct" in output


def test_makes_a_changed_title_searchable(make_image, write_csv):
    image = make_image(title="hero-image.png")
    csv_path = write_csv(
        {
            "image_id": image.pk,
            "file": image.file.name,
            "title": "Thunderbolt",
            "changed_fields": "title",
        }
    )

    run_import(csv_path)

    assert [found.pk for found in SpringfieldImage.objects.search("Thunderbolt")] == [image.pk]
