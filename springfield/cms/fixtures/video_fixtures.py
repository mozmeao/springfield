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
            },
            "id": "5bd338e8-aa03-4a03-8506-68124b4ad724",
        },
    }
