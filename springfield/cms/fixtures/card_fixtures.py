# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants, get_cta_variants
from springfield.cms.fixtures.tag_fixtures import get_tag_variants
from springfield.cms.models import FreeFormPage


def get_sticker_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="h5q1p">Sticker Card 1</p>',
                "content": '<p data-block-key="mkz0c">Sticker cards get images with an optional Dark Mode variant.</p>',
                "buttons": [
                    buttons["primary"],
                ],
            },
            "id": "49b08782-d185-4fbb-a0af-e50e25c195eb",
        },
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="h5q1p">Sticker Card 2</p>',
                "content": '<p data-block-key="mkz0c">Switch to Dark Mode in your browser settings to see the alternative image.</p>',
                "buttons": [
                    buttons["secondary"],
                ],
            },
            "id": "b93a238d-2db3-4917-907a-19478bb62fd1",
        },
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="h5q1p">Sticker Card 3</p>',
                "content": '<p data-block-key="mkz0c"><a linktype="page" id="64">Cards</a> <b>content</b> <i>have</i> <sup>rich</sup> <sub>text'
                '</sub> <s>features</s> <fxa data-cta-uid="563a54cd-4357-4d01-9370-3db3ec506d07">too</fxa>.</p>',
                "buttons": [
                    buttons["tertiary"],
                ],
            },
            "id": "0794afa0-1a7b-451c-bca3-0b8c23c26ffa",
        },
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="h5q1p">Sticker Card 4</p>',
                "content": '<p data-block-key="mkz0c">Cards can use all button variants.'
                "Check the expand link option on the card settings to make the entire card clickable.</p>",
                "buttons": [
                    buttons["ghost"],
                ],
            },
            "id": "cdc7a848-92e3-4c48-b144-071e9de0cc0a",
        },
    ]


def get_icon_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": False},
                "icon": "copy",
                "headline": '<p data-block-key="ob9zh">Icon Card</p>',
                "content": '<p data-block-key="h2wpt">Choose one of the Icon options to build the card.</p>',
                "buttons": [buttons["primary"]],
            },
            "id": "6004cabe-319f-48b7-90f5-cbbddbe4d97b",
        },
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": True},
                "icon": "alert",
                "headline": '<p data-block-key="ob9zh">Clickable Icon Card</p>',
                "content": '<p data-block-key="h2wpt">Check the Expand Link option in the card settings to make the entire card clickable.</p>',
                "buttons": [buttons["secondary"]],
            },
            "id": "510858fa-8a65-4799-b70c-acc6e6ee9b34",
        },
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": True},
                "icon": "calendar",
                "headline": '<p data-block-key="ob9zh">Another Icon Card</p>',
                "content": '<p data-block-key="h2wpt">All button options are available here too.</p>',
                "buttons": [buttons["tertiary"]],
            },
            "id": "47e18a6f-df51-417a-ad09-f47ee1ed1137",
        },
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": True},
                "icon": "blog",
                "headline": '<p data-block-key="ob9zh">Fourth Icon Card</p>',
                "content": '<p data-block-key="h2wpt">All button options are available here too.</p>',
                "buttons": [buttons["ghost"]],
            },
            "id": "1f1ab49b-41a4-4f6a-94f5-b73e895c6f87",
        },
    ]


