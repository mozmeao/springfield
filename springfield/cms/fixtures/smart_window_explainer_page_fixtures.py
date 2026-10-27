# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import animation_block, rich_text, smart_window_instructions
from springfield.cms.models.pages import SmartWindowExplainerPage


def get_smart_window_explainer_intro() -> dict:
    return {
        "type": "intro",
        "value": {
            "settings": {"layout": "right", "full_width": False, "slim": False, "anchor_id": ""},
            "media": [],
            "heading": {
                "superheading_text": '<p data-block-key="swepi1s">Lorem Ipsum</p>',
                "heading_text": '<p data-block-key="swepi1h">Lorem ipsum dolor sit amet</p>',
                "subheading_text": '<p data-block-key="swepi1b">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor '
                "incididunt ut labore et dolore magna aliqua.</p>",
            },
            "content": [],
        },
        "id": "swepi01-0000-0000-0000-000000000001",
    }


def get_smart_window_explainer_content() -> list[dict]:
    placeholder_images = get_placeholder_images()
    img = placeholder_images.image.id
    return [
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True, "narrow": False},
                "media": [animation_block(poster_image_id=img, block_id="swepmc01-0000-0000-0000-000000000010")],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="swepmc1h">Lorem ipsum dolor sit amet</p>',
                    "subheading_text": "",
                },
                "content": [
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc1c1">Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>',
                        block_id="swepmc01-0000-0000-0000-000000000011",
                    ),
                    smart_window_instructions(
                        typewriter_text="lorem ipsum dolor sit amet",
                        instructions_text="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor.",
                        block_id="swepmc01-0000-0000-0000-000000000012",
                    ),
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc1c2">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.</p>',
                        block_id="swepmc01-0000-0000-0000-000000000013",
                    ),
                ],
            },
            "id": "swepmc01-0000-0000-0000-000000000001",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False, "narrow": False},
                "media": [animation_block(poster_image_id=img, block_id="swepmc01-0000-0000-0000-000000000020")],
                "heading": {
                    "superheading_text": '<p data-block-key="swepmc2e">Consectetur</p>',
                    "heading_text": '<p data-block-key="swepmc2h">Sed do eiusmod tempor incididunt</p>',
                    "subheading_text": "",
                },
                "content": [
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc2c1">Duis aute irure dolor in reprehenderit in voluptate velit esse '
                        "cillum dolore eu fugiat nulla pariatur.</p>",
                        block_id="swepmc01-0000-0000-0000-000000000021",
                    ),
                    smart_window_instructions(
                        typewriter_text="sed do eiusmod tempor incididunt",
                        instructions_text="Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua ut enim.",
                        block_id="swepmc01-0000-0000-0000-000000000022",
                    ),
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc2c2">Excepteur sint occaecat cupidatat non proident.</p>',
                        block_id="swepmc01-0000-0000-0000-000000000023",
                    ),
                ],
            },
            "id": "swepmc01-0000-0000-0000-000000000002",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True, "narrow": False},
                "media": [animation_block(poster_image_id=img, block_id="swepmc01-0000-0000-0000-000000000030")],
                "heading": {
                    "superheading_text": '<p data-block-key="swepmc3e">Adipiscing</p>',
                    "heading_text": '<p data-block-key="swepmc3h">Quis nostrud exercitation ullamco</p>',
                    "subheading_text": "",
                },
                "content": [
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc3c1">Sunt in culpa qui officia deserunt mollit anim id est laborum.</p>',
                        block_id="swepmc01-0000-0000-0000-000000000031",
                    ),
                    smart_window_instructions(
                        typewriter_text="ut labore et dolore magna aliqua ut enim ad minim",
                        instructions_text="Ut labore et dolore magna aliqua enim ad minim veniam quis nostrud exercitation.",
                        block_id="swepmc01-0000-0000-0000-000000000032",
                    ),
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc3c2">Lorem ipsum dolor sit amet, consectetur '
                        "adipiscing elit, sed do eiusmod tempor incididunt "
                        "ut labore et dolore magna aliqua ut enim ad minim.</p>",
                        block_id="swepmc01-0000-0000-0000-000000000033",
                    ),
                ],
            },
            "id": "swepmc01-0000-0000-0000-000000000003",
        },
    ]


def get_smart_window_explainer_test_page() -> SmartWindowExplainerPage:
    get_placeholder_images()
    index_page = get_flare_pages_docs_page()

    slug = "test-smart-window-explainer"
    page = get_or_create_page(
        SmartWindowExplainerPage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Smart Window Explainer Page",
        },
    )

    page.upper_content = [get_smart_window_explainer_intro()]
    page.content = get_smart_window_explainer_content()
    page.save_revision().publish()
    return page
