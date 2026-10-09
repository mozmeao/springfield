# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Fixture for the NavigationSnippet, reproducing the current hardcoded
Browser / Features / Resources top navigation (see
``cms/includes/flare-menus/*.html``) as CMS-editable content."""

from io import BytesIO

from django.core.files.base import ContentFile

from PIL import Image
from wagtail.models import Locale

from springfield.cms.fixtures.block_factories import link_value, nav_column, nav_folder, nav_link, nav_separator, nav_top_level_link
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import NavigationSnippet, SpringfieldImage

NAVIGATION_SNIPPET_TRANSLATION_KEY = "1828921a-934b-4e82-832f-d5f3fade9c79"


def get_navigation_variants() -> list[dict]:
    """The current Browser / Features / Resources navigation as snippet items.

    Exercises every block option: folders with one or more columns, plain links
    with icons, horizontal rules between link groups, external links (which get
    the external-link icon in the frontend), and a button-style link.
    """
    return [
        nav_folder(
            label="Browser",
            columns=[
                nav_column(
                    children=[
                        nav_link(
                            label="Mobile", custom_url="/browsers/mobile/", icon="device-mobile", block_id="2026nav0-0000-0000-0000-000000000101"
                        ),
                        nav_link(label="Enterprise", custom_url="/enterprise/", icon="globe", block_id="2026nav0-0000-0000-0000-000000000102"),
                        nav_separator(block_id="2026nav0-0000-0000-0000-000000000103"),
                        nav_link(label="What's New", custom_url="/whatsnew/", icon="bookmark-fill", block_id="2026nav0-0000-0000-0000-000000000104"),
                        nav_link(label="What's Next", custom_url="/whatsnext/", icon="calendar", block_id="2026nav0-0000-0000-0000-000000000105"),
                        nav_separator(block_id="2026nav0-0000-0000-0000-000000000106"),
                        nav_link(
                            label="Extensions & Themes",
                            custom_url="https://addons.mozilla.org/firefox/",
                            icon="extension-fill",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000107",
                        ),
                        nav_link(
                            label="Support",
                            custom_url="https://support.mozilla.org/",
                            icon="avatar-info-circle-fill",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000108",
                        ),
                        nav_separator(block_id="2026nav0-0000-0000-0000-000000000109"),
                        nav_link(
                            label="Download Firefox", custom_url="/download/", has_button_style=True, block_id="2026nav0-0000-0000-0000-000000000110"
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000100",
                ),
            ],
            block_id="2026nav0-0000-0000-0000-000000000001",
        ),
        nav_folder(
            label="Features",
            columns=[
                nav_column(
                    children=[
                        nav_link(
                            label="Protection", custom_url="/features/protection/", icon="lock-fill", block_id="2026nav0-0000-0000-0000-000000000201"
                        ),
                        nav_link(
                            label="Control", custom_url="/features/control/", icon="cursor-arrow", block_id="2026nav0-0000-0000-0000-000000000202"
                        ),
                        nav_link(label="Focus", custom_url="/features/focus/", icon="search", block_id="2026nav0-0000-0000-0000-000000000203"),
                        nav_link(
                            label="About Firefox features",
                            custom_url="/features/",
                            icon="forward",
                            icon_position="right",
                            block_id="2026nav0-0000-0000-0000-000000000204",
                        ),
                        nav_separator(block_id="2026nav0-0000-0000-0000-000000000205"),
                        nav_link(
                            label="All features", custom_url="/features/all/", has_button_style=True, block_id="2026nav0-0000-0000-0000-000000000206"
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000200",
                ),
                nav_column(
                    children=[
                        nav_link(
                            label="Private browsing",
                            custom_url="/features/private-browsing/",
                            icon="shield",
                            block_id="2026nav0-0000-0000-0000-000000000211",
                        ),
                        nav_link(
                            label="Password manager",
                            custom_url="/features/password-manager/",
                            icon="lock",
                            block_id="2026nav0-0000-0000-0000-000000000212",
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000210",
                ),
            ],
            block_id="2026nav0-0000-0000-0000-000000000002",
        ),
        nav_folder(
            label="Resources",
            columns=[
                nav_column(
                    children=[
                        nav_link(
                            label="Data Protection", custom_url="/privacy/firefox/", icon="lock-fill", block_id="2026nav0-0000-0000-0000-000000000301"
                        ),
                        nav_link(
                            label="Blog",
                            custom_url="https://blog.mozilla.org/en/category/firefox/",
                            icon="reader-view-fill",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000302",
                        ),
                        nav_link(
                            label="Podcast",
                            custom_url="https://www.youtube.com/@firefox/podcasts",
                            icon="microphone-true",
                            new_window=True,
                            block_id="2026nav0-0000-0000-0000-000000000303",
                        ),
                        nav_separator(block_id="2026nav0-0000-0000-0000-000000000304"),
                        nav_link(
                            label="Newsletter", custom_url="/newsletter/", icon="notifications-true", block_id="2026nav0-0000-0000-0000-000000000305"
                        ),
                        nav_link(
                            label="Release Notes",
                            custom_url="/firefox/notes/",
                            icon="reader-view-fill",
                            block_id="2026nav0-0000-0000-0000-000000000306",
                        ),
                    ],
                    block_id="2026nav0-0000-0000-0000-000000000300",
                ),
            ],
            block_id="2026nav0-0000-0000-0000-000000000003",
        ),
        nav_top_level_link(label="Pricing", custom_url="/pricing/", block_id="2026nav0-0000-0000-0000-000000000004"),
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
    snippet, _ = NavigationSnippet.objects.update_or_create(
        translation_key=NAVIGATION_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "name": "Main navigation",
            "items": get_navigation_variants(),
            "logo": build_logo_image("Placeholder Navigation Logo", (117, 79, 224)),
            "logo_alt": "Firefox",
            "logo_dark": build_logo_image("Placeholder Navigation Logo (Dark)", (255, 138, 80)),
            "logo_link": [("link", link_value(link_to="relative_url", relative_url="/"))],
            "cta_button": [("button", [get_button_variants()["primary"]])],
        },
    )
    snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet
