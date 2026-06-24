# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import (
    get_flare_blocks_docs_page,
    get_flare_pages_docs_page,
    get_flare_snippets_docs_page,
    get_placeholder_images,
)
from springfield.cms.fixtures.snippet_fixtures import (
    get_banner_snippet,
    get_floating_qr_code_snippet,
    get_pencil_banner_snippet,
    get_pre_footer_cta_form_snippet,
    get_pre_footer_cta_snippet,
    get_qr_code_snippet,
    get_scroll_to_see_more_snippet,
    get_set_as_default_snippet,
)
from springfield.cms.models import FreeFormPage2026
from springfield.cms.models.pages import PencilBannerPlacement

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_mobile_store_qr_code():
    return {
        "type": "mobile_store_qr_code",
        "value": {
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="h1wh">Firefox on your phone</p>',
                "subheading_text": '<p data-block-key="sh1wh">The browser you trust, built for life on the go.</p>',
            },
            "qr_code_data": "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com-mobile-page",
            "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        },
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    }


def get_mobile_browsers_cards():
    image, _, _, _ = get_placeholder_images()
    image_block = [
        {
            "type": "image",
            "value": {
                "image": image.id,
                "settings": {
                    "dark_mode_image": None,
                    "mobile_image": None,
                    "dark_mode_mobile_image": None,
                },
            },
            "id": "00000000-0000-0000-0000-000000000001",
        }
    ]
    link_button_settings = {
        "theme": "link",
        "icon": None,
        "icon_position": "right",
        "analytics_id": "",
    }
    return [
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": SHOW_TO_ALL, "image_after": False},
                "media": image_block,
                "eyebrow": "",
                "headline": '<p data-block-key="android-h">Firefox for Android</p>',
                "content": '<p data-block-key="android-c">Private by default, with more ways to make Firefox your own on Android.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {**link_button_settings, "analytics_id": "11111111-1111-1111-1111-111111111111"},
                            "label": "Learn more",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "/browsers/mobile/android/",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "11111111-1111-1111-1111-111111111112",
                    }
                ],
            },
            "id": "11111111-1111-1111-1111-111111111113",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": SHOW_TO_ALL, "image_after": False},
                "media": image_block,
                "eyebrow": "",
                "headline": '<p data-block-key="ios-h">Firefox for iOS</p>',
                "content": '<p data-block-key="ios-c">A more private way to browse on iPhone and iPad, with built-in tracking protection.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {**link_button_settings, "analytics_id": "22222222-2222-2222-2222-222222222221"},
                            "label": "Learn more",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "/browsers/mobile/ios/",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "22222222-2222-2222-2222-222222222222",
                    }
                ],
            },
            "id": "22222222-2222-2222-2222-222222222223",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": SHOW_TO_ALL, "image_after": False},
                "media": image_block,
                "eyebrow": "",
                "headline": '<p data-block-key="focus-h">Firefox Focus</p>',
                "content": '<p data-block-key="focus-c">A fast, minimal browser that clears your history when you\'re done.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {**link_button_settings, "analytics_id": "33333333-3333-3333-3333-333333333331"},
                            "label": "Learn more",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "/browsers/mobile/focus/",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "33333333-3333-3333-3333-333333333332",
                    }
                ],
            },
            "id": "33333333-3333-3333-3333-333333333333",
        },
    ]


def get_mobile_store_qr_code_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    slug = "mobile-store-qr-code"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Mobile Store QR Code",
        )
        index_page.add_child(instance=page)

    page.upper_content = [get_mobile_store_qr_code()]
    page.content = [get_mobile_store_qr_code()]
    page.docs = (
        "<p>The Mobile Store QR Code block displays a QR code beside a heading and copy, generating the code from a URL that "
        "typically deep-links to the iOS / Android app stores. Use it on pages that promote the Firefox mobile app to desktop "
        "visitors.</p>"
        "<p>Keep the QR&rsquo;s destination short and brand-safe &mdash; the URL it encodes is what the user lands on after "
        "scanning. Pair with a mobile placeholder image that clarifies what to expect once on the device.</p>"
    )
    page.save_revision().publish()
    return page


def get_freeform_page_test_page() -> FreeFormPage2026:
    index_page = get_flare_pages_docs_page()

    slug = "freeform"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Free Form Page",
        )
        index_page.add_child(instance=page)

    page.upper_content = [get_mobile_store_qr_code()]
    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="sh1ff">Find the Firefox that fits you.</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "cards_list",
                        "value": {
                            "settings": {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
                            "cards": get_mobile_browsers_cards(),
                        },
                        "id": "44444444-4444-4444-4444-444444444444",
                    }
                ],
                "cta": [],
            },
            "id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
        },
    ]
    snippet = get_pencil_banner_snippet()
    PencilBannerPlacement.objects.get_or_create(page=page, snippet=snippet)
    page.save_revision().publish()
    return page


