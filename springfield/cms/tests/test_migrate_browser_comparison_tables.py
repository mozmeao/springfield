# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

import pytest
from wagtail.models import Page, Revision

from springfield.cms.blocks import TabBlock
from springfield.cms.management.commands.migrate_browser_comparison_tables import (
    BROWSER_TABLE_TYPE,
    convert_browser_comparison_tables,
    count_orphaned_optional_content,
)
from springfield.cms.models import FreeFormPage2026, ReferralGetFirefoxPage


def comparison_table(variant=None, block_id="ctbl0001-0000-0000-0000-000000000001"):
    """A minimal stored comparison_table block, optionally carrying the removed variant key."""
    value = {
        "highlighted_column": 2,
        "mobile_behavior": "stacked",
        "header_row": [],
        "content_rows": [],
    }
    if variant is not None:
        value["variant"] = variant
    return {"type": "comparison_table", "id": block_id, "value": value}


def table_with_optional_content(variant=None, block_id="ctbl0001-0000-0000-0000-000000000001"):
    """A stored table whose one body cell has a result instead of plain text."""
    block = comparison_table(variant=variant, block_id=block_id)
    block["value"]["content_rows"] = [
        {
            "type": "item",
            "id": "r0",
            "value": {
                "cells": [
                    {
                        "type": "item",
                        "id": "r0c0",
                        "value": {
                            "content": "",
                            "optional_content": [{"type": "comparison_result", "id": "r0c0-oc", "value": {"result": "yes", "label": ""}}],
                            "column_span": 1,
                        },
                    }
                ]
            },
        }
    ]
    return block


def test_browser_variant_becomes_its_own_block_type():
    block = comparison_table(variant="browser-comparison")

    assert convert_browser_comparison_tables(block) is True
    assert block["type"] == "browser_comparison_table"
    assert "variant" not in block["value"]


def test_default_variant_keeps_its_block_type_and_loses_the_stale_key():
    block = comparison_table(variant="default")

    assert convert_browser_comparison_tables(block) is True
    assert block["type"] == "comparison_table"
    assert "variant" not in block["value"]


def test_table_saved_without_a_variant_key_is_left_alone():
    block = comparison_table()

    assert convert_browser_comparison_tables(block) is False
    assert block == comparison_table()


def test_conversion_is_idempotent():
    block = comparison_table(variant="browser-comparison")
    convert_browser_comparison_tables(block)
    converted = json.loads(json.dumps(block))

    assert convert_browser_comparison_tables(block) is False
    assert block == converted


def test_tables_nested_in_a_section_are_converted():
    section = {
        "type": "section",
        "id": "sec1",
        "value": {"content": [comparison_table(variant="browser-comparison"), comparison_table(variant="default", block_id="ctbl2")]},
    }

    assert convert_browser_comparison_tables([section]) is True
    converted, untouched = section["value"]["content"]
    assert converted["type"] == "browser_comparison_table"
    assert untouched["type"] == "comparison_table"


def showcase_with_tab(tab):
    return {
        "type": "showcase",
        "id": "sc1",
        "value": {"media": [{"type": "tabs", "id": "tabs1", "value": {"tabs": [tab]}}]},
    }


def test_a_tabs_table_moves_to_the_field_that_accepts_its_new_type():
    """Each of a tab's table fields accepts one block type, so the block has to move."""
    showcase = showcase_with_tab({"tab_name": "Firefox", "comparison_table": [comparison_table(variant="browser-comparison")]})

    assert convert_browser_comparison_tables([showcase]) is True

    tab = showcase["value"]["media"][0]["value"]["tabs"][0]
    assert tab["comparison_table"] == []
    assert tab["browser_comparison_table"][0]["type"] == "browser_comparison_table"


def test_a_tabs_default_table_stays_where_it_is():
    showcase = showcase_with_tab({"tab_name": "Firefox", "comparison_table": [comparison_table(variant="default")]})

    assert convert_browser_comparison_tables([showcase]) is True

    tab = showcase["value"]["media"][0]["value"]["tabs"][0]
    assert tab["comparison_table"][0]["type"] == "comparison_table"
    assert "variant" not in tab["comparison_table"][0]["value"]
    assert BROWSER_TABLE_TYPE not in tab


def test_a_converted_tab_table_survives_being_loaded_by_the_block():
    """Wagtail discards a StreamBlock child whose type the block does not define."""
    tab = {"tab_name": "Firefox", "comparison_table": [comparison_table(variant="browser-comparison")]}
    convert_browser_comparison_tables([showcase_with_tab(tab)])

    value = TabBlock().to_python(tab)

    assert len(value["browser_comparison_table"]) == 1
    assert len(value["comparison_table"]) == 0


