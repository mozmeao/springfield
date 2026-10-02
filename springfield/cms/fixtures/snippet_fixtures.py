# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.text import slugify

from wagtail.models import Locale

from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
from springfield.cms.models import (
    BannerSnippet,
    PreFooterCTAFormSnippet,
    PreFooterCTASnippet,
    PretranslatedPhrase,
    QRCodeSnippet,
    SetAsDefaultSnippet,
    Tag,
)
from springfield.cms.models.base import QROpenBehavior
from springfield.cms.models.snippets import PencilBannerSnippet, QRCodeFloatingSnippet, ScrollToSeeMoreSnippet

BANNER_SNIPPET_TRANSLATION_KEY = "99d6da4a-e502-4d92-8850-f8ee9cf972c5"
PRE_FOOTER_CTA_SNIPPET_TRANSLATION_KEY = "15e87b5c-d265-463f-adbb-b3f61d827d4e"
PRE_FOOTER_CTA_FORM_SNIPPET_TRANSLATION_KEY = "95e69476-f4ed-44cc-8e20-238246109841"
QR_CODE_SNIPPET_TRANSLATION_KEY = "1caf4d65-684e-4f92-97e8-e23a1b02a1d7"
SET_AS_DEFAULT_SNIPPET_TRANSLATION_KEY = "e3fe81e2-5447-488a-beb3-3a273d3ee529"
FLOATING_QR_CODE_SNIPPET_TRANSLATION_KEY = "f60b64c5-bdda-48bd-8116-4d5ba2787378"
PENCIL_BANNER_SNIPPET_TRANSLATION_KEY = "de9c9b5e-030c-488e-8d70-d33064e563a5"
SCROLL_TO_SEE_MORE_SNIPPET_TRANSLATION_KEY = "ef420de9-c4e4-47ee-b9c9-340ef3a84133"


def get_banner_snippet() -> BannerSnippet:
    snippet, _ = BannerSnippet.objects.update_or_create(
        translation_key=BANNER_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "kit_theme": True,
            "heading": '<p data-block-key="c1bc4d7eadf0">Take your tabs, history and passwords wherever you go</p>',
            "content": '<p data-block-key="0b474f02">Your passwords, bookmarks, and preferences sync seamlessly across all your devices, '
            "so you can pick up where you left off. </p>",
            "qr_code": "QR Code Content",
        },
    )
    return snippet


def get_pre_footer_cta_snippet() -> PreFooterCTASnippet:
    snippet, _ = PreFooterCTASnippet.objects.update_or_create(
        translation_key=PRE_FOOTER_CTA_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "label": "Get Firefox",
            "analytics_id": "123e4567-e89b-12d3-a456-426614174000",
        },
    )
    return snippet


def get_pre_footer_cta_form_snippet() -> PreFooterCTAFormSnippet:
    snippet, _ = PreFooterCTAFormSnippet.objects.update_or_create(
        translation_key=PRE_FOOTER_CTA_FORM_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "heading": '<p data-block-key="c1bc4d7eadf0">Keep up with all things Firefox</p>',
            "subheading": '<p data-block-key="0b474f02">Get how-tos, advice and news to make your Firefox experience work best for you.</p>',
            "analytics_id": "0b474f02-d3fd-4d86-83cd-c1bc4d7eadf0",
        },
    )
    return snippet


def get_qr_code_snippet() -> QRCodeSnippet:
    snippet, _ = QRCodeSnippet.objects.update_or_create(
        translation_key=QR_CODE_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "heading": '<p data-block-key="c1bc4d7eadf0">Get Firefox on your phone</p>',
            "qr_code": "https://www.firefox.com/browsers/mobile/",
            "closable": True,
        },
    )
    return snippet


def get_set_as_default_snippet() -> SetAsDefaultSnippet:
    snippet, _ = SetAsDefaultSnippet.objects.update_or_create(
        translation_key=SET_AS_DEFAULT_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "heading_text": "Thanks for choosing Firefox",
            "not_firefox_content": (
                '<p data-block-key="nf001">Looks like you\'re using a different browser right now. '
                "Make sure you have Firefox downloaded on your device.</p>"
            ),
            "not_default_desktop_content": (
                '<p data-block-key="nd001">You\'re almost done. Just change your default browser'
                " to Firefox in the settings panel on your screen.</p>"
                '<p data-block-key="nd002"><a href="https://support.mozilla.org/kb/make-firefox-your-default-browser">'
                "Having trouble setting your default browser?</a></p>"
            ),
            "not_default_android_content": (
                '<p data-block-key="na001">Here\'s everything you need to know about setting your default browser on'
                ' <a href="https://support.mozilla.org/kb/make-firefox-default-browser-android">Android devices</a>.</p>'
            ),
            "not_default_ios_content": (
                '<p data-block-key="ni001">Here\'s everything you need to know about setting your default browser on'
                ' <a href="https://support.mozilla.org/en-US/kb/unable-set-firefox-default-browser-ios">iOS devices</a>.</p>'
            ),
            "success_content": '<p data-block-key="sc001">You\'re all set.</p>',
        },
    )
    snippet.save()
    snippet.save_revision().publish()
    snippet.refresh_from_db()

    return snippet


def get_pretranslated_phrase_snippets() -> tuple[PretranslatedPhrase, PretranslatedPhrase]:
    locale = Locale.get_default()
    get_firefox, _ = PretranslatedPhrase.objects.get_or_create(
        translation_key=PHRASES["get_firefox"]["translation_key"],
        locale=locale,
        defaults={"label": PHRASES["get_firefox"]["label"], "live": True},
    )
    download_firefox, _ = PretranslatedPhrase.objects.get_or_create(
        translation_key=PHRASES["download_firefox"]["translation_key"],
        locale=locale,
        defaults={"label": PHRASES["download_firefox"]["label"], "live": True},
    )
    return get_firefox, download_firefox


def get_floating_qr_code_snippet() -> QRCodeFloatingSnippet:
    snippet, _ = QRCodeFloatingSnippet.objects.update_or_create(
        translation_key=FLOATING_QR_CODE_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "heading": '<p data-block-key="c1bc4d7eadf1">Get Firefox on your phone</p>',
            "content": "Bring your tabs with you",
            "url": "https://www.firefox.com/browsers/mobile/",
            "open_behavior": QROpenBehavior.OPEN,
        },
    )
    return snippet


def get_pencil_banner_snippet() -> PencilBannerSnippet:
    snippet, _ = PencilBannerSnippet.objects.update_or_create(
        translation_key=PENCIL_BANNER_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={
            "title": '<p data-block-key="pb001"><i>New</i> Firefox is here</p>',
            "description": '<p data-block-key="pb002">The fastest, most private Firefox yet.</p>',
            "link": "https://www.firefox.com/",
            "dismissable": True,
            "settings": [],
        },
    )

    snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet


def get_scroll_to_see_more_snippet() -> ScrollToSeeMoreSnippet:
    snippet, _ = ScrollToSeeMoreSnippet.objects.update_or_create(
        translation_key=SCROLL_TO_SEE_MORE_SNIPPET_TRANSLATION_KEY,
        locale=Locale.get_default(),
        defaults={"text": "Scroll to see more"},
    )
    return snippet


def get_tags() -> dict[str, Tag]:
    tag_names = ["Security", "Privacy", "Performance", "Tips", "Updates"]
    locale = Locale.get_default()
    tags = {}
    for name in tag_names:
        slug = slugify(name)
        tag, _ = Tag.objects.update_or_create(
            slug=slug,
            locale=locale,
            defaults={"name": name},
        )
        tags[slug] = tag
    return tags