def get_set_as_default_button_block() -> dict:
    snippet = get_set_as_default_snippet()
    return {
        "type": "intro",
        "value": {
            "settings": {
                "layout": "vertical",
                "slim": False,
                "anchor_id": "",
            },
            "media": [],
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="sad01">Make Firefox your default</p>',
                "subheading_text": "",
            },
            "content": [
                {
                    "type": "buttons",
                    "id": "sad00001-0000-0000-0000-000000000001",
                    "value": [
                        {
                            "type": "set_as_default_button",
                            "value": {
                                "settings": {
                                    "theme": "",
                                    "icon": "",
                                    "icon_position": "right",
                                    "analytics_id": "sad00001-0000-0000-0000-000000000002",
                                },
                                "label": "Set Firefox as default",
                                "snippet": snippet.id,
                            },
                            "id": "sad00001-0000-0000-0000-000000000003",
                        }
                    ],
                }
            ],
        },
        "id": "sad00001-0000-0000-0000-000000000003",
    }


def get_freeform_page_with_set_as_default_button() -> FreeFormPage2026:
    index_page = get_flare_snippets_docs_page()

    slug = "freeform-with-set-as-default"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Free Form — Set as Default Test",
        )
        index_page.add_child(instance=page)

    page.content = [get_set_as_default_button_block()]
    page.docs = (
        "<p>This page demonstrates the Set-as-Default Snippet integration: a button that prompts the user to make Firefox their "
        "default browser, with copy that responds to the user&rsquo;s current browser and default-browser state. The snippet "
        "drives the in-page copy and outcome messages.</p>"
        "<p>Edit the snippet itself in the Snippets admin to change the copy shown in each state (not-firefox, not-default-desktop, "
        "success, etc.). The button block on this page just references the snippet &mdash; the user-facing content lives on the "
        "snippet.</p>"
    )
    page.save_revision().publish()
    return page


def get_freeform_page_with_qr_snippet() -> FreeFormPage2026:
    get_qr_code_snippet()
    index_page = get_flare_snippets_docs_page()

    slug = "freeform-with-qr"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Free Form — QR Snippet Test",
        )
        index_page.add_child(instance=page)

    page.content = [get_mobile_store_qr_code()]
    page.show_qr_code_snippet = True
    page.docs = (
        "<p>This page demonstrates the QR Code Snippet: a QR code rendered on the page when a page has show_qr_code_snippet=True. "
        "The snippet stores its heading, copy, and target URL &mdash; the page just opts in.</p>"
        "<p>Use the QR snippet on desktop pages that promote a mobile experience. To turn it on for a page, enable Show QR Code "
        "Snippet in the page&rsquo;s options panel; to change the QR target or copy, edit the snippet in the Snippets admin.</p>"
    )
    page.save_revision().publish()
    return page


def get_freeform_page_with_floating_qr_snippet() -> FreeFormPage2026:
    get_floating_qr_code_snippet()
    index_page = get_flare_snippets_docs_page()

    slug = "freeform-with-floating-qr"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Free Form — Floating QR Snippet Test",
        )
        index_page.add_child(instance=page)

    page.content = [get_mobile_store_qr_code()]
    page.show_floating_qr_code_snippet = True
    page.docs = (
        "<p>This page demonstrates the Floating QR Code Snippet: a persistent, optionally-dismissable QR code that floats in the "
        "viewport while the user scrolls. Unlike the regular QR snippet, this one stays visible across the whole page.</p>"
        "<p>Enable Show Floating QR Code Snippet in the page&rsquo;s options panel; the snippet&rsquo;s default_open flag controls "
        "whether it starts expanded. Reserve floating snippets for high-intent pages (download, get-firefox flows) &mdash; they&rsquo;re "
        "attention-heavy and shouldn&rsquo;t be the default.</p>"
    )
    page.save_revision().publish()
    return page


def get_banner_snippet_test_page() -> FreeFormPage2026:
    snippet = get_banner_snippet()
    index_page = get_flare_snippets_docs_page()

    slug = "banner-snippet"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Banner Snippet")
        index_page.add_child(instance=page)

    banner_snippet_block = {
        "type": "banner_snippet",
        "value": snippet.id,
        "id": "bs000001-0000-0000-0000-000000000001",
    }
    page.content = [banner_snippet_block]
    page.docs = (
        "<p>The Banner Snippet is a reusable banner content unit &mdash; heading, copy, and optional QR code &mdash; that can be "
        "referenced from any page&rsquo;s content stream via the &lsquo;banner_snippet&rsquo; block. Editing the snippet updates "
        "every page that references it.</p>"
        "<p>Use the Banner Snippet when the same banner needs to appear (with the same copy and asset) on multiple pages. For "
        "one-off banners, prefer the inline Banner block. The kit_theme flag on the snippet toggles brand-kit styling.</p>"
    )
    page.save_revision().publish()
    return page


