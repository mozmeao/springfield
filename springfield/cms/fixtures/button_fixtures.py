# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_test_document, get_test_index_page
from springfield.cms.fixtures.snippet_fixtures import get_pretranslated_phrase_snippets
from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
from springfield.cms.models import FreeFormPage2026, PretranslatedPhrase


def get_button_variants(full=False) -> dict[str, dict]:
    get_pretranslated_phrase_snippets()
    get_firefox_pk = PretranslatedPhrase.objects.get(
        translation_key=PHRASES["get_firefox"]["translation_key"],
        locale=Locale.get_default(),
    ).pk
    buttons = {
        "primary": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "",
                    "icon": "",
                    "icon_position": "right",
                    "analytics_id": "c4c4c73d-a612-452d-b1af-f4c0810fb441",
                },
                "pretranslated_label": None,
                "custom_label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "9e0a239d-9ef1-40f9-b031-5c68b54ee114",
        },
        "secondary": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "secondary",
                    "icon": "forward",
                    "icon_position": "right",
                    "analytics_id": "cfdf0d2c-7eee-49c2-8747-80450e22dbdd",
                },
                "pretranslated_label": None,
                "custom_label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "668a7bdc-64e4-4401-864f-ac87f8f7aa1f",
        },
        "tertiary": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "tertiary",
                    "icon": "back",
                    "icon_position": "left",
                    "analytics_id": "83b0d9d6-2b49-4704-b06a-1300704e12fc",
                },
                "pretranslated_label": None,
                "custom_label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "13e00ed4-0a68-44fa-a41c-822be75318c7",
        },
        "ghost": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "ghost",
                    "icon": "comment",
                    "icon_position": "left",
                    "analytics_id": "83b0d9d6-2b49-4704-b06a-1300704e12fc",
                },
                "pretranslated_label": None,
                "custom_label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "4ff21d57-e112-4799-a8c3-20bf9ebb2a93",
        },
        "gold": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "gold",
                    "icon": "competitiveness",
                    "icon_position": "left",
                    "analytics_id": "83b0d9d6-2b49-4704-b06a-1300704e12fc",
                },
                "pretranslated_label": None,
                "custom_label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "4ff21d57-e112-4799-a8c3-20bf9ebb2a93",
        },
        "link": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "link",
                    "icon": None,
                    "icon_position": "right",
                    "analytics_id": "83b0d9d6-2b49-4704-b06a-1300704e12fc",
                },
                "pretranslated_label": None,
                "custom_label": "Learn more",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "4ff21d57-e112-4799-a8c3-20bf9ebb2a93",
        },
        "external_mozilla": {
            "type": "button",
            "value": {
                "settings": {"theme": "", "icon": "", "icon_position": "right", "analytics_id": "5383592c-13c2-407a-82fe-f099617c05d9"},
                "pretranslated_label": None,
                "custom_label": "Mozilla",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "b418983a-94cc-4c72-a5bc-f4915318f51c",
        },
        "external_mozilla_new_tab": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "secondary",
                    "icon": "forward",
                    "icon_position": "right",
                    "analytics_id": "b4adffda-872a-4f2b-b45a-63ac7cb71e91",
                },
                "pretranslated_label": None,
                "custom_label": "Relay new Tab",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://relay.firefox.com/",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": True,
                    "relative_url": "",
                },
            },
            "id": "8c8fa9da-aa41-4d6f-88e0-d3cb3a8e429d",
        },
        "external_other": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "tertiary",
                    "icon": "export-data",
                    "icon_position": "right",
                    "analytics_id": "77d97583-3536-48ae-a72f-6a67077b9988",
                },
                "pretranslated_label": None,
                "custom_label": "Wikipedia",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://www.wikipedia.org/",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "157e4a05-80b2-42af-88d8-dc79f1541d69",
        },
        "external_other_new_tab": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "ghost",
                    "icon": "search",
                    "icon_position": "left",
                    "analytics_id": "4c411613-ef35-46c0-9eff-3a1bef76dabd",
                },
                "pretranslated_label": None,
                "custom_label": "Wikipedia new Tab",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://www.wikipedia.org/",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": True,
                    "relative_url": "",
                },
            },
            "id": "eef9102c-ad76-4575-ad92-58d099633216",
        },
        "fxa": {
            "type": "fxa_button",
            "value": {
                "settings": {
                    "theme": "tertiary",
                    "icon": "single-user",
                    "icon_position": "left",
                    "analytics_id": "d9456b7f-015d-4799-a2c8-e67a2246bf4f",
                },
                "pretranslated_label": None,
                "custom_label": "Log in to Mozilla Account",
            },
            "id": "bc17ead3-29c7-44d5-b8b8-0b0aaaee3e56",
        },
        "download": {
            "type": "download_button",
            "value": {
                "pretranslated_label": get_firefox_pk,
                "custom_label": "",
                "settings": {
                    "theme": "",
                    "icon": "downloads",
                    "icon_position": "right",
                    "analytics_id": "d414c71a-feef-4106-8e77-26b01ea38237",
                    "show_default_browser_checkbox": False,
                },
            },
            "id": "98bd248c-c715-4986-9a60-c0922ba12799",
        },
        "download_default_browser": {
            "type": "download_button",
            "value": {
                "pretranslated_label": get_firefox_pk,
                "custom_label": "",
                "settings": {
                    "theme": "secondary",
                    "icon": "downloads",
                    "icon_position": "right",
                    "analytics_id": "d414c71a-feef-4106-8e77-26b01ea38237",
                    "show_default_browser_checkbox": True,
                },
            },
            "id": "98bd248c-c715-4986-9a60-c0922ba12799",
        },
        "store_android": {
            "type": "store_button",
            "value": {"store": "android"},
            "id": "sb000001-0000-0000-0000-000000000001",
        },
        "store_ios": {
            "type": "store_button",
            "value": {"store": "ios"},
            "id": "sb000001-0000-0000-0000-000000000002",
        },
        "focus_android": {
            "type": "focus_button",
            "value": {
                "settings": {
                    "theme": "",
                    "icon": "downloads",
                    "icon_position": "right",
                    "analytics_id": "fb000001-0000-0000-0000-000000000001",
                },
                "pretranslated_label": None,
                "custom_label": "Get Firefox Focus for Android",
                "store": "android",
            },
            "id": "fb000001-0000-0000-0000-000000000002",
        },
        "focus_ios": {
            "type": "focus_button",
            "value": {
                "settings": {
                    "theme": "secondary",
                    "icon": "downloads",
                    "icon_position": "right",
                    "analytics_id": "fb000001-0000-0000-0000-000000000003",
                },
                "pretranslated_label": None,
                "custom_label": "Get Firefox Focus for iOS",
                "store": "ios",
            },
            "id": "fb000001-0000-0000-0000-000000000004",
        },
    }
    if full:
        index_page = get_test_index_page()
        test_document = get_test_document()
        buttons.update(
            {
                "page": {
                    "type": "button",
                    "value": {
                        "settings": {
                            "theme": "tertiary",
                            "icon": "back",
                            "icon_position": "left",
                            "analytics_id": "0fef2106-9dd4-4185-9d5d-e9c352392c15",
                        },
                        "pretranslated_label": None,
                        "custom_label": "Test Index Page",
                        "link": {
                            "link_to": "page",
                            "page": index_page.id,
                            "file": None,
                            "custom_url": "",
                            "anchor": "",
                            "email": "",
                            "phone": "",
                            "new_window": False,
                            "relative_url": "",
                        },
                    },
                    "id": "0dade661-5c21-4aab-9826-7d03b2e0490b",
                },
                "page_new_tab": {
                    "type": "button",
                    "value": {
                        "settings": {
                            "theme": "ghost",
                            "icon": "diamond",
                            "icon_position": "left",
                            "analytics_id": "151a5822-63b4-4621-b146-4135044f21b8",
                        },
                        "pretranslated_label": None,
                        "custom_label": "Test Index in new tab",
                        "link": {
                            "link_to": "page",
                            "page": index_page.id,
                            "file": None,
                            "custom_url": "",
                            "anchor": "",
                            "email": "",
                            "phone": "",
                            "new_window": True,
                            "relative_url": "",
                        },
                    },
                    "id": "a3b9e37d-f113-424f-a612-fa93c2b105c6",
                },
                "document": {
                    "type": "button",
                    "value": {
                        "settings": {
                            "theme": "tertiary",
                            "icon": "paperclip",
                            "icon_position": "left",
                            "analytics_id": "2ce75501-5dc6-44cf-8609-61ee89c914b0",
                        },
                        "pretranslated_label": None,
                        "custom_label": "Open document",
                        "link": {
                            "link_to": "file",
                            "page": None,
                            "file": test_document.id,
                            "custom_url": "",
                            "anchor": "",
                            "email": "",
                            "phone": "",
                            "new_window": False,
                            "relative_url": "",
                        },
                    },
                    "id": "032851a4-20a7-4ca0-8914-2e25959fe507",
                },
                "email": {
                    "type": "button",
                    "value": {
                        "settings": {
                            "theme": "secondary",
                            "icon": "email-shield",
                            "icon_position": "left",
                            "analytics_id": "569de137-625d-48f7-bbfb-0fe87b43da83",
                        },
                        "pretranslated_label": None,
                        "custom_label": "Email",
                        "link": {
                            "link_to": "email",
                            "page": None,
                            "file": None,
                            "custom_url": "",
                            "anchor": "",
                            "email": "example@mozilla.org",
                            "phone": "",
                            "new_window": False,
                            "relative_url": "",
                        },
                    },
                    "id": "fbcc60a9-b82e-4f50-b962-5783df4ff4c4",
                },
                "phone": {
                    "type": "button",
                    "value": {
                        "settings": {
                            "theme": "",
                            "icon": "plane",
                            "icon_position": "left",
                            "analytics_id": "db29813f-1941-4e78-83ac-856943e34490",
                        },
                        "pretranslated_label": None,
                        "custom_label": "Phone",
                        "link": {
                            "link_to": "phone",
                            "page": None,
                            "file": None,
                            "custom_url": "",
                            "anchor": "",
                            "email": "",
                            "phone": "+111111111",
                            "new_window": False,
                            "relative_url": "",
                        },
                    },
                    "id": "6a1d0a3e-b7eb-42c4-a322-b28d7dc43d79",
                },
            }
        )
    return buttons