def get_tag_card_variants() -> list[dict]:
    buttons = get_button_variants()
    tags = list(get_tag_variants().values())
    return [
        {
            "type": "tag_card",
            "value": {
                "settings": {"expand_link": False},
                "tags": tags[:3],
                "headline": '<p data-block-key="5j7b5">Tag Card 1</p>',
                "content": '<p data-block-key="0ucr3">Tag cards can have up to 3 tags.</p>',
                "buttons": [],
            },
            "id": "a377ba13-7fd2-42db-a0ce-1f130d3241d7",
        },
        {
            "type": "tag_card",
            "value": {
                "settings": {"expand_link": False},
                "tags": tags[3:6],
                "headline": '<p data-block-key="5j7b5">Tag Card 2</p>',
                "content": '<p data-block-key="0ucr3">The tags can have the icons positioned before or after the text.</p>',
                "buttons": [],
            },
            "id": "8edaa9df-c868-4bbf-9d21-ed81346dff90",
        },
        {
            "type": "tag_card",
            "value": {
                "settings": {"expand_link": False},
                "tags": tags[6:9],
                "headline": '<p data-block-key="5j7b5">Tag Card 3</p>',
                "content": '<p data-block-key="0ucr3">Tags can have rounded or soft corners.</p>',
                "buttons": [],
            },
            "id": "662a4d32-f61d-45c8-9f89-0b97374eade1",
        },
        {
            "type": "tag_card",
            "value": {
                "settings": {"expand_link": False},
                "tags": tags[9:12],
                "headline": '<p data-block-key="5j7b5">Tag Card 4</p>',
                "content": '<p data-block-key="0ucr3">Tag Cards can also have buttons.</p>',
                "buttons": [
                    buttons["primary"],
                ],
            },
            "id": "c66448ac-8599-4c19-8391-829feb6f16e8",
        },
    ]


def get_illustration_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "image_after": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="vqw7t">Illustration Card 1</p>',
                "content": '<p data-block-key="a8oh9">Illustration Cards have an optional Dark Mode image.</p>',
                "buttons": [buttons["primary"]],
            },
            "id": "dfba1968-a234-464e-9b7e-d640647002eb",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "image_after": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="vqw7t">Illustration Card 2</p>',
                "content": '<p data-block-key="a8oh9">Switch to Dark Mode on your browser settings to see the alternative image.</p>',
                "buttons": [buttons["secondary"]],
            },
            "id": "14890758-7673-4b63-a706-6be0fc5455d0",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "image_after": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="vqw7t">Reversed Illustration Card</p>',
                "content": '<p data-block-key="a8oh9">Check the Image After option on the card settings to invert the card layout.</p>',
                "buttons": [buttons["tertiary"]],
            },
            "id": "06511162-88b9-4f63-a688-6fce5eb37806",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": True, "image_after": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="vqw7t">Reversed Card with expand link</p>',
                "content": '<p data-block-key="a8oh9">Check the Expand Link option to make the entire card clickable.</p>',
                "buttons": [buttons["ghost"]],
            },
            "id": "3edec9e2-a0c2-4c93-909a-64318a9fbff4",
        },
    ]


def get_step_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="1aqle">Step Card 1</p>',
                "content": '<p data-block-key="flh4o">Step cards are just like illustration cards with the <i>Step XX</i> eyebrow.</p>',
                "buttons": [buttons["primary"]],
            },
            "id": "a66a74d9-122c-4a5c-8ed1-66994ee157a4",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="1aqle">Step Card 2</p>',
                "content": '<p data-block-key="flh4o">They also have Dark Mode image alternatives.</p>',
                "buttons": [buttons["secondary"]],
            },
            "id": "e217ed76-3ae9-4519-afd7-b96cac029a77",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="1aqle">Step Card 3</p>',
                "content": '<p data-block-key="flh4o">Check the <b>expand link</b> '
                "option on the card settings to make the entire card clickable.</p>",
                "buttons": [buttons["tertiary"]],
            },
            "id": "2ef5dce0-1cb3-43f6-acc9-4d99ad0c91a8",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "headline": '<p data-block-key="1aqle">Step Card 4</p>',
                "content": '<p data-block-key="flh4o">Step Cards also have all the button variants available.</p>',
                "buttons": [buttons["ghost"]],
            },
            "id": "a4cf37f8-5564-45df-af41-c707cc8c5e96",
        },
    ]


