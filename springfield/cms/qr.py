# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def get_live_floating_snippet(locale):
    """Return the live QRCodeFloatingSnippet for the given locale, or None."""
    from springfield.cms.models.snippets import QRCodeFloatingSnippet

    return QRCodeFloatingSnippet.objects.filter(locale=locale).live().first()


def resolve_qr_source(page, snippet):
    resolved_image = getattr(page, "override_image", None) or getattr(snippet, "image", None)
    resolved_url = getattr(page, "override_url", None) or getattr(snippet, "url", None)

    override_default_open = getattr(page, "override_default_open", None)

    resolved_default_open = override_default_open if override_default_open is not None else getattr(snippet, "default_open", None)

    if resolved_image:
        return {"type": "image", "value": resolved_image.file.url, "open": resolved_default_open}

    if resolved_url:
        return {"type": "qr", "value": resolved_url, "open": resolved_default_open}

    return None
