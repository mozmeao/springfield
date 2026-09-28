# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from io import StringIO

from django.core.management import call_command

import pytest
from bs4 import BeautifulSoup

from springfield.cms.management.commands.migrate_enterprise_download_resources import (
    HEADING,
    fill_enterprise_download_blocks,
)
from springfield.cms.models import FreeFormPage2026


def legacy_block(block_id="edl00001-0000-0000-0000-000000000001"):
    """The stored shape of every Enterprise Download block saved before it had fields."""
    return {"type": "enterprise_download", "value": None, "id": block_id}


def make_page(index_page, blocks, slug="enterprise-download-migration"):
    page = FreeFormPage2026(title="Enterprise Download Migration", slug=slug, content=blocks)
    index_page.add_child(instance=page)
    page.save_revision().publish()
    return page


def test_fill_replaces_a_null_value_with_heading_and_links():
    data = [legacy_block()]

    assert fill_enterprise_download_blocks(data) is True

    value = data[0]["value"]
    assert value["heading"] == HEADING
    assert value["settings"] == {"center_content": True}
    links = BeautifulSoup(value["rich_text"], "html.parser").find_all("a")
    assert [link["href"] for link in links] == [
        "https://firefox-admin-docs.mozilla.org/",
        "https://github.com/mozilla/policy-templates/releases",
        "https://support.mozilla.org/products/firefox-enterprise/whats-new-firefox-enterprise/",
    ]
    assert all(link["uid"] for link in links)


def test_fill_gives_every_block_its_own_link_uids():
    data = [legacy_block("edl00001-0000-0000-0000-000000000001"), legacy_block("edl00002-0000-0000-0000-000000000002")]

    fill_enterprise_download_blocks(data)

    uids = [[link["uid"] for link in BeautifulSoup(block["value"]["rich_text"], "html.parser").find_all("a")] for block in data]
    assert uids[0] != uids[1]


def test_fill_leaves_a_block_an_author_has_already_edited_alone():
    edited = {
        "type": "enterprise_download",
        "value": {"settings": {"center_content": False}, "heading": "<p>Downloads</p>", "rich_text": "<ul><li>Mine</li></ul>"},
        "id": "edl00003-0000-0000-0000-000000000003",
    }
    data = [edited]

    assert fill_enterprise_download_blocks(data) is False
    assert data[0]["value"]["heading"] == "<p>Downloads</p>"


def test_fill_reaches_a_block_nested_inside_a_section():
    data = [
        {
            "type": "section",
            "id": "sec00001-0000-0000-0000-000000000001",
            "value": {"content": [legacy_block()]},
        }
    ]

    assert fill_enterprise_download_blocks(data) is True
    assert data[0]["value"]["content"][0]["value"]["heading"] == HEADING


@pytest.mark.django_db
def test_command_fills_pages(index_page):
    page = make_page(index_page, [legacy_block()])

    call_command("migrate_enterprise_download_resources", stdout=StringIO())

    page.refresh_from_db()
    assert page.content.raw_data[0]["value"]["heading"] == HEADING


@pytest.mark.django_db
def test_command_fills_revisions(index_page):
    page = make_page(index_page, [legacy_block()])

    call_command("migrate_enterprise_download_resources", stdout=StringIO())

    revision = page.revisions.order_by("-created_at").first()
    stored = json.loads(revision.content["content"])
    assert stored[0]["value"]["heading"] == HEADING


@pytest.mark.django_db
def test_dry_run_writes_nothing_but_still_reports(index_page):
    page = make_page(index_page, [legacy_block()])
    output = StringIO()

    call_command("migrate_enterprise_download_resources", "--dry-run", stdout=output)

    page.refresh_from_db()
    assert page.content.raw_data[0]["value"] is None
    assert "1 pages would be updated" in output.getvalue()


@pytest.mark.django_db
def test_command_is_idempotent(index_page):
    page = make_page(index_page, [legacy_block()])
    call_command("migrate_enterprise_download_resources", stdout=StringIO())
    page.refresh_from_db()
    first = page.content.raw_data[0]["value"]["rich_text"]

    call_command("migrate_enterprise_download_resources", stdout=StringIO())

    page.refresh_from_db()
    assert page.content.raw_data[0]["value"]["rich_text"] == first
