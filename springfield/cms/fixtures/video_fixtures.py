# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings


def get_video_variants():
    return {
        "youtube": {
            "type": "video",
            "value": {
                "video_url": "https://www.youtube.com/watch?v=F-nFQryDB0s&list=PLFlAJDI87Jg3WeEerUpaKQNaYoDlIwPbG",
                "alt": "Describe the video here.",
                "poster": settings.PLACEHOLDER_IMAGE_ID,
            },
            "id": "5d272340-402a-4f4c-9a4f-b4c308207452",
        },
        "cdn": {
            "type": "video",
            "value": {
                "video_url": "https://assets.mozilla.net/video/red-pandas.webm",
                "alt": "Describe the video here.",
                "poster": settings.PLACEHOLDER_IMAGE_ID,
            },
            "id": "5bd338e8-aa03-4a03-8506-68124b4ad724",
        },
        "animation": {
            "type": "animation",
            "value": {
                "video_url": "https://assets.mozilla.net/video/red-pandas.webm",
                "alt": "Describe the video here.",
                "poster": settings.PLACEHOLDER_IMAGE_ID,
                "playback": "autoplay_loop",
            },
            "id": "36a5f8ee-f971-4498-9ede-d74e89e83b1d",
        },
        "animation_click": {
            "type": "animation",
            "value": {
                "video_url": "https://assets.mozilla.net/video/red-pandas.webm",
                "alt": "Describe the video here.",
                "poster": settings.PLACEHOLDER_IMAGE_ID,
                "playback": "click",
            },
            "id": "c51d8984-fe50-4641-b74f-22b38bb0f823",
        },
        "animation_autoplay_once": {
            "type": "animation",
            "value": {
                "video_url": "https://assets.mozilla.net/video/red-pandas.webm",
                "alt": "Describe the video here.",
                "poster": settings.PLACEHOLDER_IMAGE_ID,
                "playback": "autoplay_once",
            },
            "id": "2b4aa347-6c38-4d2b-88df-dfbff095ad45",
        },
    }
