# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.fixtures.block_factories import notification_block, show_to_value
from springfield.cms.models import FreeFormPage2026


def get_bind_to_uitour_section() -> dict:
    """A section bound to UI Tour: it only shows when its UI Tour button is visible."""
    return {
        "type": "section",
        "value": {
            "settings": {
                "anchor_id": "",
                "show_to": show_to_value(bind_to_uitour=True),
            },
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="cduith1">Bound to UI Tour</p>',
                "subheading_text": "",
            },
            "content": [],
            "cta": [
                {
                    "type": "uitour_button",
                    "value": {
                        "settings": {
                            "theme": "",
                            "icon": "open-tabs",
                            "icon_position": "right",
                            "analytics_id": "cduit001-0000-0000-0000-000000000010",
                        },
                        "button_type": "open_new_tab",
                        "pretranslated_label": None,
                        "custom_label": "Open New Tab",
                    },
                    "id": "cduit001-0000-0000-0000-000000000010",
                }
            ],
        },
        "id": "cduit001-0000-0000-0000-000000000000",
    }


def get_conditional_display_variants() -> list[dict]:
    show_to_all = show_to_value()
    return [
        # No conditions
        notification_block(
            block_id="cdbase01", message="No conditions — always visible to everyone.", show_to=show_to_all, headline="Show to all", color="", icon=""
        ),
        # Platform conditions
        notification_block(
            block_id="cdplat01",
            message="Visible on Windows only.",
            show_to=show_to_value(platforms=["windows"]),
            headline="Platform: Windows",
            color="purple",
            icon="",
        ),
        notification_block(
            block_id="cdplat02",
            message="Visible on macOS only.",
            show_to=show_to_value(platforms=["osx"]),
            headline="Platform: macOS",
            color="purple",
            icon="apple",
        ),
        notification_block(
            block_id="cdplat03",
            message="Visible on Linux only.",
            show_to=show_to_value(platforms=["linux"]),
            headline="Platform: Linux",
            color="purple",
            icon="",
        ),
        notification_block(
            block_id="cdplat04",
            message="Visible on Android only.",
            show_to=show_to_value(platforms=["android"]),
            headline="Platform: Android",
            color="purple",
            icon="android",
        ),
        notification_block(
            block_id="cdplat05",
            message="Visible on iOS only.",
            show_to=show_to_value(platforms=["ios"]),
            headline="Platform: iOS",
            color="purple",
            icon="apple",
        ),
        notification_block(
            block_id="cdplat06",
            message="Visible on mobile platforms (Android and iOS).",
            show_to=show_to_value(platforms=["android", "ios"]),
            headline="Platform: Mobile (Android + iOS)",
            color="purple",
            icon="device-mobile",
        ),
        notification_block(
            block_id="cdplat07",
            message="Visible on desktop platforms (Windows, macOS, Linux).",
            show_to=show_to_value(platforms=["windows", "osx", "linux"]),
            headline="Platform: Desktop (Windows + macOS + Linux)",
            color="purple",
            icon="device-desktop-fill",
        ),
        notification_block(
            block_id="cdplat08",
            message="Visible on Windows 10 and newer only.",
            show_to=show_to_value(platforms=["windows-10-plus"]),
            headline="Platform: Windows 10+",
            color="purple",
            icon="",
        ),
        # Firefox conditions
        notification_block(
            block_id="cdfx01",
            message="Visible to Firefox users only.",
            show_to=show_to_value(firefox="is-firefox"),
            headline="Firefox users only",
            color="orange",
            icon="globe",
        ),
        notification_block(
            block_id="cdfx02",
            message="Visible to non-Firefox users only.",
            show_to=show_to_value(firefox="not-firefox"),
            headline="Non-Firefox users only",
            color="orange",
            icon="globe",
        ),
        # Auth state conditions
        notification_block(
            block_id="cdauth01",
            message="Visible to signed-in Mozilla Account users only.",
            show_to=show_to_value(auth_state="state-fxa-supported-signed-in"),
            headline="Signed-in users only",
            color="green",
            icon="single-user",
        ),
        notification_block(
            block_id="cdauth02",
            message="Visible to signed-out users only.",
            show_to=show_to_value(auth_state="state-fxa-supported-signed-out"),
            headline="Signed-out users only",
            color="green",
            icon="single-user",
        ),
        # Default browser conditions
        notification_block(
            block_id="cddb01",
            message="Visible when Firefox is already the default browser.",
            show_to=show_to_value(default_browser="is-default"),
            headline="Firefox is default browser",
            color="green",
            icon="checkmark-circle-fill",
        ),
        notification_block(
            block_id="cddb02",
            message="Visible when Firefox is not the default browser.",
            show_to=show_to_value(default_browser="is-not-default"),
            headline="Firefox is NOT default browser",
            color="orange",
            icon="warning",
        ),
        # Version conditions
        notification_block(
            block_id="cdver01",
            message="Visible to users on Firefox 150 or newer.",
            show_to=show_to_value(min_version=150),
            headline="Firefox version >= 150",
            color="purple",
            icon="information",
        ),
        notification_block(
            block_id="cdver02",
            message="Visible to users on Firefox 150 or older.",
            show_to=show_to_value(max_version=150),
            headline="Firefox version <= 150",
            color="orange",
            icon="warning",
        ),
        notification_block(
            block_id="cdver03",
            message="Visible to users running Firefox 148 through 150.",
            show_to=show_to_value(min_version=148, max_version=150),
            headline="Firefox version 148-150",
            color="purple",
            icon="information",
        ),
        # Last-session conditions
        notification_block(
            block_id="cdlast01",
            message="Visible to lapsed users — last Firefox session ended 28+ days ago.",
            show_to=show_to_value(min_days_since_last_session=28),
            headline="Lapsed: last session 28+ days ago",
            color="orange",
            icon="warning",
        ),
        notification_block(
            block_id="cdlast02",
            message="Visible to active users — last Firefox session ended within the past 27 days.",
            show_to=show_to_value(max_days_since_last_session=27),
            headline="Active: last session within 27 days",
            color="green",
            icon="checkmark-circle-fill",
        ),
        # Geo conditions
        notification_block(
            block_id="cdgeo01",
            message="Visible to users in Canada only.",
            show_to=show_to_value(geo=["CA"]),
            headline="Geo: Canada only",
            color="green",
            icon="globe",
        ),
        notification_block(
            block_id="cdgeo02",
            message="Visible to users in the US, UK, or Canada.",
            show_to=show_to_value(geo=["US", "UK", "CA"]),
            headline="Geo: US, UK, CA",
            color="green",
            icon="globe",
        ),
        # AI controls conditions
        notification_block(
            block_id="cdai01",
            message="Visible when Firefox AI Controls are available.",
            show_to=show_to_value(ai_controls="available"),
            headline="AI Controls: available",
            color="green",
            icon="sparkles",
        ),
        notification_block(
            block_id="cdai02",
            message="Visible when Firefox AI Controls are unavailable.",
            show_to=show_to_value(ai_controls="unavailable"),
            headline="AI Controls: unavailable",
            color="red",
            icon="sparkles",
        ),
        # Sample rate conditions
        notification_block(
            block_id="cdsamp01",
            message="Visible to a random 10% sample of eligible visitors.",
            show_to=show_to_value(sample_rate=10),
            headline="Sample rate: 10%",
            color="purple",
            icon="experiments",
        ),
        notification_block(
            block_id="cdsamp02",
            message="Visible to Windows users in the same 10% sample as above — every sample-rated block on "
            "a page shares one roll, so both reveal together.",
            show_to=show_to_value(platforms=["windows"], sample_rate=10),
            headline="Windows + Sample rate: 10% (combined)",
            color="purple",
            icon="experiments",
        ),
        # Combinations
        notification_block(
            block_id="cdcomb02",
            message="Visible to Firefox users on Windows only.",
            show_to=show_to_value(platforms=["windows"], firefox="is-firefox"),
            headline="Windows + Firefox",
            color="orange",
            icon="",
        ),
        notification_block(
            block_id="cdcomb03",
            message="Visible to German users running Firefox only.",
            show_to=show_to_value(firefox="is-firefox", geo=["DE"]),
            headline="Firefox + Germany geo",
            color="green",
            icon="globe",
        ),
        notification_block(
            block_id="cdcomb04",
            message="Visible to signed-out France users on Firefox 150 or newer.",
            show_to=show_to_value(firefox="is-firefox", auth_state="state-fxa-supported-signed-out", min_version=150, geo=["FR"]),
            headline="Signed-out + France + Firefox 150+ (combined)",
            color="red",
            icon="warning",
            closable=True,
        ),
    ]


def get_conditional_display_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-conditional-display",
        parent=index_page,
        defaults={
            "title": "Conditional Display",
        },
    )

    blocks = get_conditional_display_variants()
    blocks_with_uitour = [*blocks, get_bind_to_uitour_section()]
    page.upper_content = blocks_with_uitour
    page.content = blocks_with_uitour
    page.docs = (
        "<p>The Conditional Display block wraps content that should only appear for specific audiences &mdash; particular platforms "
        "(Windows, macOS, Linux, Android, iOS), browser types (Firefox / non-Firefox), authentication states (signed-in / signed-out), "
        "or default-browser status.</p>"
        "<p>Consider having a sensible &lsquo;show to all&rsquo; fallback so the page stays coherent if no condition matches.</p>"
    )
    page.save_revision().publish()
    return page
