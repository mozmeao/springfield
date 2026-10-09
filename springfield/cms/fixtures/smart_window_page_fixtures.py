# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_pages_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import ANIMATION_URL, animation_block, heading_value, section, testimonial_card
from springfield.cms.fixtures.smart_window_explainer_page_fixtures import get_smart_window_explainer_test_page
from springfield.cms.models.pages import SmartWindowPage


def get_smart_window_sliding_carousel() -> dict:
    placeholder_images = get_placeholder_images()
    img = placeholder_images.image.id
    dark = placeholder_images.dark_image.id
    slides = [
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Lorem ipsum dolor sit amet",
                    superheading_text="Lorem",
                    subheading_text="Consectetur adipiscing elit, sed do eiusmod tempor.",
                    block_key="swph",
                ),
                "media": [animation_block(poster_image_id=img, block_id="swpsc01-0000-0000-0000-000000000010", show_pause_button=True)],
            },
            "id": "swpsc01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Sed do eiusmod tempor incididunt",
                    superheading_text="Ipsum",
                    subheading_text="Ut labore et dolore magna aliqua.",
                    block_key="swph",
                ),
                "media": [animation_block(poster_image_id=dark, block_id="swpsc01-0000-0000-0000-000000000020", show_pause_button=True)],
            },
            "id": "swpsc01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Quis nostrud exercitation ullamco",
                    superheading_text="Dolor",
                    subheading_text="Duis aute irure dolor in reprehenderit.",
                    block_key="swph",
                ),
                "media": [animation_block(poster_image_id=img, block_id="swpsc01-0000-0000-0000-000000000030", show_pause_button=True)],
            },
            "id": "swpsc01-0000-0000-0000-000000000003",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Ut enim ad minim veniam",
                    superheading_text="Amet",
                    subheading_text="Excepteur sint occaecat cupidatat non proident.",
                    block_key="swph",
                ),
                "media": [animation_block(poster_image_id=dark, block_id="swpsc01-0000-0000-0000-000000000040", show_pause_button=True)],
            },
            "id": "swpsc01-0000-0000-0000-000000000004",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Sunt in culpa qui officia deserunt",
                    superheading_text="Sit",
                    subheading_text="Mollit anim id est laborum.",
                    block_key="swph",
                ),
                "media": [animation_block(poster_image_id=img, block_id="swpsc01-0000-0000-0000-000000000050", show_pause_button=True)],
            },
            "id": "swpsc01-0000-0000-0000-000000000005",
        },
    ]
    return {
        "type": "sliding_carousel",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL},
            "slides": slides,
        },
        "id": "swpsc01-0000-0000-0000-000000000001",
    }


def get_smart_window_line_cards() -> dict:
    return {
        "type": "line_cards",
        "value": {
            "heading": {
                "superheading_text": "",
                "heading_text": "",
                "subheading_text": "",
            },
            "cards": [
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc1s">Lorem</p>',
                        "headline": '<p data-block-key="swplc1h">Lorem ipsum dolor sit amet</p>',
                        "content": '<p data-block-key="swplc1c">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod '
                        "tempor incididunt ut labore.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000001",
                },
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc2s">Ipsum</p>',
                        "headline": '<p data-block-key="swplc2h">Consectetur adipiscing elit</p>',
                        "content": '<p data-block-key="swplc2c">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi '
                        "ut aliquip.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000002",
                },
            ],
        },
        "id": "swplc01-0000-0000-0000-000000000001",
    }


def get_smart_window_illustration_cards() -> dict:
    placeholder_images = get_placeholder_images()
    img = placeholder_images.image.id
    animation_cards = [
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": False, "show_to": SHOW_TO_ALL},
                "media": [
                    {
                        "type": "media",
                        "value": [animation_block(poster_image_id=img, block_id="swpic01-0000-0000-0000-000000000011", show_pause_button=True)],
                        "id": "swpic01-0000-0000-0000-000000000012",
                    }
                ],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": '<p data-block-key="swpic1e">Lorem</p>',
                            "heading_text": '<p data-block-key="swpic1h">Lorem ipsum dolor sit amet</p>',
                            "subheading_text": "",
                        },
                        "id": "swpic01-0000-0000-0000-000000000013",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="swpic1c">Consectetur adipiscing elit.</p>',
                        "id": "swpic01-0000-0000-0000-000000000014",
                    },
                ],
            },
            "id": "swpic01-0000-0000-0000-000000000001",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": False, "show_to": SHOW_TO_ALL},
                "media": [
                    {
                        "type": "media",
                        "value": [animation_block(poster_image_id=img, block_id="swpic01-0000-0000-0000-000000000021", show_pause_button=True)],
                        "id": "swpic01-0000-0000-0000-000000000022",
                    }
                ],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": '<p data-block-key="swpic2e">Ipsum</p>',
                            "heading_text": '<p data-block-key="swpic2h">Sed do eiusmod tempor incididunt</p>',
                            "subheading_text": "",
                        },
                        "id": "swpic01-0000-0000-0000-000000000023",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="swpic2c">Ut labore et dolore magna aliqua ut enim ad minim veniam.</p>',
                        "id": "swpic01-0000-0000-0000-000000000024",
                    },
                ],
            },
            "id": "swpic01-0000-0000-0000-000000000002",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": False, "show_to": SHOW_TO_ALL},
                "media": [
                    {
                        "type": "media",
                        "value": [animation_block(poster_image_id=img, block_id="swpic01-0000-0000-0000-000000000031", show_pause_button=True)],
                        "id": "swpic01-0000-0000-0000-000000000032",
                    }
                ],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": '<p data-block-key="swpic3e">Dolor</p>',
                            "heading_text": '<p data-block-key="swpic3h">Quis nostrud exercitation ullamco</p>',
                            "subheading_text": "",
                        },
                        "id": "swpic01-0000-0000-0000-000000000033",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="swpic3c">Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore.</p>',
                        "id": "swpic01-0000-0000-0000-000000000034",
                    },
                ],
            },
            "id": "swpic01-0000-0000-0000-000000000003",
        },
    ]
    return {
        "type": "cards_list",
        "value": {
            "settings": {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
            "cards": animation_cards,
        },
        "id": "swpic01-0000-0000-0000-000000000001",
    }


def get_smart_window_testimonial_cards() -> dict:
    placeholder_images = get_placeholder_images()
    img = placeholder_images.image.id
    dark = placeholder_images.dark_image.id
    _image = {
        "image": img,
        "image_alt": "A numbered grid, standing in for a real image",
        "settings": {"dark_mode_image": dark, "mobile_image": None, "dark_mode_mobile_image": None},
    }
    _no_image = {"image": None, "image_alt": "", "settings": {"dark_mode_image": None, "mobile_image": None, "dark_mode_mobile_image": None}}
    cards = [
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000001",
            content='<p data-block-key="swptc1c">Lorem ipsum dolor sit amet, consectetur adipiscing elit,'
            " sed do eiusmod tempor incididunt ut labore et dolore.</p>",
            attribution='<p data-block-key="swptc1a">Layla Hassan</p>',
            attribution_role='<p data-block-key="swptc1r">Product Designer</p>',
            attribution_image=_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000002",
            content='<p data-block-key="swptc2c">Ut enim ad minim veniam, quis nostrud exercitation '
            "ullamco laboris nisi ut aliquip ex ea commodo.</p>",
            attribution='<p data-block-key="swptc2a">Marcus Osei</p>',
            attribution_role='<p data-block-key="swptc2r">Software Engineer</p>',
            attribution_image=_no_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000003",
            content='<p data-block-key="swptc3c">Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat.</p>',
            attribution='<p data-block-key="swptc3a">Priya Nair</p>',
            attribution_role='<p data-block-key="swptc3r">Journalist</p>',
            attribution_image=_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000004",
            content='<p data-block-key="swptc4c">Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim.</p>',
            attribution='<p data-block-key="swptc4a">Tom Reyes</p>',
            attribution_role="",
            attribution_image=_no_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000005",
            content='<p data-block-key="swptc5c">Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>',
            attribution='<p data-block-key="swptc5a">Yuki Tanaka</p>',
            attribution_role='<p data-block-key="swptc5r">UX Researcher</p>',
            attribution_image=_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000006",
            content='<p data-block-key="swptc6c">Sed ut perspiciatis unde omnis iste natus error sit '
            "voluptatem accusantium doloremque laudantium.</p>",
            attribution='<p data-block-key="swptc6a">Ana Ferreira</p>',
            attribution_role='<p data-block-key="swptc6r">Student</p>',
            attribution_image=_no_image,
        ),
    ]
    return {
        "type": "cards_list",
        "value": {
            "settings": {"container_width": "scroll", "cards_per_row": "", "two_wide_xs": False},
            "cards": cards,
        },
        "id": "swptc01-0000-0000-0000-000000000001",
    }


def get_smart_window_page_content() -> list[dict]:
    return [
        get_smart_window_sliding_carousel(),
        section(
            heading_text="Lorem ipsum dolor sit amet",
            content_blocks=[get_smart_window_line_cards()],
            section_id="swpsec1-0000-0000-0000-000000000001",
        ),
        section(
            heading_text="Consectetur adipiscing elit",
            content_blocks=[get_smart_window_illustration_cards()],
            section_id="swpsec2-0000-0000-0000-000000000001",
        ),
        get_smart_window_testimonial_cards(),
    ]


def get_smart_window_test_page() -> SmartWindowPage:
    image, dark_image, _, _ = get_placeholder_images()
    explainer_page = get_smart_window_explainer_test_page()
    index_page = get_flare_pages_docs_page()

    slug = "test-smart-window"
    page = get_or_create_page(
        SmartWindowPage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Smart Window Page",
            "heading_text": '<p data-block-key="swph">Lorem ipsum dolor sit amet</p>',
            "subheading_text": '<p data-block-key="swps">Consectetur adipiscing elit, sed do eiusmod tempor incididunt.</p>',
            "image": image,
            "image_alt": "A numbered grid, standing in for a real image",
        },
    )

    page.heading_text = '<p data-block-key="swph">Lorem ipsum dolor sit amet</p>'
    page.subheading_text = '<p data-block-key="swps">Consectetur adipiscing elit, sed do eiusmod tempor incididunt.</p>'
    page.image = image
    page.image_alt = "A numbered grid, standing in for a real image"
    page.image_dark_mode = dark_image
    page.animation = ANIMATION_URL
    page.animation_alt = "Lorem ipsum animation."
    page.show_smart_window_button = "allowed_territories"
    page.redirect_page = explainer_page
    page.content = get_smart_window_page_content()
    page.save_revision().publish()
    return page
