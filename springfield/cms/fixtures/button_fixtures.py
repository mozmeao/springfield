# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def get_button_variants() -> dict[str, dict]:
    return {
        "primary": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "",
                    "icon": "",
                    "icon_position": "right",
                    "analytics_id": "c4c4c73d-a612-452d-b1af-f4c0810fb441",
                },
                "label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                },
            },
            "id": "9e0a239d-9ef1-40f9-b031-5c68b54ee114",
        },
        "secondary": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "secondary",
                    "icon": "arrow-right",
                    "icon_position": "right",
                    "analytics_id": "cfdf0d2c-7eee-49c2-8747-80450e22dbdd",
                },
                "label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                },
            },
            "id": "668a7bdc-64e4-4401-864f-ac87f8f7aa1f",
        },
        "tertiary": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "tertiary",
                    "icon": "arrow-left",
                    "icon_position": "left",
                    "analytics_id": "83b0d9d6-2b49-4704-b06a-1300704e12fc",
                },
                "label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                },
            },
            "id": "13e00ed4-0a68-44fa-a41c-822be75318c7",
        },
        "ghost": {
            "type": "button",
            "value": {
                "settings": {
                    "theme": "ghost",
                    "icon": "chat",
                    "icon_position": "left",
                    "analytics_id": "83b0d9d6-2b49-4704-b06a-1300704e12fc",
                },
                "label": "Button",
                "link": {
                    "link_to": "custom_url",
                    "page": None,
                    "file": None,
                    "custom_url": "https://mozilla.org",
                    "anchor": "",
                    "email": "",
                    "phone": "",
                    "new_window": False,
                },
            },
            "id": "4ff21d57-e112-4799-a8c3-20bf9ebb2a93",
        },
    }


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
                },
            },
            "id": "4fd0adda-42ba-4ade-b63c-0208226696a4",
        }
    }
