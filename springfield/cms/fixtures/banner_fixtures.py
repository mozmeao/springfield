# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.tag_fixtures import get_tag_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_banner_variants():
    buttons = get_button_variants()
    videos = get_video_variants()
    tags = get_tag_variants()
    return [
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "default",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "simple-default-banner",
                },
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Default Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Simple Default Banner</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "ba260001-0000-0000-0000-000000000001", "value": [tags["purple"]]},
                    {
                        "type": "rich_text",
                        "id": "ba260001-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bu3eb">Use the content field to add any of the available content blocks. '
                        'Visit <a href="https://www.mozilla.org" uid="ba260000-0001-0001-0001-000000000001">Mozilla</a> for more.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260001-0000-0000-0000-000000000003",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000001",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "outlined",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "simple-outlined-banner-2026",
                },
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Simple Outlined Banner</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "ba260002-0000-0000-0000-000000000001", "value": [tags["red"]]},
                    {
                        "type": "rich_text",
                        "id": "ba260002-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bu3eb">Use the content field to add any of the available content blocks. '
                        "If no media is provided, it uses the centered layout.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260002-0000-0000-0000-000000000003",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000002",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "purple-radial-gradient",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "simple-purple-banner-2026",
                },
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Radial Gradient Banner</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260003-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Use the content field to add any of the available content blocks. '
                        "If no media is provided, it uses the centered layout.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260003-0000-0000-0000-000000000002",
                        "value": [buttons["tertiary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a166176e-de29-4ee8-99b3-110406f11a40",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "dark-purple-gradient",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "simple-dark-purple-banner-2026",
                },
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Dark Purple Gradient Banner</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "tags",
                        "id": "ba260004-0000-0000-0000-000000000001",
                        "value": [tags["orange"], tags["green"]],
                    },
                    {
                        "type": "rich_text",
                        "id": "ba260004-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bu3eb">Use the content field to add any of the available content blocks. '
                        "If no media is provided, it uses the centered layout.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260004-0000-0000-0000-000000000003",
                        "value": [buttons["tertiary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a944ae4e-dfe9-44ab-9d7d-e297ff85a642",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "dark-purple-gradient-inverted",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "simple-dark-purple-inverted-banner-2026",
                },
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Dark Purple Gradient Inverted Banner</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260005-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Use the content field to add any of the available content blocks. '
                        "If no media is provided, it uses the centered layout.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260005-0000-0000-0000-000000000002",
                        "value": [buttons["tertiary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a27def29-a3e6-45eb-aed8-5b8283bb4d70",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "default",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "default-banner-with-image",
                },
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
                        "id": "a1b2c3d4-0001-0001-0001-000000000004",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Default Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Default Banner with Image</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "tags",
                        "id": "ba260006-0000-0000-0000-000000000001",
                        "value": [tags["purple"], tags["red"]],
                    },
                    {
                        "type": "rich_text",
                        "id": "ba260006-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bu3eb">When media is provided, the banner uses a two column layout. '
                        "Switch between light and dark mode to see the alternative images.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260006-0000-0000-0000-000000000003",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000005",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "outlined",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "outlined-banner-with-image-2026",
                },
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
                        "id": "a1b2c3d4-0001-0001-0001-000000000006",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Image</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "ba260007-0000-0000-0000-000000000001", "value": [tags["orange"]]},
                    {
                        "type": "rich_text",
                        "id": "ba260007-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bu3eb">When media is provided, the banner uses a two column layout. '
                        "Switch between light and dark mode to see the alternative images.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260007-0000-0000-0000-000000000003",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000007",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "purple-radial-gradient",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "purple-banner-with-image-2026",
                },
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
                        "id": "a1b2c3d4-0001-0001-0001-000000000008",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Image</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260008-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">When media is provided, the banner uses a two column layout. '
                        "Switch between light and dark mode to see the alternative images.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260008-0000-0000-0000-000000000002",
                        "value": [buttons["tertiary"], buttons["ghost"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000009",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "default",
                    "media_after": True,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "default-banner-with-image-after",
                },
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
                        "id": "a1b2c3d4-0001-0001-0001-000000000010",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Default Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Default Banner with Image After</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260009-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Check the <i>Media After</i> option to switch the layout.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260009-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000011",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "outlined",
                    "media_after": True,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "outlined-banner-with-image-after-2026",
                },
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
                        "id": "a1b2c3d4-0001-0001-0001-000000000012",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Image After</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260010-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Check the <i>Media After</i> option to switch the layout.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260010-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000013",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "purple-radial-gradient",
                    "media_after": True,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "purple-banner-with-image-after-2026",
                },
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
                        "id": "a1b2c3d4-0001-0001-0001-000000000014",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Image After</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260011-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Check the <i>Media After</i> option to switch the layout.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260011-0000-0000-0000-000000000002",
                        "value": [buttons["tertiary"], buttons["ghost"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000015",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "default",
                    "media_after": True,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "default-banner-with-qr-code",
                },
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "a1b2c3d4-0001-0001-0001-000000000016",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Default Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Default Banner with QR Code</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260012-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Add the QR code data and an image to use as the QR background.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260012-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000017",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "outlined",
                    "media_after": True,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "outlined-banner-with-qr-code-2026",
                },
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "a1b2c3d4-0001-0001-0001-000000000018",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with QR Code</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260013-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">Add the QR code data and an image to use as the QR background.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260013-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000019",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "purple-radial-gradient",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "purple-banner-with-qr-code-2026",
                },
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "a1b2c3d4-0001-0001-0001-000000000020",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with QR Code</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "tags",
                        "id": "ba260014-0000-0000-0000-000000000001",
                        "value": [tags["purple"], tags["orange"], tags["green"]],
                    },
                    {
                        "type": "rich_text",
                        "id": "ba260014-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bu3eb">Add the QR code data and an image to use as the QR background.</p>',
                    },
                    {
                        "type": "buttons",
                        "id": "ba260014-0000-0000-0000-000000000003",
                        "value": [buttons["tertiary"], buttons["ghost"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000021",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "default",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "default-banner-with-video",
                },
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Default Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Default Banner with Video</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260015-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">You can add a video from YouTube or <a href="https://assets.mozilla.net">'
                        "Mozilla CDN</a>. The poster image will be displayed and swapped with the video once the user clicks the play button.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260015-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000022",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "outlined",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "outlined-banner-with-video-2026",
                },
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Video</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260016-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">You can add a video from YouTube or <a href="https://assets.mozilla.net">'
                        "Mozilla CDN</a>. The poster image will be displayed and swapped with the video once the user clicks the play button.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260016-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000023",
        },
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "purple-radial-gradient",
                    "media_after": True,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "purple-banner-with-video-2026",
                },
                "media": [videos["cdn"]],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Video</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260017-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">You can add a video from YouTube or <a href="https://assets.mozilla.net">'
                        "Mozilla CDN</a>. The poster image will be displayed and swapped with the video once the user clicks the play button.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260017-0000-0000-0000-000000000002",
                        "value": [buttons["tertiary"], buttons["ghost"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000024",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "default", "media_after": False, "show_to": SHOW_TO_ALL},
                "media": [videos["animation"]],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Default Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Default Banner with Animation</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260018-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">You can add a video from <a href="https://assets.mozilla.net">'
                        "Mozilla CDN</a>. The video will play automatically in loop. The poster image will be displayed as a fallback.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260018-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000025",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "outlined", "media_after": False, "show_to": SHOW_TO_ALL},
                "media": [videos["animation"]],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Animation</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260019-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">You can add a video from <a href="https://assets.mozilla.net">'
                        "Mozilla CDN</a>. The video will play automatically in loop. The poster image will be displayed as a fallback.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260019-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000026",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "purple-radial-gradient", "media_after": True, "show_to": SHOW_TO_ALL},
                "media": [videos["animation_autoplay_once"]],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Animation (Autoplay once)</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "ba260020-0000-0000-0000-000000000001",
                        "value": '<p data-block-key="bu3eb">You can add a video from <a href="https://assets.mozilla.net">'
                        "Mozilla CDN</a>. The video will play automatically in loop. The poster image will be displayed as a fallback.</p>",
                    },
                    {
                        "type": "buttons",
                        "id": "ba260020-0000-0000-0000-000000000002",
                        "value": [buttons["primary"], buttons["secondary"]],
                    },
                ],
            },
            "id": "a1b2c3d4-0001-0001-0001-000000000027",
        },
    ]


def get_banner_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage2026.objects.filter(slug="test-banner-page").first()
    if not page:
        page = FreeFormPage2026(
            slug="test-banner-page",
            title="Test Banner Page",
        )
        index_page.add_child(instance=page)

    variants = get_banner_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
