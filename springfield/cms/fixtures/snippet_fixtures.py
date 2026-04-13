# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.utils.text import slugify

from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import (
    BannerSnippet,
    ButtonLabelSnippet,
    DownloadFirefoxCallToActionSnippet,
    PreFooterCTAFormSnippet,
    PreFooterCTASnippet,
    QRCodeSnippet,
    Tag,
)


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


def get_button_label_snippets() -> tuple[ButtonLabelSnippet, ButtonLabelSnippet]:
    locale = Locale.get_default()
    get_firefox, _ = ButtonLabelSnippet.objects.update_or_create(
        id=settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID,
        defaults={
            "locale": locale,
            "key": "get_firefox",
            "label": "Get Firefox",
            "live": True,
            "translation_key": "f25078fd-50e4-4a73-acbc-6355bfa7de6e",
        },
    )
    download_firefox, _ = ButtonLabelSnippet.objects.update_or_create(
        id=settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID,
        defaults={
            "locale": locale,
            "key": "download_firefox",
            "label": "Download Firefox",
            "live": True,
            "translation_key": "e13dc0ed-aa51-4077-b011-fb20958ffefd",
        },
    )
    return get_firefox, download_firefox


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
