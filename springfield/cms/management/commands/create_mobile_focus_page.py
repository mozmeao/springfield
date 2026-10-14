# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Create the draft CMS scaffold for /mobile/focus/, from firefox/browsers/mobile/focus-flare.html.

English text is copied from the *values* in l10n/en/firefox/browsers/mobile/focus.ftl, not from the
message ids. build_text_to_msgid_mapping() matches translations by normalized English text, so text
that differs from the FTL value — even by a curly apostrophe — goes untranslated in silence.
"""

from springfield.cms.management.commands._page_scaffold import (
    FTL_TARGET_LOCALE_CODES,
    CreatePageCommand,
    PageSpec,
    build_rich_text,
    import_static_image,
)
from springfield.cms.models import FreeFormPage2026

FOCUS_IMAGE_DIRECTORY = "img/firefox/browsers/mobile/focus"

# The hero's QR card, from includes/s2d-focus.html. German points at the Klar listing instead,
# which is a per-locale override an editor makes on the German page.
FOCUS_QR_URL = "https://www.firefox.com/browsers/mobile/app/?product=focus&campaign=firefox-browsers-mobile-focus"
KLAR_QR_URL = "https://www.firefox.com/browsers/mobile/app/?product=klar&campaign=firefox-browsers-mobile-klar"


def import_focus_image(file_name: str, title: str):
    """Every Focus illustration carries aria-hidden in focus-flare.html, so each is decorative."""
    return import_static_image(static_path=f"{FOCUS_IMAGE_DIRECTORY}/{file_name}", title=title, is_decorative=True)


def build_store_buttons(block_id: str) -> dict:
    """Custom labels, because neither existing PretranslatedPhrase names Focus."""
    return {
        "type": "buttons",
        "id": f"{block_id}-buttons",
        "value": [
            {
                "type": "focus_button",
                "id": f"{block_id}-{store}",
                "value": {"store": store, "custom_label": "Get Firefox Focus", "settings": {}},
            }
            for store in ("android", "ios")
        ],
    }


def build_media(block_id: str, media_image, qr_code_data: str) -> list[dict]:
    """The intro's media slot holds at most one child: an illustration, or the hero's QR code."""
    if qr_code_data:
        # No background image: s2d-focus.html shows a bare QR code, and .fl-qr-code:only-child
        # sizes it for exactly this case.
        return [{"type": "qr_code", "id": f"{block_id}-media", "value": {"data": qr_code_data, "background": None}}]
    if media_image is not None:
        return [{"type": "image", "id": f"{block_id}-media", "value": {"image": media_image.pk, "settings": {}}}]
    return []


def build_intro_block(
    *,
    block_id: str,
    heading: str,
    subheading: str,
    layout: str,
    full_width: bool = False,
    media_image=None,
    qr_code_data: str = "",
    with_store_buttons: bool = False,
) -> dict:
    return {
        "type": "intro",
        "id": block_id,
        "value": {
            # anchor_id is a CharBlock(required=False): omitting it stores no value, and wagtail-localize's
            # segment extractor hands the resulting None straight to StringSegmentValue, which rejects it.
            "settings": {"slim": True, "layout": layout, "full_width": full_width, "anchor_id": ""},
            "heading": {
                "heading_text": build_rich_text(f"{block_id}-h", heading),
                "subheading_text": build_rich_text(f"{block_id}-s", subheading),
            },
            "media": build_media(block_id, media_image, qr_code_data),
            "content": [build_store_buttons(block_id)] if with_store_buttons else [],
        },
    }


def build_fields() -> dict:
    return {
        "show_nav_cta": False,
        "show_navigation": True,
        "show_pre_footer": False,
        "upper_content": [
            build_intro_block(
                block_id="focus-hero",
                heading="Simply private mobile browsing",
                subheading=(
                    "Firefox Focus is your dedicated privacy browser with automatic tracking protection. "
                    "With Focus, your pages load faster and your data stays private."
                ),
                layout="right",
                qr_code_data=FOCUS_QR_URL,
                with_store_buttons=True,
            ),
        ],
        "content": [
            build_intro_block(
                block_id="focus-delete-history",
                heading="Delete your history",
                subheading=(
                    "Easily erase your history, passwords and cookies, so unwanted ads don’t follow you around online. "
                    "Just tap the erase button on the search field and it’s gone."
                ),
                layout="left",
                media_image=import_focus_image("disappear-your-history.svg", "Firefox Focus history-erasing illustration"),
            ),
            build_intro_block(
                block_id="focus-private-mode",
                heading="Take private mode to the next level",
                subheading=(
                    "“Private browsing” on most browsers isn’t really all that private. Firefox Focus offers next-level "
                    "privacy by default and it’s backed by Mozilla, the non-profit that fights for your rights on the web."
                ),
                layout="right",
                media_image=import_focus_image("take-private-mode-to-the-next-level.svg", "Firefox Focus private mode illustration"),
            ),
            build_intro_block(
                block_id="focus-tracking-protection",
                heading="Tracking protection",
                subheading=(
                    "Firefox Focus blocks a wide range of common trackers by default including social trackers "
                    "and those sticky ones that come from things like Facebook ads."
                ),
                layout="left",
                media_image=import_focus_image("tracking-protection.svg", "Firefox Focus tracking protection illustration"),
            ),
            build_intro_block(
                block_id="focus-see-it-all",
                heading="See it all faster",
                subheading=(
                    "Focus removes trackers so the pages you’re viewing require less data and load much faster. "
                    "Also, pin up to four shortcuts on your home screen and get to your favorite site even quicker "
                    "without typing anything."
                ),
                layout="right",
                media_image=import_focus_image("see-it-all-faster.svg", "Firefox Focus page-speed illustration"),
            ),
            build_intro_block(
                block_id="focus-made-by-mozilla",
                heading="Made by Mozilla",
                subheading="We believe everyone should have control over their lives online. That’s what we’ve been fighting for since 1998.",
                layout="vertical",
                full_width=True,
                with_store_buttons=True,
            ),
        ],
    }


class Command(CreatePageCommand):
    help = "Create the draft CMS scaffold for /mobile/focus/."

    spec = PageSpec(
        slug="focus",
        page_model=FreeFormPage2026,
        parent_slugs=("mobile",),
        title="Firefox Focus",
        ftl_relative_paths=("firefox/browsers/mobile/focus.ftl",),
        target_locale_codes=FTL_TARGET_LOCALE_CODES,
        build_fields=build_fields,
        editor_notes=(
            "check the imported images carry useful alt text — decorative ones were imported as decorative",
            "the store buttons render as plain buttons, not the Google Play / App Store badges — the only block "
            "that draws the badges, store_button, is hardcoded to the Firefox app rather than Focus",
            "the QR card loses its 'Get Firefox Focus' heading and 'Scan the QR code to get started' line — the "
            "qr_code block holds only the encoded URL and an optional background image. The mobile_store_qr_code "
            "block does render a heading above a QR, but as its own full-width section rather than the hero's media",
            f"point the German page's QR code at the Klar listing: {KLAR_QR_URL}",
        ),
    )
