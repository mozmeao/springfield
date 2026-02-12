# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
from springfield.cms.fixtures.homepage_fixtures import get_card_gallery, get_showcase_variants
from springfield.cms.fixtures.snippet_fixtures import get_banner_snippet
from springfield.cms.models import FreeFormPage2026


def get_intro_2026_variants():
    """Get various IntroBlock2026 configurations."""
    return {
        "with_image": {
            "type": "intro",
            "value": {
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                                "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
                            },
                        },
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="1khhq">Protection</p>',
                    "heading_text": '<p data-block-key="yy3vb">Your online life belongs to you</p>',
                    "subheading_text": "<p data-block-key=\"m6fp1\">Protection shouldn't be a premium feature. With Firefox, it's built in.</p>",
                },
                "buttons": [],
            },
            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        },
        "with_video": {
            "type": "intro",
            "value": {
                "media": [
                    {
                        "type": "video",
                        "value": {
                            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            "alt": "Sample video description",
                            "poster": settings.PLACEHOLDER_IMAGE_ID,
                        },
                        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="1khhq"><i>NEW</i> Firefox Features</p>',
                    "heading_text": '<p data-block-key="yy3vb">Experience the next generation of browsing</p>',
                    "subheading_text": '<p data-block-key="m6fp1">Watch how Firefox makes your browsing faster, safer, and more private.</p>',
                },
                "buttons": [],
            },
            "id": "d4e5f6a7-b8c9-0123-def1-234567890123",
        },
        "without_media": {
            "type": "intro",
            "value": {
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="yy3vb">Simple and powerful</p>',
                    "subheading_text": '<p data-block-key="m6fp1">Firefox gives you the tools you need without the bloat you don\'t.</p>',
                },
                "buttons": [],
            },
            "id": "e5f6a7b8-c9d0-1234-ef12-345678901234",
        },
    }


def get_section_2026_variants():
    """Get various SectionBlock2026 configurations."""
    return {
        "with_step_cards": {
            "type": "section",
            "value": {
                "settings": {"show_to": "all", "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="qf39f">Get started in 3 easy steps</p>',
                    "subheading_text": '<p data-block-key="m6fp1">Setting up Firefox is quick and simple</p>',
                },
                "content": [
                    {
                        "type": "step_cards",
                        "value": {
                            "cards": [
                                {
                                    "type": "item",
                                    "value": {
                                        "settings": {"expand_link": False},
                                        "image": {
                                            "image": settings.PLACEHOLDER_IMAGE_ID,
                                            "settings": {
                                                "dark_mode_image": None,
                                                "mobile_image": None,
                                                "dark_mode_mobile_image": None,
                                            },
                                        },
                                        "eyebrow": '<p data-block-key="1khhq">Step 1</p>',
                                        "headline": '<p data-block-key="yy3vb">Download Firefox</p>',
                                        "content": '<p data-block-key="m6fp1">Click the download button to get started</p>',
                                        "buttons": [],
                                    },
                                    "id": "f6a7b8c9-d0e1-2345-f123-456789012345",
                                },
                                {
                                    "type": "item",
                                    "value": {
                                        "settings": {"expand_link": False},
                                        "image": {
                                            "image": settings.PLACEHOLDER_IMAGE_ID,
                                            "settings": {
                                                "dark_mode_image": None,
                                                "mobile_image": None,
                                                "dark_mode_mobile_image": None,
                                            },
                                        },
                                        "eyebrow": '<p data-block-key="1khhq">Step 2</p>',
                                        "headline": '<p data-block-key="yy3vb">Install and launch</p>',
                                        "content": '<p data-block-key="m6fp1">Follow the simple installation wizard</p>',
                                        "buttons": [],
                                    },
                                    "id": "a7b8c9d0-e1f2-3456-1234-567890123456",
                                },
                                {
                                    "type": "item",
                                    "value": {
                                        "settings": {"expand_link": False},
                                        "image": {
                                            "image": settings.PLACEHOLDER_IMAGE_ID,
                                            "settings": {
                                                "dark_mode_image": None,
                                                "mobile_image": None,
                                                "dark_mode_mobile_image": None,
                                            },
                                        },
                                        "eyebrow": '<p data-block-key="1khhq">Step 3</p>',
                                        "headline": '<p data-block-key="yy3vb">Start browsing</p>',
                                        "content": '<p data-block-key="m6fp1">Enjoy a faster, safer browsing experience</p>',
                                        "buttons": [],
                                    },
                                    "id": "b8c9d0e1-f2a3-4567-2345-678901234567",
                                },
                            ]
                        },
                        "id": "c9d0e1f2-a3b4-5678-3456-789012345678",
                    }
                ],
                "cta": [],
            },
            "id": "d0e1f2a3-b4c5-6789-4567-890123456789",
        },
        "with_cards_list": {
            "type": "section",
            "value": {
                "settings": {"show_to": "all", "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="qf39f">Why choose Firefox?</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "cards_list",
                        "value": {
                            "cards": [
                                {
                                    "type": "sticker_card",
                                    "value": {
                                        "settings": {"expand_link": False, "show_to": "all"},
                                        "image": {
                                            "image": settings.PLACEHOLDER_IMAGE_ID,
                                            "settings": {
                                                "dark_mode_image": None,
                                                "mobile_image": None,
                                                "dark_mode_mobile_image": None,
                                            },
                                        },
                                        "superheading": '<p data-block-key="p55oi">Fast</p>',
                                        "headline": '<p data-block-key="nnvio">Lightning-fast performance</p>',
                                        "content": '<p data-block-key="6ris8">Browse at the speed of thought</p>',
                                        "buttons": [],
                                    },
                                    "id": "e1f2a3b4-c5d6-7890-5678-901234567890",
                                },
                                {
                                    "type": "sticker_card",
                                    "value": {
                                        "settings": {"expand_link": False, "show_to": "all"},
                                        "image": {
                                            "image": settings.PLACEHOLDER_IMAGE_ID,
                                            "settings": {
                                                "dark_mode_image": None,
                                                "mobile_image": None,
                                                "dark_mode_mobile_image": None,
                                            },
                                        },
                                        "superheading": '<p data-block-key="p55oi">Secure</p>',
                                        "headline": '<p data-block-key="nnvio">Built-in protection</p>',
                                        "content": '<p data-block-key="6ris8">Your privacy is our priority</p>',
                                        "buttons": [],
                                    },
                                    "id": "f2a3b4c5-d6e7-8901-6789-012345678901",
                                },
                            ]
                        },
                        "id": "a3b4c5d6-e7f8-9012-7890-123456789012",
                    }
                ],
                "cta": [],
            },
            "id": "b4c5d6e7-f8a9-0123-8901-234567890123",
        },
        "without_content": {
            "type": "section",
            "value": {
                "settings": {"show_to": "all", "anchor_id": "simple-section"},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="qf39f">A simple section heading</p>',
                    "subheading_text": '<p data-block-key="m6fp1">This section has a heading but no content blocks</p>',
                },
                "content": [],
                "cta": [],
            },
            "id": "c5d6e7f8-a9b0-1234-9012-345678901234",
        },
    }


