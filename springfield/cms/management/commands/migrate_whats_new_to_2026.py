# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to migrate WhatsNewPage instances to WhatsNewPage2026.

Creates draft WhatsNewPage2026 pages with a '-new' slug suffix for each
published en-US WhatsNewPage and all its translations. All migrated pages
for a given source page share a new translation_key UUID.

Run this command before publish_migrated_whats_new_pages.

This command is idempotent: if a page with the '-new' slug already exists
in the same locale, it will be skipped with a warning.
"""

import copy
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Locale

from springfield.cms.models import WhatsNewPage, WhatsNewPage2026

# ---------------------------------------------------------------------------
# Button / theme migration helpers
# ---------------------------------------------------------------------------

BUTTON_BLOCK_TYPES = {"button", "uitour_button", "fxa_button", "download_button", "store_button", "focus_button"}


def migrate_button_theme(theme):
    """Map legacy button themes to 2026 equivalents.

    'tertiary' becomes '' (the default/primary theme).
    All other values are kept as-is.
    """
    if theme == "tertiary":
        return ""
    return theme


def migrate_buttons(buttons):
    """Deep-copy a list of button stream blocks and migrate their themes."""
    migrated = []
    for btn in buttons:
        btn = copy.deepcopy(btn)
        btn_type = btn.get("type")
        if btn_type in BUTTON_BLOCK_TYPES:
            value = btn.get("value", {})
            settings = value.get("settings", {})
            if "theme" in settings:
                settings["theme"] = migrate_button_theme(settings["theme"])
        migrated.append(btn)
    return migrated


# ---------------------------------------------------------------------------
# Block-level migration helpers
# ---------------------------------------------------------------------------


def migrate_inline_notification(value):
    """Migrate inline_notification → notification.

    Changes:
    - block type renamed to 'notification'
    - color 'blue' → 'purple'
    - 'inverted' field dropped
    - 'stacked' field added as False
    - icon, closable, show_to, message kept unchanged
    """
    value = copy.deepcopy(value)
    settings = value.get("settings", {})
    color = settings.get("color", "")
    if color == "blue":
        color = "purple"
    new_settings = {
        "color": color,
        "icon": settings.get("icon", ""),
        "stacked": False,
        "closable": settings.get("closable", False),
        "show_to": settings.get("show_to", {}),
    }
    return {
        "settings": new_settings,
        "message": value.get("message", ""),
    }


def migrate_intro(value):
    """Migrate intro → intro (2026).

    Changes:
    - settings.media_position 'after' → settings.layout 'right'
    - settings.media_position 'before' → settings.layout 'left'
    - settings.slim field added as False
    - button themes migrated
    """
    value = copy.deepcopy(value)
    settings = value.get("settings", {})
    media_position = settings.pop("media_position", "after")
    settings["layout"] = "right" if media_position == "after" else "left"
    settings.setdefault("slim", False)
    value["settings"] = settings
    if "buttons" in value:
        value["buttons"] = migrate_buttons(value["buttons"])
    return value


def migrate_section_cta(cta_list):
    """Migrate CTA ListBlock → StreamBlock (MixedButtonsBlock).

    Each CTABlock list item has the form {type: 'item', id: ..., value: {label, link, settings}}.
    Each is converted to a ButtonBlock stream item with theme='link', icon='', icon_position='after'.
    """
    migrated = []
    for cta_item in cta_list:
        cta_value = cta_item.get("value", {})
        old_settings = cta_value.get("settings", {})
        migrated.append(
            {
                "type": "button",
                "id": str(uuid.uuid4()),
                "value": {
                    **cta_value,
                    "settings": {
                        **old_settings,
                        "theme": "link",
                    },
                },
            }
        )
    return migrated


def migrate_card(card):
    """Migrate a single card block.

    sticker_card → outlined_card:
      - image → sticker
      - drop: tags, superheading
      - keep: settings, headline, content
      - migrate button themes

    illustration_card → illustration_card (2026):
      - drop: tags
      - add: eyebrow=''
      - keep: settings, headline, content
      - media: image → media=[{type: 'image', image: ...}]
      - buttons forced to 'link' theme (only theme supported by IllustrationCard2026Block)
    """
    card = copy.deepcopy(card)
    card_type = card.get("type")
    value = card.get("value", {})

    if card_type == "sticker_card":
        new_value = {
            "sticker": value.get("image"),
            "headline": value.get("headline", ""),
            "content": value.get("content", ""),
            "settings": value.get("settings", {}),
        }
        if "buttons" in value:
            new_value["buttons"] = migrate_buttons(value["buttons"])
        return {
            "type": "outlined_card",
            "id": card.get("id", str(uuid.uuid4())),
            "value": new_value,
        }

    elif card_type == "illustration_card":
        new_value = {
            "eyebrow": "",
            "media": [
                {
                    "type": "image",
                    "id": str(uuid.uuid4()),
                    "value": value.get("image"),
                }
            ],
            "headline": value.get("headline", ""),
            "content": value.get("content", ""),
            "settings": value.get("settings", {}),
        }
        if "buttons" in value:
            # IllustrationCard2026Block only supports the 'link' theme.
            buttons = copy.deepcopy(value["buttons"])
            for btn in buttons:
                if btn.get("type") in BUTTON_BLOCK_TYPES:
                    btn.setdefault("value", {}).setdefault("settings", {})["theme"] = "link"
            new_value["buttons"] = buttons
        return {
            "type": "illustration_card",
            "id": card.get("id", str(uuid.uuid4())),
            "value": new_value,
        }

    # Unknown card type — pass through unchanged
    return card


def migrate_section_content_block(block):
    """Migrate a single section content sub-block.

    media_content: pass through, migrating button themes.
    cards_list: migrate individual cards.
    Other types: pass through unchanged.
    """
    block = copy.deepcopy(block)
    block_type = block.get("type")
    value = block.get("value", {})

    if block_type == "media_content":
        if "buttons" in value:
            value["buttons"] = migrate_buttons(value["buttons"])
        block["value"] = value

    elif block_type == "cards_list":
        cards = value.get("cards", [])
        value["cards"] = [migrate_card(card) for card in cards]
        block["value"] = value

    return block


def migrate_section(value):
    """Migrate section → section (2026).

    Changes:
    - settings and heading kept as-is
    - CTA: ListBlock[CTABlock] → StreamBlock (MixedButtonsBlock)
    - content sub-blocks migrated individually
    """
    value = copy.deepcopy(value)

    # Migrate CTA list to stream
    if "cta" in value:
        cta_list = value.get("cta") or []
        value["cta"] = migrate_section_cta(cta_list)

    # Migrate content sub-blocks
    if "content" in value:
        value["content"] = [migrate_section_content_block(block) for block in value.get("content", [])]

    return value


def migrate_banner_or_kit_banner(value):
    """Migrate banner or kit_banner — keep all fields, migrate button themes."""
    value = copy.deepcopy(value)
    if "buttons" in value:
        value["buttons"] = migrate_buttons(value["buttons"])
    # Also check for a single button field (some variants)
    if "button" in value and isinstance(value["button"], dict):
        btn_settings = value["button"].get("settings", {})
        if "theme" in btn_settings:
            btn_settings["theme"] = migrate_button_theme(btn_settings["theme"])
    return value


def migrate_block(block):
    """Dispatch migration to the appropriate helper based on block type.

    Returns a migrated block dict, or None if the block should be skipped.
    """
    block = copy.deepcopy(block)
    block_type = block.get("type")
    value = block.get("value", {})

    if block_type == "subscription":
        return None

    elif block_type == "inline_notification":
        return {
            "type": "notification",
            "id": block.get("id", str(uuid.uuid4())),
            "value": migrate_inline_notification(value),
        }

    elif block_type == "intro":
        return {
            "type": "intro",
            "id": block.get("id", str(uuid.uuid4())),
            "value": migrate_intro(value),
        }

    elif block_type == "section":
        return {
            "type": "section",
            "id": block.get("id", str(uuid.uuid4())),
            "value": migrate_section(value),
        }

    elif block_type in ("banner", "kit_banner"):
        return {
            "type": block_type,
            "id": block.get("id", str(uuid.uuid4())),
            "value": migrate_banner_or_kit_banner(value),
        }

    # Unknown block type — pass through unchanged
    return block


def migrate_raw_content(raw_data):
    """Migrate a StreamField raw_data list from WhatsNewPage to WhatsNewPage2026.

    Skips 'subscription' blocks entirely. Returns a new list of migrated block dicts.
    """
    migrated = []
    for block in raw_data:
        result = migrate_block(block)
        if result is not None:
            migrated.append(result)
    return migrated


# ---------------------------------------------------------------------------
# Page creation helper
# ---------------------------------------------------------------------------


def create_migrated_page(source_page, new_slug, new_translation_key, stdout=None):
    """Create a draft WhatsNewPage2026 from a source WhatsNewPage.

    The new page is added as a child of the same parent as the source page,
    then its translation_key is updated to new_translation_key so all locale
    variants share a single translation group.
    """
    from springfield.cms.models import WhatsNewPage2026

    parent = source_page.get_parent()
    content = migrate_raw_content(source_page.content.raw_data)

    new_page = WhatsNewPage2026(
        title=source_page.title,
        slug=new_slug,
        version=source_page.version,
        show_qr_code_snippet=source_page.show_qr_code_snippet,
        content=content,
        locale=source_page.locale,
        live=False,
    )
    parent.add_child(instance=new_page)

    # Override translation_key after creation so all locale variants share
    # the same new key (Wagtail assigns a random key on add_child).
    WhatsNewPage2026.objects.filter(pk=new_page.pk).update(translation_key=new_translation_key)
    new_page.translation_key = new_translation_key  # Update the instance in memory as well
    new_page.save_revision()

    if stdout:
        stdout.write(f"  Created draft: locale={source_page.locale.language_code}, slug={new_slug}")

    return new_page


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Migrate published WhatsNewPage instances to draft WhatsNewPage2026 pages."

    @transaction.atomic
    def handle(self, *args, **options):
        en_us_locale = Locale.objects.get(language_code="en-US")
        source_pages = WhatsNewPage.objects.filter(locale=en_us_locale, live=True).order_by("slug")

        total_created = 0
        total_skipped = 0

        for source_page in source_pages:
            self.stdout.write(f"\nProcessing WhatsNewPage: {source_page.slug}")

            # All locale variants (en-US + translations) will share this key.
            new_translation_key = uuid.uuid4()

            # Collect all pages to migrate: en-US source + all translations (live or not)
            pages_to_migrate = [source_page] + list(source_page.get_translations(inclusive=False))

            for page in pages_to_migrate:
                new_slug = f"{page.slug}-new"

                # Skip if a page with this slug+locale already exists.
                if WhatsNewPage2026.objects.filter(slug=new_slug, locale=page.locale).exists():
                    self.stdout.write(self.style.WARNING(f"  SKIPPED (already exists): locale={page.locale.language_code}, slug={new_slug}"))
                    total_skipped += 1
                    continue

                create_migrated_page(page, new_slug, new_translation_key, stdout=self.stdout)
                total_created += 1

        self.stdout.write("")
        if total_skipped:
            self.stdout.write(self.style.WARNING(f"Skipped {total_skipped} page(s) that already existed."))
        self.stdout.write(self.style.SUCCESS(f"Successfully created {total_created} draft WhatsNewPage2026 page(s)."))
