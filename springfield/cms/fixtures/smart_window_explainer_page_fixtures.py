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
                "superheading_text": '<p data-block-key="swepi1s">Smart Window Explainer</p>',
                "heading_text": '<p data-block-key="swepi1h">Show visitors what the Smart Window can do</p>',
                "subheading_text": '<p data-block-key="swepi1b">This page type walks through the Firefox Smart Window one feature at a time, '
                "pairing a short animation with a phrase the visitor can type to follow along.</p>",
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
                    "heading_text": '<p data-block-key="swepmc1h">Each section pairs an animation with an instruction</p>',
                    "subheading_text": "",
                },
                "content": [
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc1c1">A Media + Content block holds the animation. Use the copy above the '
                        "instruction to say what the visitor is about to see.</p>",
                        block_id="swepmc01-0000-0000-0000-000000000011",
                    ),
                    smart_window_instructions(
                        typewriter_text="Summarize this page for me",
                        instructions_text="The Smart Window Instructions block types a phrase one character at a time, then explains what it does.",
                        block_id="swepmc01-0000-0000-0000-000000000012",
                    ),
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc1c2">Close with a line that leads into the next thing the Smart Window can do.</p>',
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
                    "superheading_text": '<p data-block-key="swepmc2e">Media before</p>',
                    "heading_text": '<p data-block-key="swepmc2h">Alternate the media side to keep a rhythm</p>',
                    "subheading_text": "",
                },
                "content": [
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc2c1">Turn off &ldquo;media after&rdquo; to put the animation first. '
                        "Alternating sides down a long explainer keeps it from feeling repetitive.</p>",
                        block_id="swepmc01-0000-0000-0000-000000000021",
                    ),
                    smart_window_instructions(
                        typewriter_text="Compare these two articles",
                        instructions_text="Keep the typed phrase short — it is a prompt the visitor could paste straight into the Smart Window.",
                        block_id="swepmc01-0000-0000-0000-000000000022",
                    ),
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc2c2">Keep each section focused on a single capability so it is easy to scan.</p>',
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
                    "superheading_text": '<p data-block-key="swepmc3e">One idea per section</p>',
                    "heading_text": '<p data-block-key="swepmc3h">End with the payoff</p>',
                    "subheading_text": "",
                },
                "content": [
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc3c1">Finish the explainer with the outcome the visitor gets from the feature.</p>',
                        block_id="swepmc01-0000-0000-0000-000000000031",
                    ),
                    smart_window_instructions(
                        typewriter_text="Draft a reply in my own style",
                        instructions_text="The instruction text can be a full sentence; the typed phrase should stay a short, realistic prompt.",
                        block_id="swepmc01-0000-0000-0000-000000000032",
                    ),
                    rich_text(
                        rich_text_html='<p data-block-key="swepmc3c2">This sample uses placeholder animations and a numbered-grid poster image. '
                        "Swap in the real assets on a production page.</p>",
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
