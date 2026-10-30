# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_pages_docs_page, get_image_media, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import (
    animation_block,
    button,
    buttons_block,
    cards_list,
    heading_value,
    illustration_card,
    image_block,
    notification_block,
    show_to_value,
)
from springfield.cms.fixtures.snippet_fixtures import get_floating_qr_code_snippet, get_qr_code_snippet
from springfield.cms.models import WhatsNewIndexPage, WhatsNewPage2026


def get_whatsnew_index_page() -> WhatsNewIndexPage:
    index_page = get_flare_pages_docs_page()
    wnp_index = get_or_create_page(
        WhatsNewIndexPage,
        slug="test-whatsnew",
        parent=index_page,
        defaults={"title": "What's New Index Page"},
    )
    wnp_index.title = "What's New Index Page"
    wnp_index.save_revision().publish()
    return wnp_index


def get_whats_new_page_with_qr_snippet() -> WhatsNewPage2026:
    get_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-qr"
    page = get_or_create_page(
        WhatsNewPage2026,
        slug=slug,
        parent=wnp_index,
        defaults={
            "title": "What's New — QR Snippet Test",
            "version": "131",
        },
    )

    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="wnp-h">What\'s new in Firefox</p>',
                    "subheading_text": "",
                },
                "content": [],
                "cta": [],
            },
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567891",
        },
    ]
    page.show_qr_code_snippet = True
    page.save_revision().publish()
    return page


def get_whats_new_page_with_floating_qr_snippet() -> WhatsNewPage2026:
    get_floating_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-floating-qr"
    page = get_or_create_page(
        WhatsNewPage2026,
        slug=slug,
        parent=wnp_index,
        defaults={
            "title": "What's New — Floating QR Snippet Test",
            "version": "131",
        },
    )

    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="wnp-h">What\'s new in Firefox</p>',
                    "subheading_text": "",
                },
                "content": [],
                "cta": [],
            },
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567891",
        },
    ]
    page.show_floating_qr_code_snippet = True
    page.save_revision().publish()
    return page


def wn_banner(
    block_id, heading_text, subheading_text, *, theme="default", media_after=False, show_to=None, media=None, superheading_text="", buttons=None
):
    """A banner block for the What's New sample, matching the shape used on real What's New pages."""
    return {
        "type": "banner",
        "value": {
            "settings": {
                "theme": theme,
                "media_after": media_after,
                "show_to": show_to or SHOW_TO_ALL,
                "anchor_id": "",
                "slim": False,
                "remove_border_radius": False,
                "centralize_content": False,
            },
            "media": media or [],
            "heading": heading_value(block_id, heading_text, subheading_text=subheading_text, superheading_text=superheading_text),
            "content": [buttons_block(f"{block_id}-btns", buttons)] if buttons else [],
        },
        "id": block_id,
    }


def learn_more_button(block_id, label="Learn more"):
    return button(block_id, label, f"{block_id}-analytics", url="https://support.mozilla.org/")


