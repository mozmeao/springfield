# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.models import FreeFormPage2026


def make_notification(block_id, message, show_to, headline=None, color="purple", icon="information", closable=False):
    return {
        "type": "notification",
        "value": {
            "settings": {
                "icon": icon,
                "color": color,
                "stacked": False,
                "closable": closable,
                "show_to": show_to,
            },
            **({"headline": f'<p data-block-key="{block_id}h">{headline}</p>'} if headline else {}),
            "message": f'<p data-block-key="{block_id}">{message}</p>',
        },
        "id": f"{block_id}-0000-0000-0000-000000000001",
    }


def make_show_to(
    platforms=None,
    firefox="",
    auth_state="",
    default_browser="",
    min_version=None,
    max_version=None,
    geo=None,
    ai_controls="",
):
    return {
        "platforms": platforms or [],
        "firefox": firefox,
        "auth_state": auth_state,
        "default_browser": default_browser,
        "min_version": min_version,
        "max_version": max_version,
        "geo": geo or [],
        "ai_controls": ai_controls,
    }


def get_conditional_display_variants() -> list[dict]:
    show_to_all = make_show_to()
    return [
        # No conditions
        make_notification(
            "cdbase01",
            "No conditions — always visible to everyone.",
            show_to_all,
            headline="Show to all",
            color="",
            icon="",
        ),
        # Platform conditions
        make_notification(
            "cdplat01",
            "Visible on Windows only.",
            make_show_to(platforms=["windows"]),
            headline="Platform: Windows",
            color="purple",
            icon="",
        ),
        make_notification(
            "cdplat02",
            "Visible on macOS only.",
            make_show_to(platforms=["osx"]),
            headline="Platform: macOS",
            color="purple",
            icon="apple",
        ),
        make_notification(
            "cdplat03",
            "Visible on Linux only.",
            make_show_to(platforms=["linux"]),
            headline="Platform: Linux",
            color="purple",
            icon="",
        ),
        make_notification(
            "cdplat04",
            "Visible on Android only.",
            make_show_to(platforms=["android"]),
            headline="Platform: Android",
            color="purple",
            icon="android",
        ),
        make_notification(
            "cdplat05",
            "Visible on iOS only.",
            make_show_to(platforms=["ios"]),
            headline="Platform: iOS",
            color="purple",
            icon="apple",
        ),
        make_notification(
            "cdplat06",
            "Visible on mobile platforms (Android and iOS).",
            make_show_to(platforms=["android", "ios"]),
            headline="Platform: Mobile (Android + iOS)",
            color="purple",
            icon="device-mobile",
        ),
        make_notification(
            "cdplat07",
            "Visible on desktop platforms (Windows, macOS, Linux).",
            make_show_to(platforms=["windows", "osx", "linux"]),
            headline="Platform: Desktop (Windows + macOS + Linux)",
            color="purple",
            icon="device-desktop-fill",
        ),
        make_notification(
            "cdplat08",
            "Visible on Windows 10 and newer only.",
            make_show_to(platforms=["windows-10-plus"]),
            headline="Platform: Windows 10+",
            color="purple",
            icon="",
        ),
        # Firefox conditions
        make_notification(
            "cdfx01",
            "Visible to Firefox users only.",
            make_show_to(firefox="is-firefox"),
            headline="Firefox users only",
            color="orange",
            icon="globe",
        ),
        make_notification(
            "cdfx02",
            "Visible to non-Firefox users only.",
            make_show_to(firefox="not-firefox"),
            headline="Non-Firefox users only",
            color="orange",
            icon="globe",
        ),
        # Auth state conditions
        make_notification(
            "cdauth01",
            "Visible to signed-in Mozilla Account users only.",
            make_show_to(auth_state="state-fxa-supported-signed-in"),
            headline="Signed-in users only",
            color="green",
            icon="single-user",
        ),
        make_notification(
            "cdauth02",
            "Visible to signed-out users only.",
            make_show_to(auth_state="state-fxa-supported-signed-out"),
            headline="Signed-out users only",
            color="green",
            icon="single-user",
        ),
        # Default browser conditions
        make_notification(
            "cddb01",
            "Visible when Firefox is already the default browser.",
            make_show_to(default_browser="is-default"),
            headline="Firefox is default browser",
            color="green",
            icon="checkmark-circle-fill",
        ),
        make_notification(
            "cddb02",
            "Visible when Firefox is not the default browser.",
            make_show_to(default_browser="is-not-default"),
            headline="Firefox is NOT default browser",
            color="orange",
            icon="warning",
        ),
        # Version conditions
        make_notification(
            "cdver01",
            "Visible to users on Firefox 150 or newer.",
            make_show_to(min_version=150),
            headline="Firefox version >= 150",
            color="purple",
            icon="information",
        ),
        make_notification(
            "cdver02",
            "Visible to users on Firefox 150 or older.",
            make_show_to(max_version=150),
            headline="Firefox version <= 150",
            color="orange",
            icon="warning",
        ),
        make_notification(
            "cdver03",
            "Visible to users running Firefox 148 through 150.",
            make_show_to(min_version=148, max_version=150),
            headline="Firefox version 148-150",
            color="purple",
            icon="information",
        ),
        # Geo conditions
        make_notification(
            "cdgeo01",
            "Visible to users in Canada only.",
            make_show_to(geo=["CA"]),
            headline="Geo: Canada only",
            color="green",
            icon="globe",
        ),
        make_notification(
            "cdgeo02",
            "Visible to users in the US, UK, or Canada.",
            make_show_to(geo=["US", "UK", "CA"]),
            headline="Geo: US, UK, CA",
            color="green",
            icon="globe",
        ),
        # AI controls conditions
        make_notification(
            "cdai01",
            "Visible when Firefox AI Controls are available.",
            make_show_to(ai_controls="available"),
            headline="AI Controls: available",
            color="green",
            icon="sparkles",
        ),
        make_notification(
            "cdai02",
            "Visible when Firefox AI Controls are unavailable.",
            make_show_to(ai_controls="unavailable"),
            headline="AI Controls: unavailable",
            color="red",
            icon="sparkles",
        ),
        # Combinations
        make_notification(
            "cdcomb02",
            "Visible to Firefox users on Windows only.",
            make_show_to(platforms=["windows"], firefox="is-firefox"),
            headline="Windows + Firefox",
            color="orange",
            icon="",
        ),
        make_notification(
            "cdcomb03",
            "Visible to German users running Firefox only.",
            make_show_to(firefox="is-firefox", geo=["DE"]),
            headline="Firefox + Germany geo",
            color="green",
            icon="globe",
        ),
        make_notification(
            "cdcomb04",
            "Visible to signed-out France users on Firefox 150 or newer.",
            make_show_to(
                firefox="is-firefox",
                auth_state="state-fxa-supported-signed-out",
                min_version=150,
                geo=["FR"],
            ),
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
    page.upper_content = blocks
    page.content = blocks
    page.save_revision().publish()
    return page