def get_intro_2026_test_page():
    """Create a test page for IntroBlock2026."""
    index_page = get_2026_test_index_page()
    variants = get_intro_2026_variants()

    page = FreeFormPage2026.objects.filter(slug="intro-2026").first()
    if not page:
        page = FreeFormPage2026(
            slug="intro-2026",
            title="Intro 2026 Test",
        )
        index_page.add_child(instance=page)

    # Test intro blocks in both upper_content and content areas
    page.upper_content = [variants["with_image"]]
    page.content = [
        variants["with_video"],
        variants["without_media"],
    ]

    page.save_revision().publish()
    return page


def get_section_2026_test_page():
    """Create a test page for SectionBlock2026."""
    index_page = get_2026_test_index_page()
    variants = get_section_2026_variants()

    page = FreeFormPage2026.objects.filter(slug="section-2026").first()
    if not page:
        page = FreeFormPage2026(
            slug="section-2026",
            title="Section 2026 Test",
        )
        index_page.add_child(instance=page)

    # Test section blocks in both upper_content and content areas
    page.upper_content = [variants["with_step_cards"]]
    page.content = [
        variants["with_cards_list"],
        variants["without_content"],
    ]

    page.save_revision().publish()
    return page


def get_showcase_test_page():
    """Create a test page for ShowcaseBlock."""
    index_page = get_2026_test_index_page()
    variants = get_showcase_variants()

    page = FreeFormPage2026.objects.filter(slug="showcase-2026").first()
    if not page:
        page = FreeFormPage2026(
            slug="showcase-2026",
            title="Showcase Test",
        )
        index_page.add_child(instance=page)

    # Test showcase blocks in both upper_content and content areas
    page.upper_content = [variants["with_title"]]
    page.content = [
        variants["no_title"],
    ]

    page.save_revision().publish()
    return page


def get_card_gallery_test_page():
    """Create a test page for CardGalleryBlock."""
    index_page = get_2026_test_index_page()
    card_gallery = get_card_gallery()

    page = FreeFormPage2026.objects.filter(slug="card-gallery-2026").first()
    if not page:
        page = FreeFormPage2026(
            slug="card-gallery-2026",
            title="Card Gallery Test",
        )
        index_page.add_child(instance=page)

    # Test card gallery in both upper_content and content areas
    page.upper_content = [card_gallery]
    page.content = [card_gallery]

    page.save_revision().publish()
    return page


def get_banner_snippet_test_page():
    """Create a test page for BannerSnippet."""
    index_page = get_2026_test_index_page()
    banner_snippet = get_banner_snippet()

    page = FreeFormPage2026.objects.filter(slug="banner-snippet-2026").first()
    if not page:
        page = FreeFormPage2026(
            slug="banner-snippet-2026",
            title="Banner Snippet Test",
        )
        index_page.add_child(instance=page)

    banner_block = {
        "type": "banner_snippet",
        "value": banner_snippet.id,
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567891",
    }

    # Test banner snippet in both upper_content and content areas
    page.upper_content = [banner_block]
    page.content = [banner_block]

    page.save_revision().publish()
    return page


def get_freeform_2026_combined_test_page():
    """Create a comprehensive test page with all FreeFormPage2026 components."""
    index_page = get_2026_test_index_page()
    intro_variants = get_intro_2026_variants()
    section_variants = get_section_2026_variants()
    showcase_variants = get_showcase_variants()
    card_gallery = get_card_gallery()
    banner_snippet = get_banner_snippet()

    from springfield.cms.fixtures.mobile_store_qr_code_fixtures import get_mobile_store_qr_code_variants

    mobile_store_variants = get_mobile_store_qr_code_variants()

    page = FreeFormPage2026.objects.filter(slug="freeform-2026-combined").first()
    if not page:
        page = FreeFormPage2026(
            slug="freeform-2026-combined",
            title="Free Form 2026 Combined Test",
        )
        index_page.add_child(instance=page)

    # Test all components in split layout
    page.upper_content = [
        intro_variants["with_image"],
        section_variants["with_step_cards"],
    ]
    page.content = [
        showcase_variants["with_title"],
        card_gallery,
        mobile_store_variants["with_heading"],
        {
            "type": "banner_snippet",
            "value": banner_snippet.id,
            "id": "combined-banner-snippet",
        },
    ]

    page.save_revision().publish()
    return page
