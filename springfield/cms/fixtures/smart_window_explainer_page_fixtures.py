# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.models.pages import SmartWindowExplainerPage

_ANIMATION_URL = "https://assets.mozilla.net/video/red-pandas.webm"


def _animation_media(image_id, block_id=None):
    return {
        "type": "animation",
        "value": {
            "video_url": _ANIMATION_URL,
            "alt": "Lorem ipsum animation.",
            "poster": image_id,
            "playback": "autoplay_loop",
        },
        "id": block_id,
    }


def _rich_text(text, block_id):
    return {"type": "rich_text", "value": text, "id": block_id}


def _instructions(typewriter_text, instructions_text, block_id):
    return {
        "type": "smart_window_instructions",
        "value": {
            "pre_typewriter_text": "Type this",
            "typewriter_text": typewriter_text,
            "instructions": f'<p data-block-key="{block_id}i">{instructions_text}</p>',
        },
        "id": block_id,
    }


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
            "buttons": [],
        },
        "id": "swepi01-0000-0000-0000-000000000001",
    }


def get_smart_window_explainer_content() -> list[dict]:
    img = settings.PLACEHOLDER_IMAGE_ID
    return [
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True, "narrow": False},
                "media": [_animation_media(img, "swepmc01-0000-0000-0000-000000000010")],
                "eyebrow": "",
                "headline": '<p data-block-key="swepmc1h">Lorem ipsum dolor sit amet</p>',
                "tags": [],
                "content": [
                    _rich_text(
                        '<p data-block-key="swepmc1c1">Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>',
                        "swepmc01-0000-0000-0000-000000000011",
                    ),
                    _instructions(
                        "lorem ipsum dolor sit amet",
                        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor.",
                        "swepmc01-0000-0000-0000-000000000012",
                    ),
                    _rich_text(
                        '<p data-block-key="swepmc1c2">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.</p>',
                        "swepmc01-0000-0000-0000-000000000013",
                    ),
                ],
                "buttons": [],
            },
            "id": "swepmc01-0000-0000-0000-000000000001",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False, "narrow": False},
                "media": [_animation_media(img, "swepmc01-0000-0000-0000-000000000020")],
                "eyebrow": '<p data-block-key="swepmc2e">Consectetur</p>',
                "headline": '<p data-block-key="swepmc2h">Sed do eiusmod tempor incididunt</p>',
                "tags": [],
                "content": [
                    _rich_text(
                        '<p data-block-key="swepmc2c1">Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu '
                        "fugiat nulla pariatur.</p>",
                        "swepmc01-0000-0000-0000-000000000021",
                    ),
                    _instructions(
                        "sed do eiusmod tempor incididunt",
                        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua ut enim.",
                        "swepmc01-0000-0000-0000-000000000022",
                    ),
                    _rich_text(
                        '<p data-block-key="swepmc2c2">Excepteur sint occaecat cupidatat non proident.</p>',
                        "swepmc01-0000-0000-0000-000000000023",
                    ),
                ],
                "buttons": [],
            },
            "id": "swepmc01-0000-0000-0000-000000000002",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True, "narrow": False},
                "media": [_animation_media(img, "swepmc01-0000-0000-0000-000000000030")],
                "eyebrow": '<p data-block-key="swepmc3e">Adipiscing</p>',
                "headline": '<p data-block-key="swepmc3h">Quis nostrud exercitation ullamco</p>',
                "tags": [],
                "content": [
                    _rich_text(
                        '<p data-block-key="swepmc3c1">Sunt in culpa qui officia deserunt mollit anim id est laborum.</p>',
                        "swepmc01-0000-0000-0000-000000000031",
                    ),
                    _instructions(
                        "ut labore et dolore magna aliqua ut enim ad minim",
                        "Ut labore et dolore magna aliqua enim ad minim veniam quis nostrud exercitation.",
                        "swepmc01-0000-0000-0000-000000000032",
                    ),
                    _rich_text(
                        '<p data-block-key="swepmc3c2">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt '
                        "ut labore et dolore magna aliqua ut enim ad minim.</p>",
                        "swepmc01-0000-0000-0000-000000000033",
                    ),
                ],
                "buttons": [],
            },
            "id": "swepmc01-0000-0000-0000-000000000003",
        },
    ]


def get_smart_window_explainer_test_page() -> SmartWindowExplainerPage:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-smart-window-explainer"
    page = SmartWindowExplainerPage.objects.filter(slug=slug).first()
    if not page:
        page = SmartWindowExplainerPage(
            slug=slug,
            title="Test Smart Window Explainer",
        )
        index_page.add_child(instance=page)

    page.upper_content = [get_smart_window_explainer_intro()]
    page.content = get_smart_window_explainer_content()
    page.save_revision().publish()
    return page