def get_whats_new_full_test_page() -> WhatsNewPage2026:
    """A full What's New page modelled on a real recent release (Firefox 159): an update
    notification and a hero banner up top, then a Section of features, platform-targeted
    banners, an outlined banner, a recap card group, and a closing full-width banner.
    The copy explains how each part of a What's New page is meant to be used."""
    placeholder_images = get_placeholder_images()
    img = placeholder_images.image.id
    wnp_index = get_whatsnew_index_page()

    page = get_or_create_page(
        WhatsNewPage2026,
        slug="test-wnp-full",
        parent=wnp_index,
        defaults={
            "title": "01. What's New — Full Sample",
            "version": "159",
        },
    )
    # Sequential prefix keeps the representative sample at the top of the What's New tier.
    page.title = "01. What's New — Full Sample"

    page.upper_content = [
        notification_block(
            "wnfnot1",
            message="Your Firefox is up to date. This bar greets people returning right after an update.",
            show_to=show_to_value(),
            headline="You're up to date",
        ),
        wn_banner(
            "wnfhero1-0000-0000-0000-000000000001",
            heading_text="Lead with your single biggest feature",
            subheading_text="The upper banner is the hero. Give it one animation, a sentence of copy and a single link — "
            "this is the first thing a returning user sees.",
            superheading_text="What's new in Firefox 159",
            media_after=True,
            media=[animation_block("wnfhero-anim", poster_image_id=img, show_pause_button=True)],
            buttons=[learn_more_button("wnfhero-btn", "Learn how this feature works")],
        ),
    ]

    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": heading_value(
                    "wnfsec1",
                    heading_text="Group a cluster of features in a Section",
                    subheading_text="A Section gathers related banners under one heading, with an optional shared call to action.",
                ),
                "content": [
                    wn_banner(
                        "wnfsec1-banner-a",
                        heading_text="Describe one feature at a time",
                        subheading_text="Keep each banner to a single idea so the page stays skimmable.",
                        media=get_image_media("wnfsec1-media-a"),
                        buttons=[learn_more_button("wnfsec1-btn-a", "Read the how-to")],
                    ),
                    wn_banner(
                        "wnfsec1-banner-b",
                        heading_text="Alternate the media side for rhythm",
                        subheading_text="Flip the media left and right between banners so a long page doesn't feel repetitive.",
                        media_after=True,
                        media=[animation_block("wnfsec1-anim-b", poster_image_id=img, show_pause_button=True)],
                        buttons=[learn_more_button("wnfsec1-btn-b")],
                    ),
                ],
                "cta": [button("wnfsec1-cta", "See full release notes", "wnfsec1-cta-analytics", url="https://www.firefox.com/", theme="link")],
            },
            "id": "wnfsec01-0000-0000-0000-000000000001",
        },
        wn_banner(
            "wnfwin",
            heading_text="Target a feature to the platform it applies to",
            subheading_text="This banner uses Show To, so only Windows visitors see it.",
            show_to=show_to_value(platforms=["windows"]),
            media=get_image_media("wnfwin-media"),
            buttons=[learn_more_button("wnfwin-btn", "Windows example")],
        ),
        wn_banner(
            "wnfmac",
            heading_text="…and show the matching version to Mac users",
            subheading_text="A second copy of the same feature, shown only to macOS. Pair platform banners this way.",
            show_to=show_to_value(platforms=["osx"]),
            media=get_image_media("wnfmac-media"),
            buttons=[learn_more_button("wnfmac-btn", "macOS example")],
        ),
        wn_banner(
            "wnfout",
            heading_text="Use the outlined theme for secondary notes",
            subheading_text="The outlined banner is lighter than a filled one — good for a nice-to-know feature rather than a headline.",
            theme="outlined",
            media_after=True,
            media=get_image_media("wnfout-media"),
            buttons=[learn_more_button("wnfout-btn")],
        ),
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": heading_value(
                    "wnfsec2",
                    heading_text="In case you missed it",
                    subheading_text="Close with a card group that recaps older highlights — each card the same shape, each linking out.",
                ),
                "content": [
                    cards_list(
                        "wnfcards",
                        [
                            illustration_card(
                                "wnfcard1",
                                "Cards suit a short recap",
                                "Give every card the same media type and a one-line takeaway.",
                                [image_block("wnfcard1-img", img)],
                            ),
                            illustration_card(
                                "wnfcard2",
                                "Keep the cards parallel",
                                "Matching copy length keeps the row even and easy to scan.",
                                [image_block("wnfcard2-img", img)],
                            ),
                            illustration_card(
                                "wnfcard3",
                                "Three across reads well",
                                "On narrow screens the cards stack into a single column automatically.",
                                [image_block("wnfcard3-img", img)],
                            ),
                        ],
                    )
                ],
                "cta": [],
            },
            "id": "wnfsec02-0000-0000-0000-000000000001",
        },
        wn_banner(
            "wnfpurple",
            heading_text="End on a full-width call to action",
            subheading_text="The purple gradient banner is the loudest one — save it for the single thing you most want people to do.",
            theme="purple-radial-gradient",
            media=get_image_media("wnfpurple-media"),
        ),
    ]
    page.save_revision().publish()
    return page