def get_pencil_banner_snippet_test_page() -> FreeFormPage2026:
    snippet = get_pencil_banner_snippet()
    index_page = get_flare_snippets_docs_page()

    slug = "pencil-banner-snippet"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Pencil Banner Snippet")
        index_page.add_child(instance=page)

    PencilBannerPlacement.objects.get_or_create(page=page, snippet=snippet)
    page.docs = (
        "<p>The Pencil Banner Snippet is the thin, ribbon-style banner that appears above the navigation bar on selected pages. "
        "It carries a short title, description, link, and dismissable flag, and is attached to a page via a Pencil Banner "
        "Placement in the page admin.</p>"
        "<p>Use pencil banners sparingly &mdash; they&rsquo;re interruptive and lose impact quickly when overused. Always set "
        "dismissable=True for non-essential announcements so returning users aren&rsquo;t repeatedly nagged.</p>"
    )
    page.save_revision().publish()
    return page


def get_pre_footer_cta_snippet_test_page() -> FreeFormPage2026:
    get_pre_footer_cta_snippet()
    index_page = get_flare_snippets_docs_page()

    slug = "pre-footer-cta-snippet"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Pre-Footer CTA Snippet")
        index_page.add_child(instance=page)

    page.show_pre_footer = True
    page.docs = (
        "<p>The Pre-Footer CTA Snippet renders a final call-to-action above the page footer &mdash; typically a &lsquo;Get "
        "Firefox&rsquo; button with a single label and analytics ID. Pages opt in via the Show Pre-Footer toggle in the page "
        "options panel.</p>"
        "<p>Keep the label short and action-oriented. The analytics_id should be unique per snippet so downstream funnel reporting "
        "can distinguish placements. Edit the snippet itself in the Snippets admin to change its label and analytics ID.</p>"
    )
    page.save_revision().publish()
    return page


def get_pre_footer_cta_form_snippet_test_page() -> FreeFormPage2026:
    get_pre_footer_cta_form_snippet()
    index_page = get_flare_snippets_docs_page()

    slug = "pre-footer-cta-form-snippet"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Pre-Footer CTA Form Snippet")
        index_page.add_child(instance=page)

    page.show_pre_footer = True
    page.docs = (
        "<p>The Pre-Footer CTA Form Snippet renders a newsletter-style signup form in the pre-footer area, with a heading, "
        "subheading, and an inline email form. Pages opt in via Show Pre-Footer.</p>"
        "<p>Use the form variant when the page goal is list growth rather than a click-through download. The analytics_id is "
        "required for form-submission tracking. Heading and subheading copy are edited on the snippet, not the page.</p>"
    )
    page.save_revision().publish()
    return page


def get_scroll_to_see_more_snippet_test_page() -> FreeFormPage2026:
    snippet = get_scroll_to_see_more_snippet()
    get_placeholder_images()
    index_page = get_flare_snippets_docs_page()

    slug = "scroll-to-see-more-snippet"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Scroll To See More Snippet")
        index_page.add_child(instance=page)

    featured_image_block = {
        "type": "featured_image_section",
        "value": {
            "scroll_to_see_more_snippet": snippet.id,
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="ssm-h">Scroll-to-see-more demo</p>',
                "subheading_text": "",
            },
            "media": [
                {
                    "type": "image",
                    "value": {
                        "image": settings.PLACEHOLDER_IMAGE_ID,
                        "settings": {"dark_mode_image": None, "mobile_image": None, "dark_mode_mobile_image": None},
                    },
                    "id": "ssm00001-0000-0000-0000-000000000001",
                }
            ],
            "content": [],
            "cta": [],
        },
        "id": "ssm00002-0000-0000-0000-000000000001",
    }
    page.upper_content = [featured_image_block]
    page.docs = (
        "<p>The Scroll-to-See-More Snippet is a small, animated indicator (usually rendered near the fold) that signals to the "
        "user there&rsquo;s additional content below. The snippet stores just its label text; placement is controlled by host "
        "blocks &mdash; for instance, the Featured Image Section block accepts a Scroll-to-See-More snippet setting.</p>"
        "<p>Use only on landing-style pages with substantial below-the-fold content. It adds visual noise on short pages and "
        "should not be enabled by default.</p>"
    )
    page.save_revision().publish()
    return page
