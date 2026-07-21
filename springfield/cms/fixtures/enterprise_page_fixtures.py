# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Fixture that recreates the "Enterprise (New)" firefox.com page.

Faithful reproduction of the ten top-level blocks that make up the page,
using the shared placeholder images. Real button destinations and analytics
IDs (the ``data-cta-uid`` values from the source page) are preserved.
"""

from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.contact_page_fixtures import get_form_field_variants
from springfield.cms.models import ContactPage, FreeFormPage2026, NavigationSnippet, SpringfieldImage

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

# Real button destinations from the source page (locale prefix dropped).
CONTACT_URL = "/enterprise/contact/"
PRODUCT_URL = "/enterprise/product/"
SUPPORT_URL = "/enterprise/support/"
DOWNLOAD_URL = "/enterprise/download/"


def _image_value():
    return {
        "image": settings.PLACEHOLDER_IMAGE_ID,
        "settings": {
            "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
            "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
            "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
        },
    }


def _media(block_id):
    return [{"type": "image", "value": _image_value(), "id": block_id}]


def _heading(block_key, heading_text, subheading_text="", superheading_text=""):
    return {
        "superheading_text": f'<p data-block-key="{block_key}sup">{superheading_text}</p>' if superheading_text else "",
        "heading_text": f'<p data-block-key="{block_key}head">{heading_text}</p>',
        "subheading_text": f'<p data-block-key="{block_key}sub">{subheading_text}</p>' if subheading_text else "",
    }


def _link_value(url="", page=None, new_window=False):
    """A SpringfieldLinkBlock value: a page reference when ``page`` is given,
    otherwise a custom URL."""
    return {
        "link_to": "page" if page else "custom_url",
        "page": page.id if page else None,
        "file": None,
        "custom_url": url,
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": new_window,
        "relative_url": "",
    }


def _button(block_id, label, analytics_id, url="", page=None, theme="", size=""):
    return {
        "type": "button",
        "value": {
            "settings": {
                "theme": theme,
                "size": size,
                "icon": "",
                "icon_position": "right",
                "analytics_id": analytics_id,
            },
            "pretranslated_label": None,
            "custom_label": label,
            "link": _link_value(url=url, page=page),
        },
        "id": block_id,
    }


def _button_row(block_id, buttons, spacing="", alignment="", help_text=""):
    return {
        "type": "button_row",
        "value": {
            "spacing": spacing,
            "alignment": alignment,
            "buttons": buttons,
            "help_text": help_text,
        },
        "id": block_id,
    }


def _featured_image_section():
    """Block 1 — hero: heading, a single primary CTA, and the hero image."""
    return {
        "type": "featured_image_section",
        "value": {
            "scroll_to_see_more_snippet": None,
            "heading": _heading(
                "enthero",
                heading_text="Secure enterprise browsing, powered by Firefox.",
                subheading_text="Make the browser a governed control layer for data governance, audit readiness, and sovereignty.",
            ),
            "content": [
                _button_row(
                    "ent-b1-btnrow",
                    buttons=[
                        _button(
                            "ent-b1-btn1",
                            label="Request early access",
                            url=CONTACT_URL,
                            analytics_id="4ab1011f-d310-4892-9922-2c91a3139010",
                        )
                    ],
                )
            ],
            "media": _media("ent-b1-media"),
        },
        "id": "ent-b1-featured-image-section",
    }


def _trusted_media_content():
    """Block 2 — media_content: image beside the "trusted by" copy."""
    return {
        "type": "media_content",
        "value": {
            "settings": {"media_after": False},
            "media": _media("ent-b2-media"),
            "heading": _heading(
                "enttrust",
                heading_text="Trusted by some of Europe's most security-conscious institutions.",
            ),
            "content": [
                {
                    "type": "rich_text",
                    "value": (
                        '<p data-block-key="entb2body">Firefox Enterprise is independent, open source, and backed by a '
                        "nonprofit. Your data isn't our business, protecting it is.</p>"
                    ),
                    "id": "ent-b2-body",
                }
            ],
        },
        "id": "ent-b2-media-content",
    }


def _illustration_card(block_id, headline, content):
    return {
        "type": "illustration_card",
        "value": {
            "settings": {"expand_link": False, "show_to": SHOW_TO_ALL},
            "media": _media(f"{block_id}-media"),
            "eyebrow": "",
            "headline": f'<p data-block-key="{block_id}h">{headline}</p>',
            "content": f'<p data-block-key="{block_id}c">{content}</p>',
            "buttons": [],
        },
        "id": block_id,
    }


def _control_layer_section():
    """Block 3 — section with a three-card illustration grid."""
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": _heading(
                "entcards",
                heading_text="Security, sovereignty, and resilience in one control layer.",
            ),
            "content": [
                {
                    "type": "cards_list",
                    "value": {
                        "settings": {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
                        "cards": [
                            _illustration_card(
                                "ent-b3-card1",
                                headline="Protect work where it happens.",
                                content=(
                                    "Extend your security perimeter to the browser itself. Govern access, data movement, "
                                    "extensions, AI use, telemetry, and updates from a single place, without forcing workflows "
                                    "through remote rendering or full device management."
                                ),
                            ),
                            _illustration_card(
                                "ent-b3-card2",
                                headline="Control your architecture.",
                                content=(
                                    "Run Firefox Enterprise through a local partner, sovereign cloud, or fully on prem. "
                                    "Identity, telemetry, logs, and policy stay inside your boundaries. Access the auditable "
                                    "evidence of control that EU rules increasingly require."
                                ),
                            ),
                            _illustration_card(
                                "ent-b3-card3",
                                headline="Escape the dependency.",
                                content=(
                                    "Add a governed browser layer with verifiable, auditable trust - and without vendor lock in, "
                                    "new cloud dependency or rip-and-replace. Backed by a nonprofit and built on its own engine, "
                                    "Firefox Enterprise avoids the single-engine risk every Chromium browser shares."
                                ),
                            ),
                        ],
                    },
                    "id": "ent-b3-cards-list",
                }
            ],
            "cta": [],
        },
        "id": "ent-b3-section",
    }


def _showcase(block_id, headline, caption_description):
    return {
        "type": "showcase",
        "value": {
            "settings": {"layout": "expanded"},
            "headline": f'<p data-block-key="{block_id}h">{headline}</p>',
            "media": _media(f"{block_id}-media"),
            "caption_title": "",
            "caption_description": f'<p data-block-key="{block_id}c">{caption_description}</p>',
        },
        "id": block_id,
    }


def _two_column_card(block_id, heading_text, subheading_text, list_items, buttons):
    list_html = "".join(f'<li data-block-key="{block_id}li{index}">{item}</li>' for index, item in enumerate(list_items))
    return {
        "type": "card",
        "value": {
            "settings": {"image_position": "bottom-right"},
            "tag": "",
            "content": [
                {
                    "type": "heading",
                    "value": _heading(f"{block_id}head", heading_text=heading_text, subheading_text=subheading_text),
                    "id": f"{block_id}-heading",
                },
                {
                    "type": "rich_text",
                    "value": f"<ul>{list_html}</ul>",
                    "id": f"{block_id}-list",
                },
                _button_row(f"{block_id}-btnrow", buttons=buttons, alignment="left"),
                {
                    "type": "media",
                    "value": _media(f"{block_id}-media-img"),
                    "id": f"{block_id}-media",
                },
            ],
        },
        "id": block_id,
    }


def _two_ways_section():
    """Block 6 — section with a two-column card comparison."""
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": _heading(
                "enttwoways",
                heading_text="Two ways to work with Firefox.",
                subheading_text=(
                    "Deploy the full governed browser, or get expert support for the Firefox you already run. "
                    "Both give your team a direct line to the people behind the product."
                ),
            ),
            "content": [
                {
                    "type": "two_column_cards",
                    "value": {
                        "settings": {
                            "show_to": SHOW_TO_ALL,
                            "anchor_id": "",
                            "theme": "light-light",
                            "reduce_card_padding": False,
                        },
                        "cards": [
                            _two_column_card(
                                "ent-b6-card1",
                                heading_text="Firefox Enterprise On-Prem",
                                subheading_text=(
                                    "Full-scale governance for critical regulated infrastructures, including financial "
                                    "services, utilities, healthcare and public sector."
                                ),
                                list_items=[
                                    "Built-in Browser Data Loss Prevention (DLP)",
                                    "AI Governance &amp; Dynamic Prompt Controls",
                                    "SIEM Log Integration / Real-time Audit",
                                    "Sovereign Cloud &amp; On-Prem Host Deployment",
                                    "Included Professional Support",
                                ],
                                buttons=[
                                    _button(
                                        "ent-b6-card1-btn1",
                                        label="Request Early Access",
                                        url=CONTACT_URL,
                                        analytics_id="2e585499-c15a-4880-855c-ec1a3af9e258",
                                    ),
                                    _button(
                                        "ent-b6-card1-btn2",
                                        label="Learn More",
                                        url=PRODUCT_URL,
                                        analytics_id="d052ea9b-ef6a-4e3d-8e64-4c0b6cccfe0d",
                                        theme="link",
                                    ),
                                ],
                            ),
                            _two_column_card(
                                "ent-b6-card2",
                                heading_text="Firefox Professional Support",
                                subheading_text="A direct line to Mozilla for teams running Firefox. Support covers:",
                                list_items=[
                                    "Firefox / Firefox ESR deployment, configuration, policies, and updates",
                                    "Compatibility diagnosis and operational guidance",
                                    "Advisory and rollout support where included in your plan",
                                ],
                                buttons=[
                                    _button(
                                        "ent-b6-card2-btn1",
                                        label="Request Early Access",
                                        url=CONTACT_URL,
                                        analytics_id="827bbc00-d5a9-4b9d-8d55-cc39b726bc4b",
                                    ),
                                    _button(
                                        "ent-b6-card2-btn2",
                                        label="Learn More",
                                        url=SUPPORT_URL,
                                        analytics_id="f5a73705-fcb9-4b93-baf2-ce664f005b59",
                                        theme="link",
                                    ),
                                ],
                            ),
                        ],
                    },
                    "id": "ent-b6-two-column-cards",
                }
            ],
            "cta": [],
        },
        "id": "ent-b6-section",
    }


def _browser_stat_media_content():
    """Block 9 — media_content: the "70% of working time" stat with a CTA."""
    return {
        "type": "media_content",
        "value": {
            "settings": {"media_after": False},
            "media": _media("ent-b9-media"),
            "content": [
                {
                    "type": "rich_text",
                    "value": (
                        '<p data-block-key="entb9body">The browser is one of the busiest, and least governed, doors in an '
                        "organization. Over 70% of an employee’s working time runs through it. So do over 80% of security "
                        "incidents.</p>"
                    ),
                    "id": "ent-b9-body",
                },
                {
                    "type": "buttons",
                    "value": [
                        _button(
                            "ent-b9-btn1",
                            label="Learn more about Firefox Enterprise",
                            url=PRODUCT_URL,
                            analytics_id="3a5b3398-18ae-4d1f-b2fc-0d119e4199ef",
                            theme="secondary",
                        )
                    ],
                    "id": "ent-b9-buttons",
                },
            ],
        },
        "id": "ent-b9-media-content",
    }


def _enterprise_content():
    return [
        _featured_image_section(),
        _trusted_media_content(),
        _control_layer_section(),
        _showcase(
            "ent-b4-showcase",
            headline="The browser has become the operating surface of modern work.",
            caption_description=(
                "It's where work, data, and identity converge. And where security has the least visibility and control. "
                "See our thoughts behind the shift and the analysis to help you read where it's headed."
            ),
        ),
        _button_row(
            "ent-b5-btnrow",
            buttons=[
                _button(
                    "ent-b5-btn1",
                    label="Get our thoughts",
                    url=PRODUCT_URL,
                    analytics_id="d3fcb24b-0675-4d2a-b0d2-7fcd8cf4a661",
                    theme="secondary",
                )
            ],
        ),
        _two_ways_section(),
        _showcase(
            "ent-b7-showcase",
            headline="Transparent, compliant, and secure.",
            caption_description=(
                "Firefox Enterprise maps to the frameworks European regulators care about like GDPR, NIS2, DORA, and "
                "SecNumCloud. It also provides source-code access, customer-controlled telemetry boundaries, and "
                "self-hosted diagnostic logs."
            ),
        ),
        _button_row(
            "ent-b8-btnrow",
            buttons=[
                _button(
                    "ent-b8-btn1",
                    label="See the features",
                    url=PRODUCT_URL,
                    analytics_id="01b645c5-86fa-4363-8123-f947f49425f9",
                    theme="secondary",
                )
            ],
        ),
        _browser_stat_media_content(),
        _button_row(
            "ent-b10-btnrow",
            buttons=[
                _button(
                    "ent-b10-btn1",
                    label="Request early access",
                    url=CONTACT_URL,
                    analytics_id="5ae62e3f-510f-4366-8f79-d76fe5ecd86c",
                    size="large",
                )
            ],
            help_text=(
                '<p data-block-key="entb10help">Not ready for Firefox Enterprise?<br/>'
                f'<a href="{DOWNLOAD_URL}">Download Firefox for your organization for free.</a></p>'
            ),
            spacing="small",
        ),
    ]


def get_enterprise_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_pages_docs_page()

    slug = "enterprise"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Enterprise",
        },
    )

    page.theme = "enterprise"
    page.show_pre_footer = False
    page.content = _enterprise_content()
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Child pages of the enterprise sub-site (Product, Support, Download, Contact).
# Content reproduced verbatim from the saved firefox.com HTML pages, using the
# shared placeholder imagery. All use the enterprise theme and inherit the
# enterprise navigation from the parent page.
# ---------------------------------------------------------------------------


def _rich_text(block_id, html):
    return {"type": "rich_text", "value": html, "id": block_id}


def _buttons(block_id, buttons):
    return {"type": "buttons", "value": buttons, "id": block_id}


def _hero(block_id, heading_text, subheading_text, buttons):
    """A featured_image_section hero: heading, a button row, and the hero image."""
    return {
        "type": "featured_image_section",
        "value": {
            "scroll_to_see_more_snippet": None,
            "heading": _heading(block_id, heading_text=heading_text, subheading_text=subheading_text),
            "content": [_button_row(f"{block_id}-btnrow", buttons=buttons)],
            "media": _media(f"{block_id}-media"),
        },
        "id": block_id,
    }


def _icon_card(block_id, icon, headline, content):
    return {
        "type": "icon_card",
        "value": {
            "settings": {"expand_link": False, "show_to": SHOW_TO_ALL},
            "icon": icon,
            "headline": f'<p data-block-key="{block_id}h">{headline}</p>',
            "content": f'<p data-block-key="{block_id}c">{content}</p>',
            "buttons": [],
        },
        "id": block_id,
    }


def _cards_list(block_id, cards, cards_per_row=""):
    return {
        "type": "cards_list",
        "value": {
            "settings": {"container_width": "", "cards_per_row": cards_per_row, "two_wide_xs": False},
            "cards": cards,
        },
        "id": block_id,
    }


def _section(block_id, heading_text, subheading_text="", content_blocks=None):
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": _heading(block_id, heading_text=heading_text, subheading_text=subheading_text),
            "content": content_blocks or [],
            "cta": [],
        },
        "id": block_id,
    }


def _sticker_card(block_id, headline, content, superheading=""):
    return {
        "type": "sticker_card",
        "value": {
            "settings": {"expand_link": False, "show_to": SHOW_TO_ALL},
            "image": _image_value(),
            "superheading": f'<p data-block-key="{block_id}s">{superheading}</p>' if superheading else "",
            "headline": f'<p data-block-key="{block_id}h">{headline}</p>',
            "content": f'<p data-block-key="{block_id}c">{content}</p>',
            "buttons": [],
        },
        "id": block_id,
    }


def _banner(block_id, theme, heading_text, subheading_text, buttons, slim=False):
    return {
        "type": "banner",
        "value": {
            "settings": {
                "theme": theme,
                "media_after": False,
                "show_to": SHOW_TO_ALL,
                "anchor_id": "",
                "slim": slim,
                "remove_border_radius": False,
                "centralize_content": False,
            },
            "media": [],
            "heading": _heading(block_id, heading_text=heading_text, subheading_text=subheading_text),
            "content": [_buttons(f"{block_id}-btns", buttons)],
        },
        "id": block_id,
    }


def _media_content(block_id, heading_text, subheading_text, body_blocks, media_after=False):
    return {
        "type": "media_content",
        "value": {
            "settings": {"media_after": media_after},
            "media": _media(f"{block_id}-media"),
            "heading": _heading(block_id, heading_text=heading_text, subheading_text=subheading_text),
            "content": body_blocks,
        },
        "id": block_id,
    }


def _intro(block_id, heading_text, subheading_text, content_blocks, layout="right", remove_border_radius=False, media=None):
    return {
        "type": "intro",
        "value": {
            "settings": {
                "layout": layout,
                "full_width": False,
                "slim": False,
                "anchor_id": "",
                "remove_border_radius": remove_border_radius,
            },
            "media": _media(f"{block_id}-media") if media is None else media,
            "heading": _heading(block_id, heading_text=heading_text, subheading_text=subheading_text),
            "content": content_blocks,
        },
        "id": block_id,
    }


def _download_button(block_id, label, analytics_id, theme=""):
    return {
        "type": "download_button",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "settings": {
                "theme": theme,
                "icon": "downloads",
                "icon_position": "right",
                "analytics_id": analytics_id,
                "show_default_browser_checkbox": False,
            },
        },
        "id": block_id,
    }


def _enterprise_download(block_id):
    return {"type": "enterprise_download", "value": None, "id": block_id}


def _product_content(contact_page):
    return [
        _hero(
            "prod-hero",
            heading_text="The browser, secured and under your control.",
            subheading_text=(
                "Firefox Enterprise gives security and IT teams a governed browser that supports data governance, "
                "compliance and audit readiness, and sovereignty requirements."
            ),
            buttons=[
                _button(
                    "prod-hero-btn",
                    label="Request early access",
                    analytics_id="c1000000-0000-0000-0000-000000000001",
                    page=contact_page,
                )
            ],
        ),
        _section(
            "prod-security",
            heading_text="Security",
            subheading_text=(
                "Extend your threat defense to the place where work actually happens, while integrating with the DLP, "
                "SIEM, and security tools you already run. Give users secure access to what they need, without hindering "
                "their experience, or adding the infrastructure tax of VPNs, MDM, or virtual desktops."
            ),
            content_blocks=[
                _cards_list(
                    "prod-security-cards",
                    [
                        _icon_card(
                            "prod-sec-card1",
                            icon="window",
                            headline="Control data at the point of use.",
                            content=(
                                "Stop sensitive data leaks where they happen, including through AI, with content-aware "
                                "inspection within the session, extending your existing DLP to the browser."
                            ),
                        ),
                        _icon_card(
                            "prod-sec-card2",
                            icon="shield-cross",
                            headline="Defend against browser-borne threats.",
                            content=(
                                "Block phishing, malicious sites, and credential theft with extension control and policy "
                                "enforcement. Contain risky sites with native isolation that retains performance without "
                                "remote rendering tax or VDI bills."
                            ),
                        ),
                        _icon_card(
                            "prod-sec-card3",
                            icon="device-mobile",
                            headline="Secure access from any device.",
                            content=(
                                "Give employees, contractors, and partners tiered access from managed and unmanaged devices "
                                "without MDM, VPN, or network routing. Enforce strong authentication even on legacy apps that "
                                "don't support it."
                            ),
                        ),
                    ],
                    cards_per_row="2",
                )
            ],
        ),
        _section(
            "prod-sovereignty",
            heading_text="Sovereignty",
            subheading_text=(
                "Define the boundaries for telemetry and browsing data, and deploy on-prem or in an approved hosting "
                "environment. You own the infrastructure with no forced cloud dependency."
            ),
            content_blocks=[
                _cards_list(
                    "prod-sovereignty-cards",
                    [
                        _icon_card(
                            "prod-sov-card1",
                            icon="warning",
                            headline="Extend DLP to where data actually moves.",
                            content=(
                                "Stop accidental and intentional data loss where it happens and deter what inspection can't "
                                "catch. Close the gap your network and endpoint tools can't see, without ripping out what "
                                "you've already bought."
                            ),
                        ),
                        _icon_card(
                            "prod-sov-card2",
                            icon="settings",
                            headline="Close the browser blind spot for your SOC.",
                            content=(
                                "Give security teams real-time visibility into browser-level activity and admin actions, "
                                "where most tooling goes dark."
                            ),
                        ),
                        _icon_card(
                            "prod-sov-card3",
                            icon="heart-rate",
                            headline="Sovereignty by Design.",
                            content=(
                                "Keep data, keys, telemetry, and policy inside your jurisdiction and control boundary. Run "
                                "it on-premises and audit the open-source browser yourself."
                            ),
                        ),
                    ],
                    cards_per_row="2",
                )
            ],
        ),
        _section(
            "prod-resilience",
            heading_text="Resilience",
            subheading_text=(
                "Break free from vendor lock-in, dependencies, and risks by leveraging the only independent, open-source "
                "browser that returns control and infrastructure to your organization."
            ),
            content_blocks=[
                _cards_list(
                    "prod-resilience-cards",
                    [
                        _icon_card(
                            "prod-res-card1",
                            icon="globe",
                            headline="Stay running when the monoculture breaks.",
                            content=(
                                "Mitigate the risk that a Chromium incident, bad release, or unilateral decision takes your "
                                "workforce offline. True engine diversity plus disciplined change management keeps critical "
                                "workflows operating."
                            ),
                        ),
                        _icon_card(
                            "prod-res-card2",
                            icon="quality",
                            headline="Aligned by mission, not monetization.",
                            content=(
                                "Your browser vendor's incentives shape your risk. Nonprofit-backed governance means the "
                                "roadmap answers to a mission, not a revenue target. No user-data monetization, no ecosystem "
                                "lock-in, no strategy shift that leaves you stranded."
                            ),
                        ),
                    ],
                    cards_per_row="2",
                )
            ],
        ),
        _showcase(
            "prod-showcase",
            headline="See Firefox Enterprise in your environment.",
            caption_description=("Tell us a bit about your environment and priorities. We'll route your request to the right next step."),
        ),
        _button_row(
            "prod-close-btnrow",
            buttons=[
                _button(
                    "prod-close-btn",
                    label="Request early access",
                    analytics_id="c1000000-0000-0000-0000-000000000002",
                    page=contact_page,
                    theme="secondary",
                )
            ],
        ),
    ]


def _support_content(contact_page):
    return [
        _hero(
            "supp-hero",
            heading_text="A direct line to Mozilla for teams running Firefox.",
            subheading_text=(
                "Firefox Professional Support gives your IT team a direct, private path to the people behind the product. "
                "Resolve issues faster with expert triage, guidance, and escalation."
            ),
            buttons=[
                _button(
                    "supp-hero-btn",
                    label="Request early access",
                    analytics_id="c2000000-0000-0000-0000-000000000001",
                    page=contact_page,
                )
            ],
        ),
        _section(
            "supp-cards-section",
            heading_text="Real people. Faster answers.",
            content_blocks=[
                _cards_list(
                    "supp-cards",
                    [
                        _icon_card(
                            "supp-card1",
                            icon="arrow-trending",
                            headline="Headline",
                            content=("A direct escalation path with guaranteed response times to keep rollouts and critical work on track"),
                        ),
                        _icon_card(
                            "supp-card2",
                            icon="closed-caption",
                            headline="Headline",
                            content="A private support portal for incident handling and diagnosis to ensure timely resolution",
                        ),
                        _icon_card(
                            "supp-card3",
                            icon="applied-policy",
                            headline="Headline",
                            content=("Expert integration guidance across enterprise policies, supported apps, updates, extensions, and certificates"),
                        ),
                        _icon_card(
                            "supp-card4",
                            icon="avatar-signed-out",
                            headline="Headline",
                            content="Named contacts, business reviews, and local-language support on higher tiers",
                        ),
                    ],
                    cards_per_row="2",
                )
            ],
        ),
        _media_content(
            "supp-feature",
            heading_text="Going further? Support comes built in with Firefox Enterprise.",
            subheading_text=(
                "Firefox Enterprise adds centralized management, built-in DLP, SIEM integration, and sovereign deployment "
                "with our highest tier of support included. No separate support contract."
            ),
            body_blocks=[
                _rich_text("supp-feature-body1", '<p data-block-key="suppfb1">24×7 coverage</p>'),
                _rich_text(
                    "supp-feature-body2",
                    '<ul><li data-block-key="suppfb2a">24×7 coverage</li>'
                    '<li data-block-key="suppfb2b">15-minute response for business-halting incidents</li>'
                    '<li data-block-key="suppfb2c">Named Success Lead</li>'
                    '<li data-block-key="suppfb2d">Monthly business reviews</li></ul>',
                ),
            ],
        ),
        _rich_text(
            "supp-fineprint",
            '<h2 data-block-key="suppfp0">The fine print</h2>'
            '<p data-block-key="suppfp1">What support covers</p>'
            "<ul>"
            '<li data-block-key="suppfp2">Firefox and Firefox ESR deployment, configuration, policy management, and updates</li>'
            '<li data-block-key="suppfp3">Guidance for supported integrations, extensions, and managed environments</li>'
            '<li data-block-key="suppfp4">Compatibility diagnosis and operational guidance</li>'
            '<li data-block-key="suppfp5">Advisory and rollout support where included in your plan</li>'
            "</ul>"
            '<p data-block-key="suppfp6">What it doesn’t</p>'
            "<ul>"
            '<li data-block-key="suppfp7">Not an end-user helpdesk, free consumer support, or a substitute for '
            "third-party vendor support, custom feature development, or remediation of non-Mozilla systems</li>"
            '<li data-block-key="suppfp8">Not managed security, SOC, threat monitoring, or managed DLP</li>'
            "</ul>",
        ),
        _banner(
            "supp-banner",
            theme="purple-radial-gradient",
            heading_text="Let's talk before your next rollout.",
            subheading_text="A short call will help us understand your Firefox footprint and which level of support fits.",
            buttons=[
                _button(
                    "supp-banner-btn",
                    label="Request early access",
                    analytics_id="c2000000-0000-0000-0000-000000000002",
                    page=contact_page,
                )
            ],
            slim=True,
        ),
    ]


def _download_content(contact_page):
    return [
        _intro(
            "dl-intro",
            heading_text="Use Firefox as your enterprise browser",
            subheading_text=(
                "Firefox delivers secure, resilient, and privacy-focused browsing at scale. With enterprise policies in "
                "both Firefox or Firefox Extended Support Release (ESR), organizations get flexibility, control, and "
                "transparency in a trusted, open-source browser."
            ),
            content_blocks=[
                _buttons(
                    "dl-intro-btns",
                    [
                        _download_button(
                            "dl-intro-dlbtn",
                            label="Download Firefox",
                            analytics_id="c3000000-0000-0000-0000-000000000001",
                        )
                    ],
                )
            ],
            layout="right",
            remove_border_radius=True,
        ),
        _banner(
            "dl-banner-1",
            theme="dark-purple-gradient",
            heading_text="Firefox Professional Support",
            subheading_text=(
                "Early access is now open for our new support program. Built for organizations that use Firefox to ensure "
                "security, resilience, and data sovereignty, it provides private, reliable, and custom support for "
                "large-scale deployments."
            ),
            buttons=[
                _button(
                    "dl-banner-1-btn",
                    label="Contact Sales",
                    analytics_id="c3000000-0000-0000-0000-000000000002",
                    page=contact_page,
                )
            ],
        ),
        _section(
            "dl-cards-section",
            heading_text="Enterprise-grade protection, powered by Firefox",
            content_blocks=[
                _cards_list(
                    "dl-cards",
                    [
                        _sticker_card(
                            "dl-card1",
                            headline="Your browser, your business",
                            content=(
                                "Firefox combines open-source transparency with advanced security features and frequent "
                                "updates to help safeguard your organization's data."
                            ),
                        ),
                        _sticker_card(
                            "dl-card2",
                            headline="Deploy when and how you want",
                            content=(
                                "With install packages and a wide expansion of group policies and features, deployment is "
                                "faster and more flexible than ever — and a breeze for Windows, Linux, and macOS environments."
                            ),
                        ),
                        _sticker_card(
                            "dl-card3",
                            headline="Release cycles that fit your organization",
                            content=(
                                "Choose Firefox for the latest features and stable releases every four weeks, or Firefox ESR "
                                "for long-term stability, regular security updates, and annual major releases."
                            ),
                        ),
                    ],
                )
            ],
        ),
        _banner(
            "dl-banner-2",
            theme="purple-radial-gradient",
            heading_text="Firefox Professional Support documentation",
            subheading_text=(
                "Firefox Professional Support is a dedicated offering for teams who need private issue triage and "
                "escalation, defined response times, custom development options, and close collaboration with Mozilla's "
                "engineering and product teams."
            ),
            buttons=[
                _button(
                    "dl-banner-2-btn",
                    label="Support Plan",
                    analytics_id="c3000000-0000-0000-0000-000000000003",
                    url="https://www.mozilla.org/firefox/enterprise/",
                )
            ],
        ),
        _enterprise_download("dl-enterprise-download"),
    ]


def get_enterprise_product_page(parent, contact_page) -> FreeFormPage2026:
    page = get_or_create_page(
        FreeFormPage2026,
        slug="product",
        parent=parent,
        defaults={"title": "Product"},
    )
    page.theme = "enterprise"
    page.show_pre_footer = False
    page.content = _product_content(contact_page)
    page.docs = "<p>Firefox Enterprise product page, reproduced from the firefox.com enterprise sub-site.</p>"
    page.save_revision().publish()
    return page


def get_enterprise_support_page(parent, contact_page) -> FreeFormPage2026:
    page = get_or_create_page(
        FreeFormPage2026,
        slug="support",
        parent=parent,
        defaults={"title": "Support"},
    )
    page.theme = "enterprise"
    page.show_pre_footer = False
    page.content = _support_content(contact_page)
    page.docs = "<p>Firefox Professional Support page, reproduced from the firefox.com enterprise sub-site.</p>"
    page.save_revision().publish()
    return page


def get_enterprise_download_page(parent, contact_page) -> FreeFormPage2026:
    page = get_or_create_page(
        FreeFormPage2026,
        slug="download",
        parent=parent,
        defaults={"title": "Download"},
    )
    page.theme = "enterprise"
    page.show_pre_footer = False
    page.content = _download_content(contact_page)
    page.docs = "<p>Firefox Enterprise download page, reproduced from the firefox.com enterprise sub-site.</p>"
    page.save_revision().publish()
    return page


def get_enterprise_contact_page(parent) -> ContactPage:
    page = get_or_create_page(
        ContactPage,
        slug="contact",
        parent=parent,
        defaults={
            "title": "Contact",
            "basket_api_path": "/api/v1/contact/enterprise/",
            "thank_you_message": '<p data-block-key="entctty">Thanks for reaching out! We\'ll be in touch about early access.</p>',
        },
    )
    page.theme = "enterprise"
    page.intro = [
        _intro(
            "ent-contact-intro",
            heading_text="Request early access",
            subheading_text="Tell us about your organization and we'll get back to you about Firefox Enterprise.",
            content_blocks=[],
            layout="vertical",
            media=[],
        )
    ]
    page.form_fields = get_form_field_variants()
    page.basket_api_path = "/api/v1/contact/enterprise/"
    page.thank_you_message = '<p data-block-key="entctty">Thanks for reaching out! We\'ll be in touch about early access.</p>'
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Enterprise navigation snippet + sub-site coordinator.
# ---------------------------------------------------------------------------


def _get_enterprise_logo(title, filename) -> SpringfieldImage:
    """Load (idempotently) an enterprise logo from the media directory."""
    image = SpringfieldImage.objects.filter(title=title).first()
    if image:
        return image
    file_path = Path(settings.ROOT) / "media" / "img" / "logos" / "firefox-enterprise" / filename
    with file_path.open("rb") as logo_file:
        return SpringfieldImage.objects.create(title=title, file=ContentFile(logo_file.read(), name=filename))


def _nav_top_level_link(block_id, label, page, analytics_id) -> dict:
    return {
        "type": "top_level_link",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "link": _link_value(page=page),
            "analytics_id": analytics_id,
        },
        "id": block_id,
    }


def get_enterprise_navigation_snippet(parent, product_page, support_page, contact_page) -> NavigationSnippet:
    locale = Locale.get_default()
    snippet, _ = NavigationSnippet.objects.update_or_create(
        name="Enterprise navigation",
        locale=locale,
        defaults={
            "items": [
                _nav_top_level_link("ent-nav-product", "Product", product_page, "c5000000-0000-0000-0000-000000000001"),
                _nav_top_level_link("ent-nav-support", "Support", support_page, "c5000000-0000-0000-0000-000000000002"),
                _nav_top_level_link("ent-nav-contact", "Contact", contact_page, "c5000000-0000-0000-0000-000000000003"),
            ],
            "logo": _get_enterprise_logo("Firefox Enterprise Logo", "firefox-enterprise.svg"),
            "logo_dark": _get_enterprise_logo("Firefox Enterprise Logo (Dark)", "firefox-enterprise-dark.svg"),
            "logo_link": [{"type": "link", "value": _link_value(page=parent), "id": "ent-nav-logolink"}],
            "cta_button": [
                {
                    "type": "button",
                    "value": [
                        _button(
                            "ent-nav-cta",
                            label="Request early access",
                            analytics_id="c5000000-0000-0000-0000-000000000004",
                            page=contact_page,
                        )
                    ],
                    "id": "ent-nav-cta-wrap",
                }
            ],
        },
    )
    snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet


def get_enterprise_pages() -> dict:
    """Build the full enterprise sub-site: the parent page, its four child
    pages, and the enterprise navigation snippet wired as the parent's custom
    navigation (inherited by every child). Returns all created pages keyed by
    role."""
    parent = get_enterprise_test_page()
    contact = get_enterprise_contact_page(parent)
    product = get_enterprise_product_page(parent, contact)
    support = get_enterprise_support_page(parent, contact)
    download = get_enterprise_download_page(parent, contact)

    snippet = get_enterprise_navigation_snippet(parent, product, support, contact)
    parent.custom_navigation = snippet
    parent.save_revision().publish()

    return {
        "enterprise": parent,
        "product": product,
        "support": support,
        "download": download,
        "contact": contact,
    }