def get_cards_list_variants(cards, heading_1=None, heading_2=None) -> list[dict]:
    ctas = get_cta_variants()
    heading_1 = heading_1 or "Cards List with 3 columns layout"
    heading_2 = heading_2 or "Cards List with 4 columns layout"
    return [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": "all"},
                "heading": {
                    "superheading_text": "",
                    "heading_text": f'<p data-block-key="avdst">{heading_1}</p>',
                    "subheading_text": '<p data-block-key="pzw8b">The default layout uses <b>3 columns</b>.</p>',
                },
                "content": [
                    {
                        "type": "cards_list",
                        "value": {"cards": cards[:3]},
                        "id": "93ce98fc-2116-429b-afad-ca279675d766",
                    }
                ],
                "cta": [ctas["basic"]],
            },
            "id": "edde0a67-fec2-4967-8eb1-e64b693f2402",
        },
        {
            "type": "section",
            "value": {
                "settings": {"show_to": "all"},
                "heading": {
                    "superheading_text": "",
                    "heading_text": f'<p data-block-key="avdst">{heading_2}</p>',
                    "subheading_text": '<p data-block-key="pzw8b">The default layout uses <s>3 columns</s>,'
                    " but if there are 4 cards it changes to <i>4 columns</i>.</p>",
                },
                "content": [
                    {
                        "type": "cards_list",
                        "value": {"cards": cards[:4]},
                        "id": "76a544ed-823a-46fb-a61d-ccbea55cff80",
                    }
                ],
                "cta": [ctas["basic"]],
            },
            "id": "d65e4a61-8ecc-4c3e-a6c7-8609996bb414",
        },
    ]


def get_step_cards_list_variants(cards, heading_1=None, heading_2=None) -> list[dict]:
    card_lists = [*get_cards_list_variants(cards, heading_1, heading_2)]
    card_lists[0]["value"]["content"][0]["type"] = "step_cards"
    card_lists[1]["value"]["content"][0]["type"] = "step_cards"
    return card_lists


def get_sticker_cards_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-sticker-cards-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-sticker-cards-page",
            title="Test Sticker Cards Page",
        )
        index_page.add_child(instance=page)

    page.content = get_cards_list_variants(
        cards=get_sticker_card_variants(),
        heading_1="Cards List with Sticker Cards",
        heading_2="Cards List with Sticker Cards - 4 columns",
    )
    page.save_revision().publish()

    return page


def get_icon_cards_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-icon-cards-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-icon-cards-page",
            title="Test Icon Cards Page",
        )
        index_page.add_child(instance=page)

    page.content = get_cards_list_variants(
        cards=get_icon_card_variants(),
        heading_1="Cards List with Icon Cards",
        heading_2="Cards List with Icon Cards - 4 columns",
    )
    page.save_revision().publish()

    return page


def get_tag_cards_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-tag-cards-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-tag-cards-page",
            title="Test Tag Cards Page",
        )
        index_page.add_child(instance=page)

    page.content = get_cards_list_variants(
        cards=get_tag_card_variants(),
        heading_1="Cards List with Tag Cards",
        heading_2="Cards List with Tag Cards - 4 columns",
    )
    page.save_revision().publish()

    return page


def get_illustration_cards_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-illustration-cards-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-illustration-cards-page",
            title="Test Illustration Cards Page",
        )
        index_page.add_child(instance=page)

    page.content = get_cards_list_variants(
        cards=get_illustration_card_variants(),
        heading_1="Cards List with Illustration Cards",
        heading_2="Cards List with Illustration Cards - 4 columns",
    )
    page.save_revision().publish()

    return page


def get_step_cards_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-step-cards-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-step-cards-page",
            title="Test Step Cards Page",
        )
        index_page.add_child(instance=page)

    page.content = get_step_cards_list_variants(
        cards=get_step_card_variants(),
        heading_1="Step Cards List with 3 columns layout",
        heading_2="Step Cards List with 4 columns layout",
    )
    page.save_revision().publish()

    return page