def get_cta_variants() -> dict[str, dict]:
    return {
        "basic": {
            "type": "item",
            "value": {
                "settings": {"analytics_id": "6cbbc05e-d7ad-4929-befc-410e1e26e776"},
                "label": "Call To Action",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                    "relative_url": "",
                },
            },
            "id": "4fd0adda-42ba-4ade-b63c-0208226696a4",
        }
    }


def get_button_blocks() -> list[dict]:
    buttons = get_button_variants(full=True)
    return [
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="j8nhz">External link Buttons with Mozilla domains</p>',
                    "subheading_text": '<p data-block-key="6u373">Choose <i>Custom URL</i> to ad a link to another site. '
                    'Check the <i>Open in new window</i> option if the link should open in another browser tab/window.</p><p data-block-key="ft6q5">'
                    '</p><p data-block-key="a68ij"><b>*.mozilla.org</b>, <b>*.mozillafoundation.org</b>, and <b>*.firefox.com</b> '
                    "(except <b>www.firefox.com</b>) domains automatically get UTM parameters added to the links. </p>",
                },
                "content": [
                    {
                        "type": "buttons",
                        "id": "842aa17d-0000-0000-0000-000000000001",
                        "value": [buttons["external_mozilla"], buttons["external_mozilla_new_tab"]],
                    },
                ],
            },
            "id": "842aa17d-3dc9-450d-982e-3afe90f40472",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="j8nhz">External link buttons with non Mozilla domains</p>',
                    "subheading_text": '<p data-block-key="6u373">Choose <i>Custom URL</i> to ad a link to another site. Check the '
                    '<i>Open in new window</i> option if the link should open in another browser tab/window.</p><p data-block-key="ft6q5"></p>'
                    '<p data-block-key="5inkg">Links to non Mozilla domain don\'t get the UTM parameters.</p>',
                },
                "content": [
                    {
                        "type": "buttons",
                        "id": "3fa1b0a0-0000-0000-0000-000000000001",
                        "value": [buttons["external_other"], buttons["external_other_new_tab"]],
                    },
                ],
            },
            "id": "3fa1b0a0-b990-4468-a3d7-39ab3a68b477",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="j8nhz">Internal link button</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "buttons", "id": "961cf2a3-0000-0000-0000-000000000001", "value": [buttons["page"], buttons["page_new_tab"]]},
                ],
            },
            "id": "961cf2a3-6b87-439a-8588-85b18d136781",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="j8nhz">Mozilla Account Button</p>',
                    "subheading_text": '<p data-block-key="6u373">If opened in Firefox, the button takes the user to the browser login. '
                    "In other browsers it's a link to log in to the Mozilla Account.</p>",
                },
                "content": [
                    {"type": "buttons", "id": "6662346e-0000-0000-0000-000000000001", "value": [buttons["fxa"]]},
                ],
            },
            "id": "6662346e-f897-45a6-95c6-b68e239e465b",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="dkgdn">Download Firefox Button</p>',
                    "subheading_text": '<p data-block-key="dkgdn">A special link to /thanks with the required attributes for the download flow.</p>'
                    '<p data-block-key="5inkg">Optional "Set as default browser" checkbox. The checkbox is only shown to Windows users.</p>',
                },
                "content": [
                    {
                        "type": "buttons",
                        "id": "79f53077-0000-0000-0000-000000000001",
                        "value": [buttons["download"], buttons["download_default_browser"]],
                    },
                ],
            },
            "id": "79f53077-d740-4332-b9ab-6f9dd95c326a",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="j8nhz">Document link</p>',
                    "subheading_text": '<p data-block-key="6u373">Choose from any document uploaded to the CMS.</p>',
                },
                "content": [
                    {"type": "buttons", "id": "52a2b31d-0000-0000-0000-000000000001", "value": [buttons["document"]]},
                ],
            },
            "id": "52a2b31d-7f05-4376-af75-52cf666e4365",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="j8nhz">Email and phone links</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "buttons", "id": "706155ae-0000-0000-0000-000000000001", "value": [buttons["email"], buttons["phone"]]},
                ],
            },
            "id": "706155ae-f993-4582-b2eb-21de4efa660e",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="sbh01">Store Buttons</p>',
                    "subheading_text": '<p data-block-key="sbsub1">Display the Google Play or App Store button.</p>',
                },
                "content": [
                    {"type": "buttons", "id": "storeintr-0000-0000-0000-000000000002", "value": [buttons["store_android"], buttons["store_ios"]]},
                ],
            },
            "id": "storeintr-0000-0000-0000-000000000001",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="fbh01">Firefox Focus Buttons</p>',
                    "subheading_text": '<p data-block-key="fbsub1">Display a link to Firefox Focus on Google Play or App Store.</p>',
                },
                "content": [
                    {"type": "buttons", "id": "focusintr-0000-0000-0000-000000000002", "value": [buttons["focus_android"], buttons["focus_ios"]]},
                ],
            },
            "id": "focusintr-0000-0000-0000-000000000001",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="uitour01h">UI Tour: Open New Tab</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "uitour01-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="uitour01t">Calls <code>Mozilla.UITour.showNewTab()</code> to open a new browser tab in Firefox. '
                        "Only works in Firefox Desktop — the button is hidden on other browsers.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "uitour01-0000-0000-0000-000000000002",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "",
                                        "icon": "open-tabs",
                                        "icon_position": "right",
                                        "analytics_id": "uitour01-0000-0000-0000-000000000010",
                                    },
                                    "button_type": "open_new_tab",
                                    "pretranslated_label": None,
                                    "custom_label": "Open New Tab",
                                },
                                "id": "uitour01-0000-0000-0000-000000000010",
                            },
                        ],
                    },
                ],
            },
            "id": "uitour01-0000-0000-0000-000000000000",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="uitour02h">UI Tour: Open Preferences</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "uitour02-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="uitour02t">Calls <code>Mozilla.UITour.openPreferences(pane)</code> to open '
                        "<code>about:preferences</code> in Firefox, scrolled to a specific pane. The button is hidden on other browsers.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "uitour02-0000-0000-0000-000000000002",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "",
                                        "icon": "settings",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000010",
                                    },
                                    "button_type": "open_about_preferences",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences (default)",
                                },
                                "id": "uitour02-0000-0000-0000-000000000010",
                            },
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "settings",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000011",
                                    },
                                    "button_type": "open_about_preferences_general",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: General",
                                },
                                "id": "uitour02-0000-0000-0000-000000000011",
                            },
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "home",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000012",
                                    },
                                    "button_type": "open_about_preferences_home",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: Home",
                                },
                                "id": "uitour02-0000-0000-0000-000000000012",
                            },
                        ],
                    },
                    {
                        "type": "buttons",
                        "id": "uitour02-0000-0000-0000-000000000003",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "search",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000013",
                                    },
                                    "button_type": "open_about_preferences_search",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: Search",
                                },
                                "id": "uitour02-0000-0000-0000-000000000013",
                            },
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "lock",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000014",
                                    },
                                    "button_type": "open_about_preferences_privacy",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: Privacy",
                                },
                                "id": "uitour02-0000-0000-0000-000000000014",
                            },
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "sparkles",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000015",
                                    },
                                    "button_type": "open_about_preferences_ai",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: AI Controls",
                                },
                                "id": "uitour02-0000-0000-0000-000000000015",
                            },
                        ],
                    },
                    {
                        "type": "buttons",
                        "id": "uitour02-0000-0000-0000-000000000004",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "sparkle-single",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000016",
                                    },
                                    "button_type": "open_about_preferences_experimental",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: Experimental",
                                },
                                "id": "uitour02-0000-0000-0000-000000000016",
                            },
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "sync",
                                        "icon_position": "left",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000017",
                                    },
                                    "button_type": "open_about_preferences_sync",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: Sync",
                                },
                                "id": "uitour02-0000-0000-0000-000000000017",
                            },
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "secondary",
                                        "icon": "",
                                        "icon_position": "right",
                                        "analytics_id": "uitour02-0000-0000-0000-000000000018",
                                    },
                                    "button_type": "open_about_preferences_more_from_mozilla",
                                    "pretranslated_label": None,
                                    "custom_label": "Preferences: More From Mozilla",
                                },
                                "id": "uitour02-0000-0000-0000-000000000018",
                            },
                        ],
                    },
                ],
            },
            "id": "uitour02-0000-0000-0000-000000000000",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="uitour03h">UI Tour: Open Protections Report</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "uitour03-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="uitour03t">Calls <code>Mozilla.UITour.showProtectionReport()</code> to open the Firefox '
                        "Privacy Protections dashboard. The button is hidden on other browsers.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "uitour03-0000-0000-0000-000000000002",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "",
                                        "icon": "shield-checkmark",
                                        "icon_position": "left",
                                        "analytics_id": "uitour03-0000-0000-0000-000000000010",
                                    },
                                    "button_type": "open_protections_report",
                                    "pretranslated_label": None,
                                    "custom_label": "View Protections Report",
                                },
                                "id": "uitour03-0000-0000-0000-000000000010",
                            },
                        ],
                    },
                ],
            },
            "id": "uitour03-0000-0000-0000-000000000000",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="uitour04h">UI Tour: Open Smart Window</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "uitour04-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="uitour04t">Calls <code>Mozilla.UITour.showFirefoxAccountsForAIWindow()</code> to open the '
                        "Firefox Accounts sign-in flow for the AI Smart Window feature. "
                        "The button is hidden on other browsers. Requires AI Controls to be available "
                        "(requires class <code>.ai-controls-available</code> on <code>&lt;html&gt;</code>). "
                        "Add a <code>data-next-url</code> attribute to the button element to redirect the user to a specific URL after sign-in.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "uitour04-0000-0000-0000-000000000002",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "",
                                        "icon": "sparkles",
                                        "icon_position": "left",
                                        "analytics_id": "uitour04-0000-0000-0000-000000000010",
                                    },
                                    "button_type": "open_smart_window",
                                    "pretranslated_label": None,
                                    "custom_label": "Open Smart Window",
                                },
                                "id": "uitour04-0000-0000-0000-000000000010",
                            },
                        ],
                    },
                ],
            },
            "id": "uitour04-0000-0000-0000-000000000000",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="uitour05h">UI Tour: Pin to Taskbar</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "uitour05-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="uitour05t">Calls <code>Mozilla.UITour.pinToTaskbar()</code> '
                        "to pin Firefox to the taskbar (Windows) or Dock (macOS). Only available on Windows and macOS. "
                        "The button is hidden on non-Firefox-Desktop browsers. "
                        "JS also hides it when Firefox is already pinned or pinning is not supported, "
                        "by checking <code>getConfiguration('appinfo').needsPin</code>.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "uitour05-0000-0000-0000-000000000002",
                        "value": [
                            {
                                "type": "uitour_button",
                                "value": {
                                    "settings": {
                                        "theme": "",
                                        "icon": "",
                                        "icon_position": "right",
                                        "analytics_id": "uitour05-0000-0000-0000-000000000010",
                                    },
                                    "button_type": "pin_to_taskbar",
                                    "pretranslated_label": None,
                                    "custom_label": "Pin Firefox to Taskbar",
                                },
                                "id": "uitour05-0000-0000-0000-000000000010",
                            },
                        ],
                    },
                ],
            },
            "id": "uitour05-0000-0000-0000-000000000000",
        },
    ]


def get_buttons_test_page() -> FreeFormPage2026:
    index_page = get_test_index_page()

    slug = "test-buttons"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Buttons 2026")
        index_page.add_child(instance=page)

    blocks = get_button_blocks()
    page.upper_content = blocks
    page.content = blocks
    page.save_revision().publish()
    return page
