# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from wagtail.models import Locale

from springfield.cms.models import BannerSnippet, PreFooterCTAFormSnippet


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
