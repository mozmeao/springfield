# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from wagtail.models import Page
from wagtail_localize.models import StringSegment, StringTranslation, Translation, TranslationSource

from springfield.cms.utils import create_page_translation_data

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Translation)
def translation_saved_signal(sender, instance, created, **kwargs):
    """Create/update PageTranslationData when a Translation is saved (created or updated)."""

    def check_after_commit():
        source_instance = instance.source.get_source_instance()

        # Only create/update PageTranslationData if this is a translation for a Page.
        # Other objects (for example, snippets), do not need PageTranslationData.
        if isinstance(source_instance, Page):
            original_translation_for_page = Page.objects.filter(translation_key=source_instance.translation_key).order_by("id").first()
            create_page_translation_data(original_translation_for_page)

    transaction.on_commit(check_after_commit)


@receiver(post_save, sender=StringTranslation)
def string_translation_saved_signal(sender, instance, created, **kwargs):
    """Create/update PageTranslationData when a StringTranslation is saved (created or updated)."""

    # Get the page through the string's segments and translation source
    # StringTranslation -> StringSegment -> TranslationSource -> Page
    try:
        segment = StringSegment.objects.get(context=instance.context, string=instance.translation_of)
        source_instance = segment.source.get_source_instance()
    except Exception as e:
        logger.exception(f"Error getting page for StringTranslation: {e}")

    # Only create/update PageTranslationData if this is a translation for a Page.
    # Other objects (for example, snippets), do not need PageTranslationData.
    if isinstance(source_instance, Page):
        original_translation_for_page = Page.objects.filter(translation_key=source_instance.translation_key).order_by("id").first()
        create_page_translation_data(original_translation_for_page)


@receiver(pre_delete, sender=StringTranslation)
def string_translation_deleted_signal(sender, instance, **kwargs):
    """Create/update PageTranslationData when a StringTranslation is deleted."""
    # Get the page through the string's segments and translation source
    # StringTranslation -> StringSegment -> TranslationSource -> Page
    try:
        segment = StringSegment.objects.get(context=instance.context, string=instance.translation_of)
        source_instance = segment.source.get_source_instance()
    except Exception as e:
        logger.exception(f"Error getting page for StringTranslation: {e}")
    else:
        # Only create/update PageTranslationData if this is a translation for a Page.
        # Other objects (for example, snippets), do not need PageTranslationData.
        if isinstance(source_instance, Page):
            original_translation_for_page = Page.objects.filter(translation_key=source_instance.translation_key).order_by("id").first()
            create_page_translation_data(original_translation_for_page)


@receiver(post_save, sender=TranslationSource)
def translation_source_saved_signal(sender, instance, created, **kwargs):
    """Create/update PageTranslationData when a TranslationSource is saved (created or updated)."""
    source_instance = instance.get_source_instance()

    # Use transaction.on_commit to run after all database changes are committed
    def check_after_commit():
        original_translation_for_page = Page.objects.filter(translation_key=source_instance.translation_key).order_by("id").first()
        # Only create/update PageTranslationData if this is a translation for a Page.
        # Other objects (for example, snippets), do not need PageTranslationData.
        if isinstance(source_instance, Page):
            create_page_translation_data(original_translation_for_page)

    transaction.on_commit(check_after_commit)


@receiver(post_save)
def page_saved_signal(sender, instance, created, **kwargs):
    """Create/update PageTranslationData when a Page is saved."""
    # Only process if it's a Page instance
    if isinstance(instance, Page) and not kwargs.get("raw", False):
        # Use transaction.on_commit to run after all database changes are committed
        def check_after_commit():
            original_translation_for_page = Page.objects.filter(translation_key=instance.translation_key).order_by("id").first()
            create_page_translation_data(original_translation_for_page)

        transaction.on_commit(check_after_commit)
