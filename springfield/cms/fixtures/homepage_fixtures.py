# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_snippet
from springfield.cms.models import HomePage


def get_home_intro():
    buttons = get_button_variants()

    return {
        "type": "intro",
        "value": {
            "heading": {
                "superheading_text": '<p data-block-key="1khhq"><a href="https://mozilla.org"><i>NEW</i> See the latest</a></p>',
                "heading_text": '<p data-block-key="yy3vb">This is the internet, on your terms</p>',
                "subheading_text": '<p data-block-key="m6fp1">Fast, customizable and secure, Firefox lets you browse how you like, when you like. '
                "We're built by a people-first organization that answers to you — not billionaires.  </p>",
            },
            "buttons": [buttons["download"]],
        },
        "id": "f5a78a6e-7dfb-477e-ad38-d800460ff152",
    }


def get_cards_list():
    return {
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
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                        "tags": [],
                        "superheading": '<p data-block-key="p55oi">AI</p>',
                        "headline": '<p data-block-key="nnvio">Chat with your favorite AI </p>',
                        "content": '<p data-block-key="6ris8">Access AI chatbots directly from the sidebar, no tab-switching required. </p>',
                        "buttons": [],
                    },
                    "id": "770c184d-1840-4128-b424-575b9449c31e",
                },
                {
                    "type": "sticker_card",
                    "value": {
                        "settings": {"expand_link": False, "show_to": "all"},
                        "image": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                        "tags": [],
                        "superheading": '<p data-block-key="p55oi">Privacy</p>',
                        "headline": '<p data-block-key="nnvio">Privacy you can see and control </p>',
                        "content": '<p data-block-key="6ris8">We block trackers automatically and give you control over what you share.</p>',
                        "buttons": [],
                    },
                    "id": "b5722296-ce54-4e26-9b14-0ef23dd4030c",
                },
                {
                    "type": "sticker_card",
                    "value": {
                        "settings": {"expand_link": False, "show_to": "all"},
                        "image": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                        "tags": [],
                        "superheading": '<p data-block-key="p55oi">Organization</p>',
                        "headline": '<p data-block-key="nnvio">Work smarter, \u2028not harder</p>',
                        "content": '<p data-block-key="6ris8">Browse smarter with vertical tabs, tab groups, '
                        "sidebar access, PDF editing and more.</p>",
                        "buttons": [],
                    },
                    "id": "0670ff11-78b2-4c5d-81c2-f4b392af3adb",
                },
                {
                    "type": "sticker_card",
                    "value": {
                        "settings": {"expand_link": False, "show_to": "all"},
                        "image": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                        "tags": [],
                        "superheading": '<p data-block-key="p55oi">Independence</p>',
                        "headline": '<p data-block-key="nnvio">Your browser answers to you</p>',
                        "content": '<p data-block-key="6ris8">Independent from day one. No billionaire overlords. '
                        "No shareholders demanding your data.</p>",
                        "buttons": [],
                    },
                    "id": "3f06b021-aed7-4e8f-bc80-e13665e70f52",
                },
            ]
        },
        "id": "800071e2-f2c2-41cb-9ffe-712935b5cd79",
    }


def get_home_carousel():
    return {
        "type": "carousel",
        "value": {
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="hz35x">Run free when you</p><p data-block-key="tv0n">switch to '
                '<span class="fl-fx-logo">\u200d</span> Firefox</p>',
                "subheading_text": '<p data-block-key="4p98d">Switching is fast. We’ll import your bookmarks, passwords, '
                "autofill data and browsing history — automatically. No re-learning required. No data left behind.</p>",
            },
            "slides": [
                {
                    "type": "item",
                    "value": {
                        "headline": '<p data-block-key="v9evz">Download Firefox</p>',
                        "image": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                    },
                    "id": "a3f38c72-322a-48ef-8228-e401152a5b5c",
                },
                {
                    "type": "item",
                    "value": {
                        "headline": '<p data-block-key="v9evz">Select what you want to bring with you</p>',
                        "image": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                    },
                    "id": "f3ef3097-4e9e-4736-9056-1aedcb12d1d6",
                },
                {
                    "type": "item",
                    "value": {
                        "headline": '<p data-block-key="v9evz">Click import</p>',
                        "image": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": None,
                                "dark_mode_mobile_image": None,
                            },
                        },
                    },
                    "id": "33f6a49c-a286-47c9-9968-8bf782ffef35",
                },
            ],
        },
        "id": "2dcf9793-65bf-48d7-b91d-32a0a6cddb5d",
    }


