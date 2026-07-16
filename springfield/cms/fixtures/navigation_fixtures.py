# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Fixture for the NavigationSnippet, reproducing the current hardcoded
Browser / Features / Resources top navigation (see
``cms/includes/flare-menus/*.html``) as CMS-editable content."""

from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile

from PIL import Image
from wagtail.models import Locale

from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import NavigationSnippet, SpringfieldImage


def build_link(link_to="custom_url", custom_url="", relative_url="", new_window=False):
    return {
        "link_to": link_to,
        "page": None,
        "file": None,
        "custom_url": custom_url,
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": new_window,
        "relative_url": relative_url,
    }


def build_nav_link(label, custom_url="", icon="", icon_position="left", has_button_style=False, new_window=False, block_id="", analytics_id=None):
    return {
        "type": "link",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "link": build_link(custom_url=custom_url, new_window=new_window),
            "icon": icon,
            "icon_position": icon_position,
            "has_button_style": has_button_style,
            "analytics_id": analytics_id or str(uuid4()),
        },
        "id": block_id,
    }


def build_separator(block_id=""):
    return {"type": "separator", "value": None, "id": block_id}


def build_column(children, block_id=""):
    return {"type": "item", "value": children, "id": block_id}


def build_folder(label, columns, block_id=""):
    return {
        "type": "folder",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "sub_items": columns,
        },
        "id": block_id,
    }


def build_top_level_link(label, custom_url="", new_window=False, block_id="", analytics_id=None):
    return {
        "type": "top_level_link",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "link": build_link(custom_url=custom_url, new_window=new_window),
            "analytics_id": analytics_id or str(uuid4()),
        },
        "id": block_id,
    }


def get_navigation_variants() -> list[dict]:
    """The current Browser / Features / Resources navigation as snippet items.

    Exercises every block option: folders with one or more columns, plain links
    with icons, horizontal rules between link groups, external links (which get
    the external-link icon in the frontend), and a button-style link.
    """
    return [
        build_folder(
            "Browser",
            columns=[
                build_column(
                    [
                        build_nav_link(
                            "Mobile", custom_url="/browsers/mobile/", icon="device-mobile", block_id="2026nav0-0000-0000-0000-000000000101"
                        ),
                        build_nav_link("Enterprise", custom_url="/enterprise/", icon="globe", block_id="2026nav0-0000-0000-0000-000000000102"),
                        build_separator(block_id="2026nav0-0000-0000-0000-000000000103"),
                        build_nav_link("What's New", custom_url="/whatsnew/", icon="bookmark-fill", block_id="2026nav0-0000-0000-0000-000000000104"),
                        build_nav_link("What's Next", custom_url="/whatsnext/", icon="calendar", block_id="2026nav0-0000-0000-0000-000000000105"),
                        build_separator(block_id="2026nav0-0000-0000-0000-000000000106"),
                        build_nav_link(
                            "Extensions & Themes",
                            custom_url="https://addons.mozilla.org/firefox/",
                            icon="extension-fill",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000107",
                        ),
                        build_nav_link(
                            "Support",
                            custom_url="https://support.mozilla.org/",
                            icon="avatar-info-circle-fill",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000108",
                        ),
                        build_separator(block_id="2026nav0-0000-0000-0000-000000000109"),
                        build_nav_link(
                            "Download Firefox", custom_url="/download/", has_button_style=True, block_id="2026nav0-0000-0000-0000-000000000110"
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000100",
                ),
            ],
            block_id="2026nav0-0000-0000-0000-000000000001",
        ),
        build_folder(
            "Features",
            columns=[
                build_column(
                    [
                        build_nav_link(
                            "Protection", custom_url="/features/protection/", icon="lock", block_id="2026nav0-0000-0000-0000-000000000201"
                        ),
                        build_nav_link(
                            "Control", custom_url="/features/control/", icon="cursor-arrow", block_id="2026nav0-0000-0000-0000-000000000202"
                        ),
                        build_nav_link("Focus", custom_url="/features/focus/", icon="search", block_id="2026nav0-0000-0000-0000-000000000203"),
                        build_nav_link(
                            "About Firefox features",
                            custom_url="/features/",
                            icon="forward",
                            icon_position="right",
                            block_id="2026nav0-0000-0000-0000-000000000204",
                        ),
                        build_separator(block_id="2026nav0-0000-0000-0000-000000000205"),
                        build_nav_link(
                            "All features", custom_url="/features/all/", has_button_style=True, block_id="2026nav0-0000-0000-0000-000000000206"
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000200",
                ),
                build_column(
                    [
                        build_nav_link(
                            "Private browsing",
                            custom_url="/features/private-browsing/",
                            icon="shield",
                            block_id="2026nav0-0000-0000-0000-000000000211",
                        ),
                        build_nav_link(
                            "Password manager", custom_url="/features/password-manager/", icon="lock", block_id="2026nav0-0000-0000-0000-000000000212"
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000210",
                ),
            ],
            block_id="2026nav0-0000-0000-0000-000000000002",
        ),
        build_folder(
            "Resources",
            columns=[
                build_column(
                    [
                        build_nav_link(
                            "Data Protection", custom_url="/privacy/firefox/", icon="lock", block_id="2026nav0-0000-0000-0000-000000000301"
                        ),
                        build_nav_link(
                            "Blog",
                            custom_url="https://blog.mozilla.org/en/category/firefox/",
                            icon="newsfeed",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000302",
                        ),
                        build_nav_link(
                            "Podcast",
                            custom_url="https://www.youtube.com/@firefox/podcasts",
                            icon="microphone-true",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000303",
                        ),
                        build_separator(block_id="2026nav0-0000-0000-0000-000000000304"),
                        build_nav_link(
                            "Newsletter", custom_url="/newsletter/", icon="notifications-true", block_id="2026nav0-0000-0000-0000-000000000305"
                        ),
                        build_nav_link(
                            "Release Notes", custom_url="/firefox/notes/", icon="reader-view-fill", block_id="2026nav0-0000-0000-0000-000000000306"
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000300",
                ),
            ],
            block_id="2026nav0-0000-0000-0000-000000000003",
        ),
        build_top_level_link(
            "Pricing",
            custom_url="/pricing/",
            block_id="2026nav0-0000-0000-0000-000000000004",
        ),
    ]


def build_logo_image(title, color) -> SpringfieldImage:
    """Create (idempotently) a small placeholder logo image within the size cap."""
    buffer = BytesIO()
    Image.new("RGB", (240, 60), color).save(buffer, format="PNG")
    buffer.seek(0)
    image, _ = SpringfieldImage.objects.get_or_create(
        title=title,
        defaults={"file": ContentFile(buffer.read(), f"{title}.png")},
    )
    return image


def get_navigation_snippet() -> NavigationSnippet:
    locale = Locale.get_default()
    snippet, _ = NavigationSnippet.objects.update_or_create(
        id=settings.PLACEHOLDER_SNIPPET_ID,
        defaults={
            "locale": locale,
            "name": "Main navigation",
            "items": get_navigation_variants(),
            "logo": build_logo_image("Placeholder Navigation Logo", (117, 79, 224)),
            "logo_dark": build_logo_image("Placeholder Navigation Logo (Dark)", (255, 138, 80)),
            "logo_link": [("link", build_link(link_to="relative_url", relative_url="/"))],
            "cta_button": [("button", [get_button_variants()["primary"]])],
        },
    )
    snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet
