# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

import pytest
from taggit.models import Tag, TaggedItem
from wagtail.models import Collection

from springfield.cms.models.images import SpringfieldImage

pytestmark = [pytest.mark.django_db]


def run_normalize(**options):
    """Run the command and return everything it printed."""
    output = StringIO()
    call_command("normalize_image_tags", stdout=output, **options)
    return output.getvalue()


@pytest.mark.parametrize(
    ("old_name", "kept_name"),
    [
        ("french", "French"),
        ("fr", "French"),
        ("FR", "French"),
        ("german", "German"),
        ("de", "German"),
        ("DE", "German"),
        ("pictograms", "pictogram"),
        ("illustration", "Illustration"),
    ],
)
def test_moves_an_old_spelling_onto_the_tag_to_keep(make_image, old_name, kept_name):
    image = make_image()
    image.tags.add(old_name)

    run_normalize()

    assert [tag.name for tag in image.tags.all()] == [kept_name]
    assert not Tag.objects.filter(name=old_name).exists()


def test_leaves_one_tag_on_an_image_that_carries_both_spellings(make_image):
    image = make_image()
    image.tags.add("fr", "French")

    run_normalize()

    assert [tag.name for tag in image.tags.all()] == ["French"]


def test_creates_the_tag_to_keep_when_no_image_has_it_yet(make_image):
    image = make_image()
    image.tags.add("de")

    assert not Tag.objects.filter(name="German").exists()

    run_normalize()

    assert [tag.name for tag in image.tags.all()] == ["German"]


def test_gives_the_surviving_tag_the_slug_the_merge_frees(make_image):
    make_image().tags.add("french")
    make_image().tags.add("French")
    assert Tag.objects.get(name="French").slug == "french_1"

    run_normalize()

    assert Tag.objects.get(name="French").slug == "french"


def test_removes_the_unused_lowercase_illustration_tag(make_image):
    image = make_image()
    image.tags.add("Illustration")
    Tag.objects.create(name="illustration")

    run_normalize()

    assert [tag.name for tag in image.tags.all()] == ["Illustration"]
    assert Tag.objects.get(name="Illustration").slug == "illustration"
    assert not Tag.objects.filter(name="illustration").exists()


def test_deletes_an_unwanted_tag_and_takes_it_off_its_images(make_image):
    image = make_image()
    image.tags.add("test")

    run_normalize()

    assert list(image.tags.all()) == []
    assert not Tag.objects.filter(name="test").exists()


def test_keeps_a_tag_another_model_still_uses(make_image):
    image = make_image()
    image.tags.add("test")
    collection = Collection.get_first_root_node()
    TaggedItem.objects.create(
        tag=Tag.objects.get(name="test"),
        content_type=ContentType.objects.get_for_model(Collection),
        object_id=collection.pk,
    )

    run_normalize()

    assert list(image.tags.all()) == []
    assert Tag.objects.filter(name="test").exists()


def test_dry_run_leaves_every_tag_unchanged(make_image):
    image = make_image()
    image.tags.add("fr")

    output = run_normalize(dry_run=True)

    assert [tag.name for tag in image.tags.all()] == ["fr"]
    assert Tag.objects.filter(name="fr").exists()
    assert not Tag.objects.filter(name="French").exists()
    assert "1 tag to merge" in output


def test_a_second_run_changes_nothing(make_image):
    image = make_image()
    image.tags.add("de")

    # The first run merges tags.
    output = run_normalize()
    assert "1 tags merged" in output

    # The second run does nothing, since the first run already merged tags.
    output = run_normalize()
    assert [tag.name for tag in image.tags.all()] == ["German"]
    assert "0 tags merged" in output
    assert "0 tags deleted" in output


def test_makes_a_merged_tag_searchable(make_image):
    image = make_image()
    image.tags.add("de")

    assert [found.pk for found in SpringfieldImage.objects.search("German")] == []

    run_normalize()

    assert [found.pk for found in SpringfieldImage.objects.search("German")] == [image.pk]
