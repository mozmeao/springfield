# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.utils.text import slugify

from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import (
    BannerSnippet,
    DownloadFirefoxCallToActionSnippet,
    PreFooterCTAFormSnippet,
    PreFooterCTASnippet,
    QRCodeSnippet,
    SetAsDefaultSnippet,
    Tag,
)
from springfield.cms.models.snippets import QRCodeFloatingSnippet


def get_banner_snippet() -> BannerSnippet:
    locale = Locale.get_default()
    snippet, _ = BannerSnippet.objects.update_or_create(
        id=settings.BANNER_SNIPPET_ID,
        defaults={
            "locale": locale,
            "kit_theme": True,
            "heading": '<p data-block-key="c1bc4d7eadf0">Take your tabs, history and passwords wherever you go</p>',
            "content": '<p data-block-key="0b474f02">Your passwords, bookmarks, and preferences sync seamlessly across all your devices, '
            "so you can pick up where you left off. </p>",
            "qr_code": "QR Code Content",
        },
    )
    return snippet


def get_pre_footer_cta_snippet() -> PreFooterCTASnippet:
    locale = Locale.get_default()
    snippet, _ = PreFooterCTASnippet.objects.update_or_create(
        id=settings.PRE_FOOTER_CTA_SNIPPET_ID,
        defaults={
            "locale": locale,
            "label": "Get Firefox",
            "analytics_id": "123e4567-e89b-12d3-a456-426614174000",
        },
    )
    return snippet


def get_pre_footer_cta_form_snippet() -> PreFooterCTAFormSnippet:
    locale = Locale.get_default()
    snippet, _ = PreFooterCTAFormSnippet.objects.update_or_create(
        id=settings.PRE_FOOTER_CTA_FORM_SNIPPET_ID,
        defaults={
            "locale": locale,
            "heading": '<p data-block-key="c1bc4d7eadf0">Keep up with all things Firefox</p>',
            "subheading": '<p data-block-key="0b474f02">Get how-tos, advice and news to make your Firefox experience work best for you.</p>',
            "analytics_id": "0b474f02-d3fd-4d86-83cd-c1bc4d7eadf0",
        },
    )
    return snippet


def get_download_firefox_cta_snippet() -> DownloadFirefoxCallToActionSnippet:
    image, _, _, _ = get_placeholder_images()
    locale = Locale.get_default()
    snippet, _ = DownloadFirefoxCallToActionSnippet.objects.update_or_create(
        id=settings.DOWNLOAD_FIREFOX_CTA_SNIPPET_ID,
        defaults={
            "locale": locale,
            "heading": '<p data-block-key="c1bc4d7eadf0">Download Firefox Browser</p>',
            "description": '<p data-block-key="0b474f02">Fast, private and free web browser. </p>',
            "image": image,
        },
    )
    return snippet


def get_qr_code_snippet() -> QRCodeSnippet:
    locale = Locale.get_default()
    snippet, _ = QRCodeSnippet.objects.update_or_create(
        id=settings.QR_CODE_SNIPPET_ID,
        defaults={
            "locale": locale,
            "heading": '<p data-block-key="c1bc4d7eadf0">Get Firefox on your phone</p>',
            "qr_code": "https://www.firefox.com/browsers/mobile/",
            "closable": True,
        },
    )
    return snippet


def get_set_as_default_snippet() -> SetAsDefaultSnippet:
    locale = Locale.get_default()
    snippet = SetAsDefaultSnippet.objects.filter(id=settings.SET_AS_DEFAULT_SNIPPET_ID).first()
    if not snippet:
        snippet = SetAsDefaultSnippet(id=settings.SET_AS_DEFAULT_SNIPPET_ID, locale=locale)

    snippet.heading_text = "Thanks for choosing Firefox"
    snippet.not_firefox_content = (
        '<p data-block-key="nf001">Looks like you\'re using a different browser right now. Make sure you have Firefox downloaded on your device.</p>'
    )
    snippet.not_default_desktop_content = (
        '<p data-block-key="nd001">You\'re almost done. Just change your default browser'
        " to Firefox in the settings panel on your screen.</p>"
        '<p data-block-key="nd002"><a href="https://support.mozilla.org/kb/make-firefox-your-default-browser">'
        "Having trouble setting your default browser?</a></p>"
    )
    snippet.not_default_android_content = (
        '<p data-block-key="na001">Here\'s everything you need to know about setting your default browser on'
        ' <a href="https://support.mozilla.org/kb/make-firefox-default-browser-android">Android devices</a>.</p>'
    )
    snippet.not_default_ios_content = (
        '<p data-block-key="ni001">Here\'s everything you need to know about setting your default browser on'
        ' <a href="https://support.mozilla.org/en-US/kb/unable-set-firefox-default-browser-ios">iOS devices</a>.</p>'
    )
    snippet.success_content = '<p data-block-key="sc001">You\'re all set.</p>'
    snippet.save()
    snippet.save_revision().publish()
    snippet.refresh_from_db()

    return snippet


def get_floating_qr_code_snippet() -> QRCodeFloatingSnippet:
    locale = Locale.get_default()
    snippet, _ = QRCodeFloatingSnippet.objects.update_or_create(
        id=settings.QR_CODE_SNIPPET_ID,
        defaults={
            "locale": locale,
            "heading": '<p data-block-key="c1bc4d7eadf1">Get Firefox on your phone</p>',
            "content": "Bring your tabs with you",
            "url": "https://www.firefox.com/browsers/mobile/",
            "default_open": True,
        },
    )
    return snippet


def get_tags() -> list[Tag]:
    tag_names = ["Security", "Privacy", "Performance", "Tips", "Updates"]
    locale = Locale.get_default()
    tags = {}
    for name in tag_names:
        slug = slugify(name)
        tag, _ = Tag.objects.update_or_create(
            name=name,
            slug=slug,
            locale=locale,
        )
        tags[slug] = tag
    return tags
