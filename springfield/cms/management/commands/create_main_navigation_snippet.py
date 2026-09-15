# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to create the main navigation snippet and its translations.

Reproduces the hardcoded Browser / Features / Resources header navigation
(``cms/includes/flare-menus/*.html``) as a CMS-editable NavigationSnippet.
"""

from pathlib import Path
from uuid import UUID, uuid5

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.cms.navigation_strings import NAVIGATION_LABELS, NAVIGATION_TRANSLATIONS

# Stable identifiers. Do not change them — translation_key is what wagtail_localize
# uses to link the English snippet to its translated copies, and the block IDs keep
# re-runs from replacing content the CMS has already translated.
SNIPPET_TRANSLATION_KEY = "c0ffee00-0b8a-4c1e-9b0e-3f1d2a5e7c41"
BLOCK_ID_NAMESPACE = UUID("1f3b6d24-7a05-4e8c-9d2f-8b4c6e0a1573")

SNIPPET_NAME = "Main navigation"

# External destinations, which have no CMS page to link to. The podcast link carries
# its own campaign parameters because add_utm_parameters only rewrites Mozilla-owned
# domains, and youtube.com is not one of them.
ADDONS_URL = "https://addons.mozilla.org/firefox/"
SUPPORT_URL = "https://support.mozilla.org/"
BLOG_URL = "https://blog.mozilla.org/en/category/firefox/"
PODCAST_URL = "https://www.youtube.com/@firefox/podcasts?utm_source=www.firefox.com&utm_medium=referral&utm_campaign=nav&utm_content=resources"


def block_id(key):
    """A stable block ID derived from a key such as ``browser.mobile``."""
    return str(uuid5(BLOCK_ID_NAMESPACE, key))


def find_live_page_for_path(path, root_page):
    """Return the live CMS page served at a site-relative path, or None if the path is a static view."""
    # Inline import: migration modules are loaded before the app registry is ready.
    from wagtail.models import Page

    return Page.objects.live().filter(url_path=f"{root_page.url_path}{path.strip('/')}/", locale_id=root_page.locale_id).first()


def build_empty_link():
    return {
        "link_to": "",
        "page": None,
        "file": None,
        "custom_url": "",
        "relative_url": "",
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": False,
    }


def build_internal_link(path, root_page):
    """Link to the CMS page published at ``path``, falling back to a relative URL for static pages."""
    link = build_empty_link()
    page = find_live_page_for_path(path, root_page)
    if page:
        link["link_to"] = "page"
        link["page"] = page.pk
    else:
        link["link_to"] = "relative_url"
        link["relative_url"] = path
    return link


def build_external_link(url):
    link = build_empty_link()
    link["link_to"] = "custom_url"
    link["custom_url"] = url
    return link


def build_nav_link(key, label, link, icon="", icon_position="left", has_button_style=False):
    return {
        "type": "link",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "link": link,
            "icon": icon,
            "icon_position": icon_position,
            "has_button_style": has_button_style,
            "analytics_id": block_id(f"{key}.analytics"),
        },
        "id": block_id(key),
    }


def build_whats_new_or_next_link(key, block_type, label, icon):
    return {
        "type": block_type,
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "icon": icon,
            "icon_position": "left",
            "has_button_style": False,
            "analytics_id": block_id(f"{key}.analytics"),
        },
        "id": block_id(key),
    }


def build_separator(key):
    return {"type": "separator", "value": None, "id": block_id(key)}


def build_folder(key, label, columns):
    return {
        "type": "folder",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "sub_items": [{"type": "item", "value": column, "id": block_id(f"{key}.column-{index}")} for index, column in enumerate(columns, 1)],
        },
        "id": block_id(key),
    }


def count_page_links(items):
    return sum(
        1
        for folder in items
        for column in folder["value"]["sub_items"]
        for child in column["value"]
        if child["type"] == "link" and child["value"]["link"]["link_to"] == "page"
    )


def build_navigation_items(root_page):
    return [
        build_folder(
            "browser",
            NAVIGATION_LABELS["navigation-browser"],
            columns=[
                [
                    build_nav_link(
                        "browser.mobile",
                        NAVIGATION_LABELS["navigation-mobile"],
                        build_internal_link("/mobile/", root_page),
                        icon="device-mobile",
                    ),
                    build_nav_link(
                        "browser.enterprise",
                        NAVIGATION_LABELS["navigation-enterprise"],
                        build_internal_link("/browsers/enterprise/", root_page),
                        icon="globe",
                    ),
                    build_separator("browser.separator-1"),
                    build_whats_new_or_next_link(
                        "browser.whats-new",
                        "whats_new_link",
                        NAVIGATION_LABELS["navigation-whats-new"],
                        icon="bookmark-fill",
                    ),
                    build_whats_new_or_next_link(
                        "browser.whats-next",
                        "whats_next_link",
                        NAVIGATION_LABELS["navigation-whats-next"],
                        icon="calendar",
                    ),
                    build_separator("browser.separator-2"),
                    build_nav_link(
                        "browser.extensions-and-themes",
                        NAVIGATION_LABELS["navigation-extensions-and-themes"],
                        build_external_link(ADDONS_URL),
                        icon="extension-fill",
                    ),
                    build_nav_link(
                        "browser.support",
                        NAVIGATION_LABELS["navigation-support"],
                        build_external_link(SUPPORT_URL),
                        icon="avatar-info-circle-fill",
                    ),
                    build_separator("browser.separator-3"),
                    build_nav_link(
                        "browser.download",
                        NAVIGATION_LABELS["navigation-download-firefox"],
                        build_internal_link("/download/", root_page),
                        has_button_style=True,
                    ),
                ],
            ],
        ),
        build_folder(
            "features",
            NAVIGATION_LABELS["navigation-features"],
            columns=[
                [
                    build_nav_link(
                        "features.protection",
                        NAVIGATION_LABELS["navigation-protection"],
                        build_internal_link("/features/protection/", root_page),
                        icon="lock-fill",
                    ),
                    build_nav_link(
                        "features.control",
                        NAVIGATION_LABELS["navigation-control"],
                        build_internal_link("/features/control/", root_page),
                        icon="cursor-arrow",
                    ),
                    build_nav_link(
                        "features.focus",
                        NAVIGATION_LABELS["navigation-focus"],
                        build_internal_link("/features/focus/", root_page),
                        icon="search",
                    ),
                    build_nav_link(
                        "features.index",
                        NAVIGATION_LABELS["navigation-about-firefox-features"],
                        build_internal_link("/features/", root_page),
                        icon="forward",
                        icon_position="right",
                    ),
                    build_separator("features.separator-1"),
                    build_nav_link(
                        "features.all",
                        NAVIGATION_LABELS["navigation-features-all"],
                        build_internal_link("/features/all/", root_page),
                        has_button_style=True,
                    ),
                ],
            ],
        ),
        build_folder(
            "resources",
            NAVIGATION_LABELS["navigation-resources"],
            columns=[
                [
                    build_nav_link(
                        "resources.data-protection",
                        NAVIGATION_LABELS["navigation-data-protection"],
                        build_internal_link("/user-privacy/", root_page),
                        icon="lock-fill",
                    ),
                    build_nav_link(
                        "resources.blog",
                        NAVIGATION_LABELS["navigation-blog"],
                        build_external_link(BLOG_URL),
                        icon="reader-view-fill",
                    ),
                    build_nav_link(
                        "resources.podcast",
                        NAVIGATION_LABELS["navigation-podcast"],
                        build_external_link(PODCAST_URL),
                        icon="microphone-true",
                    ),
                    build_separator("resources.separator-1"),
                    build_nav_link(
                        "resources.newsletter",
                        NAVIGATION_LABELS["navigation-newsletter"],
                        build_internal_link("/newsletter/", root_page),
                        icon="notifications-true",
                    ),
                    build_nav_link(
                        "resources.release-notes",
                        NAVIGATION_LABELS["navigation-release-notes"],
                        build_internal_link("/firefox/notes/", root_page),
                        icon="reader-view-fill",
                    ),
                ],
            ],
        ),
    ]


class Command(BaseCommand):
    help = "Create the main navigation snippet and import its translations."

    @transaction.atomic
    def handle(self, *args, **options):
        # Inline imports: migration modules load before the app registry is ready.
        from wagtail.models import Locale, Site
        from wagtail_localize.models import Translation, TranslationSource

        from springfield.cms.ftl_parser import build_po_from_ftl, build_text_to_msgid_mapping
        from springfield.cms.models import NavigationSnippet

        # Create the English snippet

        self.stdout.write("Phase 1: Creating the navigation snippet...\n")

        site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
        if not site:
            self.stdout.write(self.style.WARNING("  No default site — skipping.\n"))
            return

        locale_en_us = Locale.objects.get(language_code="en-US")
        root_page = site.root_page
        items = build_navigation_items(root_page)

        snippet, _ = NavigationSnippet.objects.update_or_create(
            translation_key=SNIPPET_TRANSLATION_KEY,
            locale=locale_en_us,
            defaults={"name": SNIPPET_NAME, "items": items, "live": True},
        )
        snippet.save_revision().publish()

        self.stdout.write(f"  {snippet} (id={snippet.pk}), {count_page_links(items)} links resolved to CMS pages\n")

        # Register the TranslationSource and fix schema_version

        self.stdout.write("Phase 2: Registering the TranslationSource...\n")

        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        migration_names = sorted(f.stem for f in migrations_dir.glob("0*.py"))
        latest_schema_version = migration_names[-1] if migration_names else ""

        source, created = TranslationSource.get_or_create_from_instance(snippet)
        if not created:
            source.update_from_db()
            source.refresh_segments()
        source.schema_version = latest_schema_version
        source.save(update_fields=["schema_version"])

        self.stdout.write(f"  {'Created' if created else 'Refreshed'} TranslationSource, schema_version={latest_schema_version}\n")

        # Import the translated labels
        self.stdout.write("Phase 3: Importing translations...\n")

        text_to_msgid = build_text_to_msgid_mapping(NAVIGATION_LABELS)

        for target_locale in Locale.objects.exclude(language_code="en-US"):
            translated_labels = NAVIGATION_TRANSLATIONS.get(target_locale.language_code)
            if not translated_labels:
                continue

            translation, _ = Translation.objects.get_or_create(source=source, target_locale=target_locale)
            po = build_po_from_ftl(translation, text_to_msgid, translated_labels)
            # build_po_from_ftl always returns a polib.POFile. An empty
            # file is falsy because POFile is a list subclass, so check truthiness.
            if po:
                translation.import_po(
                    po,
                    delete=False,  # idempotent: don't wipe existing translations
                    translation_type="manual",
                    tool_name="ftl_import",
                )
                translation.save_target(publish=True)
                self.stdout.write(f"  {target_locale.language_code}: {len(po)} strings imported\n")

        self.stdout.write(self.style.SUCCESS("\nDone.\n"))
