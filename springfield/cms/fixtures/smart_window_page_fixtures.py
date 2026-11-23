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
                    heading_text="Each slide pairs a heading with an animation",
                    superheading_text="Sliding carousel",
                    subheading_text="Use the arrows or swipe to move between slides.",
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
                    heading_text="Animations loop until the visitor pauses",
                    superheading_text="Autoplay",
                    subheading_text="Each slide shows a pause button over the animation.",
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
                    heading_text="Posters can alternate light and dark",
                    superheading_text="Dark mode",
                    subheading_text="This slide uses the dark-mode placeholder image.",
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
                    heading_text="Keep slide headings short",
                    superheading_text="Rhythm",
                    subheading_text="Long headings crowd the animation beside them.",
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
                    heading_text="End on the strongest capability",
                    superheading_text="Wrap up",
                    subheading_text="The last slide is the one visitors remember.",
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
                        "superheading": '<p data-block-key="swplc1s">Line cards</p>',
                        "headline": '<p data-block-key="swplc1h">A compact row of headline-and-text cards</p>',
                        "content": '<p data-block-key="swplc1c">Line Cards suit short, parallel points that do not need an image — '
                        "two or three reads best.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000001",
                },
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc2s">Keep it brief</p>',
                        "headline": '<p data-block-key="swplc2h">One idea per card</p>',
                        "content": '<p data-block-key="swplc2c">Give each card a single takeaway so the row stays scannable at a glance.</p>',
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
                            "superheading_text": '<p data-block-key="swpic1e">Illustration cards</p>',
                            "heading_text": '<p data-block-key="swpic1h">Cards can lead with an animation</p>',
                            "subheading_text": "",
                        },
                        "id": "swpic01-0000-0000-0000-000000000013",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="swpic1c">The media area sits above the heading and body copy.</p>',
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
                            "superheading_text": '<p data-block-key="swpic2e">Consistent media</p>',
                            "heading_text": '<p data-block-key="swpic2h">Give every card the same media type</p>',
                            "subheading_text": "",
                        },
                        "id": "swpic01-0000-0000-0000-000000000023",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="swpic2c">Mixing images and animations across a row makes the cards look uneven.</p>',
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
                            "superheading_text": '<p data-block-key="swpic3e">Three across</p>',
                            "heading_text": '<p data-block-key="swpic3h">Three cards fit a row comfortably</p>',
                            "subheading_text": "",
                        },
                        "id": "swpic01-0000-0000-0000-000000000033",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="swpic3c">On narrow screens the cards stack into a single column automatically.</p>',
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
            content='<p data-block-key="swptc1c">A testimonial card holds a short quote, a name, an optional role, '
            "and an optional portrait. Keep the quote to a sentence or two.</p>",
            attribution='<p data-block-key="swptc1a">Layla Hassan</p>',
            attribution_role='<p data-block-key="swptc1r">Product Designer</p>',
            attribution_image=_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000002",
            content='<p data-block-key="swptc2c">This card has no portrait, so it falls back to showing just the quote '
            "and attribution. Cards in one row can mix the two.</p>",
            attribution='<p data-block-key="swptc2a">Marcus Osei</p>',
            attribution_role='<p data-block-key="swptc2r">Software Engineer</p>',
            attribution_image=_no_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000003",
            content='<p data-block-key="swptc3c">The scrolling row holds more cards than fit on screen; visitors swipe to see the rest.</p>',
            attribution='<p data-block-key="swptc3a">Priya Nair</p>',
            attribution_role='<p data-block-key="swptc3r">Journalist</p>',
            attribution_image=_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000004",
            content='<p data-block-key="swptc4c">The role line is optional too. Leave it blank when the person&rsquo;s name '
            "is enough on its own.</p>",
            attribution='<p data-block-key="swptc4a">Tom Reyes</p>',
            attribution_role="",
            attribution_image=_no_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000005",
            content='<p data-block-key="swptc5c">Short quotes keep the cards the same height and the row tidy.</p>',
            attribution='<p data-block-key="swptc5a">Yuki Tanaka</p>',
            attribution_role='<p data-block-key="swptc5r">UX Researcher</p>',
            attribution_image=_image,
        ),
        testimonial_card(
            block_id="swptc01-0000-0000-0000-000000000006",
            content='<p data-block-key="swptc6c">Aim for a handful of real quotes rather than a long list of weak ones.</p>',
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
            heading_text="Sections group the blocks below a heading",
            content_blocks=[get_smart_window_line_cards()],
            section_id="swpsec1-0000-0000-0000-000000000001",
        ),
        section(
            heading_text="A second section, this one holding cards",
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
            "heading_text": '<p data-block-key="swph">Meet the Firefox Smart Window</p>',
            "subheading_text": '<p data-block-key="swps">The hero heading, subheading and animation at the top are page fields, '
            "not blocks — the stream below fills in the rest of the page.</p>",
            "image": image,
            "image_alt": "A numbered grid, standing in for a real image",
        },
    )

    page.heading_text = '<p data-block-key="swph">Meet the Firefox Smart Window</p>'
    page.subheading_text = (
        '<p data-block-key="swps">The hero heading, subheading and animation at the top are page fields, '
        "not blocks — the stream below fills in the rest of the page.</p>"
    )
    page.image = image
    page.image_alt = "A numbered grid, standing in for a real image"
    page.image_dark_mode = dark_image
    page.animation = ANIMATION_URL
    page.animation_alt = "A looping placeholder animation."
    page.show_smart_window_button = "allowed_territories"
    page.redirect_page = explainer_page
    page.content = get_smart_window_page_content()
    page.save_revision().publish()
    return page