def get_showcase_variants():
    return {
        "with_title": {
            "type": "showcase",
            "value": {
                "settings": {"layout": "expanded"},
                "headline": '<p data-block-key="t7z9f">All your stuff on \u2028all your devices</p>',
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
                        "id": "a086ca43-5ad4-4888-bf07-5b925b92ea77",
                    }
                ],
                "caption_title": '<p data-block-key="n053e">Take your tabs, history and passwords wherever you go.</p>',
                "caption_description": '<p data-block-key="bg8rh">Sign in once, sync everywhere. Your tabs, bookmarks, '
                "passwords and history follow you from desktop to phone to tablet — encrypted and private. "
                "Send pages between devices with one tap, or pick up mid-scroll right where you left off.</p>",
            },
            "id": "96e39826-5d1d-467e-a543-dad0d105be82",
        },
        "no_title": {
            "type": "showcase",
            "value": {
                "settings": {"layout": "expanded"},
                "headline": '<p data-block-key="hobr0">Made for 8 billion people. \u2028Not 8 billionaires.</p>',
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
                        "id": "a086ca43-5ad4-4888-bf07-5b925b92ea77",
                    }
                ],
                "caption_title": "",
                "caption_description": '<p data-block-key="qskqt">Make Firefox your own, from your language to your layout, '
                "and leave big tech behind.\xa0</p>",
            },
            "id": "9b590d74-ad50-4346-a8c1-934beb661715",
        },
    }


def get_card_gallery():
    buttons = get_button_variants()
    return {
        "type": "card_gallery",
        "value": {
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="kx74z">A browser built \u2028around you</p>',
                "subheading_text": "",
            },
            "main_card": {
                "icon": "themes",
                "headline": '<p data-block-key="espxb">Your productivity, amplified</p>',
                "description": '<ul><li data-block-key="nwdrr">Tab groups and Firefox View organize chaos into clarity</li>'
                '<li data-block-key="abrc2">Picture-in-picture lets you multitask without missing a moment</li>'
                '<li data-block-key="9fo56">Customizable sidebar puts your most-used tools one click away</li>'
                '<li data-block-key="2ba94">Pinned tabs keep important sites always accessible</li></ul>',
                "buttons": [buttons["primary"]],
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
                    },
                },
            },
            "secondary_card": {
                "icon": "trending",
                "headline": '<p data-block-key="czbp1">Simple. Thoughtful. Minimal.</p>',
                "description": '<p data-block-key="7lrh2">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque ac congue urna.</p>',
                "buttons": [buttons["primary"]],
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
                    },
                },
            },
            "callout_card": {
                "headline": '<p data-block-key="5z7qg">Control your corner of the internet</p>',
                "description": '<p data-block-key="f9aqa">Tweak settings, extensions and themes to match your vibe.</p>',
            },
            "cta": [],
        },
        "id": "6f56633b-38e3-4b67-8f54-a01ac1bd080a",
    }


def get_kit_banner():
    buttons = get_button_variants()
    return {
        "type": "kit_banner",
        "value": {
            "settings": {"show_to": "all", "anchor_id": "kit-banner"},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="cggck">Peace of mind?</p><p data-block-key="eia38">Piece of cake.</p>',
                "subheading_text": '<p data-block-key="qobm0">We block trackers automatically. Update security features seamlessly. '
                'Protect your data relentlessly.</p><p data-block-key="4tljo">With Firefox, you don’t have to become a privacy expert to '
                "browse safely.</p>",
            },
            "qr_code": "",
            "buttons": [buttons["ghost"]],
        },
        "id": "6b5ea914-32d5-4418-870c-73887974102e",
    }


def get_home_test_page() -> HomePage:
    index_page = get_2026_test_index_page()

    # Make sure the Pre-Footer CTA Snippet is created
    get_pre_footer_cta_snippet()

    page = HomePage.objects.filter(slug="test-home-page").first()
    if not page:
        page = HomePage(
            slug="test-home-page",
            title="Test Home Page",
        )
        index_page.add_child(instance=page)

    page.upper_content = [get_home_intro(), get_cards_list(), get_home_carousel()]
    page.lower_content = [*get_showcase_variants().values(), get_card_gallery(), get_kit_banner()]
    page.save_revision().publish()
    return page