def test_blocks_that_are_not_comparison_tables_are_untouched():
    intro = {"type": "intro", "id": "in1", "value": {"heading": "Compare browsers"}}

    assert convert_browser_comparison_tables([intro]) is False


def test_optional_content_left_on_a_comparison_table_is_counted():
    assert count_orphaned_optional_content(table_with_optional_content()) == 1


def test_a_table_of_plain_text_cells_has_nothing_to_report():
    assert count_orphaned_optional_content(comparison_table()) == 0


def run_command(**kwargs):
    out = StringIO()
    call_command("migrate_browser_comparison_tables", stdout=out, **kwargs)
    return out.getvalue()


def make_page(content, slug):
    parent = Page.objects.get(slug="home")
    page = FreeFormPage2026(slug=slug, title="Browser comparison migration test page")
    parent.add_child(instance=page)
    page.content = content
    page.save_revision().publish()
    return page


def make_referral_page(upper_content, slug):
    """A page whose showcase allows tabs, which is where a table can go missing.

    Writes the StreamField JSON straight to the row: assigning through the field would
    re-serialize it from the bound blocks and drop the variant key this test needs.
    """
    parent = Page.objects.get(slug="home")
    page = ReferralGetFirefoxPage(slug=slug, title="Browser comparison migration test referral page")
    parent.add_child(instance=page)
    ReferralGetFirefoxPage.objects.filter(pk=page.pk).update(upper_content=json.dumps(upper_content))
    return ReferralGetFirefoxPage.objects.get(pk=page.pk)


def stored_tables(page):
    page.refresh_from_db()
    return list(page.content.raw_data)


@pytest.mark.django_db
class TestMigrateBrowserComparisonTablesCommand:
    def test_page_table_is_retyped(self):
        page = make_page([comparison_table(variant="browser-comparison")], slug="bctbl-retype")

        run_command()

        assert stored_tables(page)[0]["type"] == "browser_comparison_table"

    def test_page_without_the_variant_is_left_alone(self):
        page = make_page([comparison_table()], slug="bctbl-untouched")

        run_command()

        assert stored_tables(page) == [comparison_table()]

    def test_dry_run_makes_no_changes(self):
        page = make_page([comparison_table(variant="browser-comparison")], slug="bctbl-dry-run")

        output = run_command(dry_run=True)

        assert "DRY RUN" in output
        assert stored_tables(page)[0]["type"] == "comparison_table"

    def test_a_table_inside_a_tab_survives_the_migration(self):
        """The tab path is the one that silently loses the block if it is only retyped."""
        page = make_referral_page(
            [
                {
                    "type": "showcase",
                    "id": "sc1",
                    "value": {
                        "media": [
                            {
                                "type": "tabs",
                                "id": "tabs1",
                                "value": {
                                    "section_id": "hub",
                                    "tabs": [{"tab_name": "Firefox", "comparison_table": [comparison_table(variant="browser-comparison")]}],
                                },
                            }
                        ]
                    },
                }
            ],
            slug="bctbl-in-tab",
        )

        run_command()
        page.refresh_from_db()

        tab = page.upper_content[0].value["media"][0].value["tabs"][0]
        assert len(tab["browser_comparison_table"]) == 1
        assert len(tab["comparison_table"]) == 0

    def test_optional_content_the_comparison_table_can_no_longer_render_is_reported(self):
        page = make_page([table_with_optional_content()], slug="bctbl-orphaned")

        output = run_command()

        assert f"pk={page.pk}: 1 comparison table cell(s) hold optional content" in output

    def test_a_retyped_table_keeps_its_optional_content_unreported(self):
        """The browser comparison table still renders it, so there is nothing to warn about."""
        page = make_page([table_with_optional_content(variant="browser-comparison")], slug="bctbl-kept")

        output = run_command()

        assert stored_tables(page)[0]["type"] == BROWSER_TABLE_TYPE
        assert "hold optional content" not in output

    def test_revision_is_also_converted(self):
        page = make_page([comparison_table(variant="browser-comparison")], slug="bctbl-revision")

        run_command()

        content_type = ContentType.objects.get_for_model(FreeFormPage2026)
        revision = Revision.objects.filter(content_type=content_type, object_id=str(page.pk)).order_by("created_at").first()
        assert json.loads(revision.content["content"])[0]["type"] == "browser_comparison_table"
