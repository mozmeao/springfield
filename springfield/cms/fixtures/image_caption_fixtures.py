# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import (
    get_flare_blocks_docs_page,
    get_image_variants,
    get_or_create_page,
    get_placeholder_images,
    with_fresh_ids,
)
from springfield.cms.fixtures.block_factories import link_value
from springfield.cms.models import FreeFormPage2026


def image_caption(block_id, layout, caption="", link=None):
    return {
        "type": "image_caption",
        "value": {
            "image": get_image_variants(),
            "caption": f'<p data-block-key="{block_id}c">{caption}</p>' if caption else "",
            "link": link if link is not None else link_value(link_to=""),
            "layout": layout,
        },
        "id": block_id,
    }


def get_image_caption_variants() -> list[dict]:
    return [
        image_caption(
            "2026ic01-0000-0000-0000-000000000001",
            layout="default",
            caption="Default layout: the image keeps its natural width and the caption sits centered below it. Use this for most inline images.",
            link=link_value(custom_url="https://www.mozilla.org/"),
        ),
        image_caption(
            "2026ic01-0000-0000-0000-000000000002",
            layout="default",
            caption="",
        ),
        image_caption(
            "2026ic01-0000-0000-0000-000000000003",
            layout="expanded",
            caption="Expanded layout: the image grows wider than the text column to draw more attention.",
        ),
        image_caption(
            "2026ic01-0000-0000-0000-000000000004",
            layout="full",
            caption="Full-width layout: the image spans the whole container edge to edge.",
        ),
    ]


def get_image_caption_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-image-caption",
        parent=index_page,
        defaults={"title": "Image + Caption"},
    )

    variants = with_fresh_ids(get_image_caption_variants())
    page.content = variants
    page.docs = (
        "<p>The Image + Caption block places one image with an optional caption underneath. "
        "Pick the layout to control how wide the image gets: <b>Default</b> keeps it inline with the text, "
        "<b>Expanded</b> makes it wider than the text column, and <b>Full Width</b> spans the whole container.</p>"
        "<p>Add a link to make the image clickable, and leave the caption empty when the image speaks for itself. "
        "The caption is the second sample above, with no text below the image.</p>"
    )
    page.save_revision().publish()
    return page
