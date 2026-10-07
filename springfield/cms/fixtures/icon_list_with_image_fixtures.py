# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import icon_list_item, section
from springfield.cms.models import FreeFormPage2026


def get_icon_list_with_image_variants() -> list[dict]:
    placeholder_images = get_placeholder_images()
    return [
        {
            "type": "icon_list_with_image",
            "value": {
                "image": placeholder_images.image.id,
                "list_items": [
                    icon_list_item(icon="checkmark", text="Block harmful trackers automatically", item_id="il2026i1a"),
                    icon_list_item(icon="lock", text="Keep your passwords safe and synced", item_id="il2026i1b"),
                    icon_list_item(icon="shield", text="Browse without leaving a trace", item_id="il2026i1c"),
                ],
            },
            "id": "2026il01-0000-0000-0000-000000000001",
        },
        {
            "type": "icon_list_with_image",
            "value": {
                "image": placeholder_images.image.id,
                "list_items": [
                    icon_list_item(icon="bookmark", text="Save pages and sync across devices", item_id="il2026i2a"),
                    icon_list_item(icon="history", text="Access your browsing history anywhere", item_id="il2026i2b"),
                    icon_list_item(icon="tab", text="Manage tabs with ease", item_id="il2026i2c"),
                    icon_list_item(icon="extension", text="Add extensions to customize your experience", item_id="il2026i2d"),
                    icon_list_item(icon="themes", text="Personalize with themes", item_id="il2026i2e"),
                ],
            },
            "id": "2026il01-0000-0000-0000-000000000002",
        },
    ]


def get_icon_list_with_image_sections() -> list[dict]:
    variants = get_icon_list_with_image_variants()
    return [
        section(
            heading_text="Icon List with Image - 3 Items",
            subheading_text="The image is displayed alongside a list of icon and text items.",
            content_blocks=[variants[0]],
            section_id="2026ils1-0000-0000-0000-000000000001",
        ),
        section(
            heading_text="Icon List with Image - 5 Items",
            subheading_text="The list can contain any number of items.",
            content_blocks=[variants[1]],
            section_id="2026ils1-0000-0000-0000-000000000002",
        ),
    ]


def get_icon_list_with_image_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-icon-list-with-image"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Icon List with Image",
        },
    )

    sections = get_icon_list_with_image_sections()
    page.upper_content = sections
    page.content = sections
    page.docs = (
        "<p>The Icon List with Image block places a vertical list of icon+text items beside a supporting image. It&rsquo;s well "
        "suited for product walkthroughs, capability checklists, and &lsquo;why us&rsquo; sections that benefit from a single "
        "anchoring visual.</p>"
        "<p>Limit the list to 4&ndash;6 items so column heights stay balanced. Match the image to the list&rsquo;s overall theme &mdash; "
        "abstract or decorative imagery weakens the structure.</p>"
    )
    page.save_revision().publish()
    return page
