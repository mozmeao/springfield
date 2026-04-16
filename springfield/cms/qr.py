# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def resolve_qr_source(page, snippet):
    resolved_image = page.override_image or snippet.image
    resolved_url = page.override_url or snippet.url

    # resolved_default_open = page.override_default_open if page.override_default_open is not None else snippet.default_open

    # Image takes precedence
    if resolved_image:
        return {
            "type": "image",
            "value": resolved_image.file.url,
        }

    # URL fallback → generate QR from URL
    if resolved_url:
        return {"type": "qr", "value": resolved_url}

    return None
