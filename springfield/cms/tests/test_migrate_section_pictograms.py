# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management import call_command

import pytest
from PIL import Image as PILImage
from wagtail.models import Revision

from springfield.cms.management.commands.migrate_section_pictograms import set_section_pictograms
from springfield.cms.models import FreeFormPage2026, SpringfieldImage

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def make_image(title):
    """Create a SpringfieldImage with a real file, so width and height are populated."""
    buffer = BytesIO()
    PILImage.new("RGB", (100, 100), (117, 79, 224)).save(buffer, format="PNG")
    buffer.seek(0)
    return SpringfieldImage.objects.create(title=title, is_decorative=True, file=ContentFile(buffer.read(), f"{title}.png"))


def get_anchored_section(block_id, anchor_id, pictogram=None):
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": anchor_id},
            "pictogram": pictogram,
            "heading": {"superheading_text": "", "heading_text": f'<p data-block-key="{block_id}">{anchor_id}</p>', "subheading_text": ""},
            "content": [],
            "cta": [],
        },
        "id": block_id,
    }


@pytest.fixture
def anchored_page(minimal_site):
    page = FreeFormPage2026(title="Enterprise", slug="enterprise-pictograms", theme="enterprise", show_pre_footer=False)
    minimal_site.root_page.add_child(instance=page)
    page.content = [
        get_anchored_section("pic00001-0000-0000-0000-000000000001", "sovereignty"),
        get_anchored_section("pic00002-0000-0000-0000-000000000002", "overview"),
    ]
    page.save_revision().publish()
    return page


@pytest.mark.django_db
def test_command_sets_pictograms_on_anchored_sections(anchored_page):
    # The sections do not currently have a pictogram.
    assert [section["value"]["pictogram"] for section in anchored_page.content.raw_data] == [None, None], (
        "Both sections must start without a pictogram, or the assertions below would hold whether or not the command ran"
    )
    assert not SpringfieldImage.objects.exists(), "The command creates the image it assigns, so none may exist beforehand"

    call_command("migrate_section_pictograms")

    anchored_page.refresh_from_db()
    sections = anchored_page.content.raw_data
    sovereignty = SpringfieldImage.objects.get(title="Sovereignty pictogram")
    assert sections[0]["value"]["pictogram"] == sovereignty.pk
    assert sections[1]["value"]["pictogram"] is None, "A section with an unrelated anchor keeps no pictogram"
    assert sovereignty.is_decorative is True


@pytest.mark.django_db
def test_walker_descends_into_a_stream_value_loaded_from_the_database(anchored_page):
    page = FreeFormPage2026.objects.get(pk=anchored_page.pk)

    changed = set_section_pictograms(page.content.raw_data, {"sovereignty": 4242})

    assert changed is True, "raw_data is a RawDataView, not a list. A list-only isinstance check descends into nothing"
    assert page.content.raw_data[0]["value"]["pictogram"] == 4242


@pytest.mark.django_db
def test_command_is_idempotent(anchored_page, capsys):
    call_command("migrate_section_pictograms")
    first_pass = SpringfieldImage.objects.count()
    capsys.readouterr()

    call_command("migrate_section_pictograms")

    second_output = capsys.readouterr().out
    assert SpringfieldImage.objects.count() == first_pass, "A second run should not create duplicate image records"
    assert "0 pages updated" in second_output, "The image count alone passes even when the walk never runs, so assert the content half too"


@pytest.mark.django_db
def test_command_leaves_an_existing_pictogram_alone(minimal_site):
    existing = make_image("Chosen by an editor")
    page = FreeFormPage2026(title="Enterprise", slug="enterprise-existing", theme="enterprise", show_pre_footer=False)
    minimal_site.root_page.add_child(instance=page)
    page.content = [get_anchored_section("pic00003-0000-0000-0000-000000000003", "sovereignty", pictogram=existing.pk)]
    page.save_revision().publish()

    call_command("migrate_section_pictograms")

    page.refresh_from_db()
    assert page.content.raw_data[0]["value"]["pictogram"] == existing.pk


@pytest.mark.django_db
def test_command_updates_revisions(anchored_page):
    call_command("migrate_section_pictograms")

    sovereignty = SpringfieldImage.objects.get(title="Sovereignty pictogram")
    # Read the revision back from the database rather than through the page's cached
    # `latest_revision` relation, which still holds the pre-command copy in memory.
    revision = Revision.objects.get(pk=anchored_page.get_latest_revision().pk)
    revision_content = json.loads(revision.content["content"])
    assert revision_content[0]["value"]["pictogram"] == sovereignty.pk, (
        "The editor's draft must agree with the live page, or opening it would revert the migration"
    )


@pytest.mark.django_db
def test_dry_run_writes_nothing_but_still_reports(anchored_page, capsys):
    call_command("migrate_section_pictograms", "--dry-run")

    anchored_page.refresh_from_db()
    assert anchored_page.content.raw_data[0]["value"]["pictogram"] is None
    assert SpringfieldImage.objects.count() == 0

    output = capsys.readouterr().out
    assert "1 pages would be updated" in output, "A dry run must predict the count the real run will report"
