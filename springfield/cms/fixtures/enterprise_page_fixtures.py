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

from springfield.cms.fixtures.base_fixtures import (
    SHOW_TO_ALL,
    get_flare_pages_docs_page,
    get_image_media,
    get_image_variants,
    get_or_create_page,
    get_placeholder_images,
)
from springfield.cms.fixtures.block_factories import (
    banner,
    button,
    button_row,
    buttons_block,
    cards_list,
    download_button,
    heading_block,
    heading_value,
    hero,
    icon_card,
    illustration_card,
    intro,
    link_value,
    media_content,
    nav_top_level_link,
    pictogram_card,
    rich_text,
    section,
    showcase,
    two_column_card,
)
from springfield.cms.fixtures.comparison_table_fixtures import make_content_rows, make_header_row
from springfield.cms.fixtures.contact_page_fixtures import get_form_field_variants_with_fieldsets
from springfield.cms.fixtures.enterprise_download_fixtures import get_enterprise_download, get_enterprise_download_rich_text
from springfield.cms.models import ContactPage, FreeFormPage2026, NavigationSnippet, SpringfieldImage
from springfield.cms.models.pages import BASKET_CONTACT_ENTERPRISE_PATH

# Real button destinations from the source page (locale prefix dropped).
CONTACT_URL = "/enterprise/contact/"
PRODUCT_URL = "/enterprise/product/"
SUPPORT_URL = "/enterprise/support/"
DOWNLOAD_URL = "/enterprise/download/"


def featured_image_section():
    """Block 1 — hero: heading, a single primary CTA, and the hero image."""
    return {
        "type": "featured_image_section",
        "value": {
            "scroll_to_see_more_snippet": None,
            "heading": heading_value(
                block_key="enthero",
                heading_text="Your workforce runs through the browser. Firefox gives you enterprise control.",
                subheading_text="Firefox Enterprise puts security controls where work happens. Make the browser a governed control "
                "layer for data governance, audit readiness, and sovereignty.",
            ),
            "content": [
                button_row(
                    "ent-b1-btnrow",
                    buttons=[
                        button(
                            "ent-b1-btn1",
                            label="Request early access",
                            url=CONTACT_URL,
                            analytics_id="4ab1011f-d310-4892-9922-2c91a3139010",
                        )
                    ],
                )
            ],
            "media": get_image_media(block_id="ent-b1-media"),
        },
        "id": "ent-b1-featured-image-section",
    }


def trusted_media_content():
    """Block 2 — media_content: image beside the "trusted by" copy."""
    return {
        "type": "media_content",
        "value": {
            "settings": {"media_after": False},
            "media": get_image_media(block_id="ent-b2-media"),
            "heading": heading_value(block_key="enttrust", heading_text="Trusted by some of Europe's most security-conscious institutions."),
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


def control_layer_section():
    """Block 3 — section with a three-card illustration grid."""
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": heading_value(block_key="entcards", heading_text="Security, sovereignty, and resilience in one control layer."),
            "content": [
                {
                    "type": "cards_list",
                    "value": {
                        "settings": {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
                        "cards": [
                            illustration_card(
                                block_id="ent-b3-card1",
                                headline="Protect work where it happens.",
                                content="Extend your security perimeter to the browser itself. Govern access, data movement, "
                                "extensions, AI use, telemetry, and updates from a single place, without forcing workflows "
                                "through remote rendering or full device management.",
                                media=get_image_media("ent-b3-card1-media-img"),
                            ),
                            illustration_card(
                                block_id="ent-b3-card2",
                                headline="Own your architecture.",
                                content="Run Firefox Enterprise through a local partner, sovereign cloud, or fully on prem. "
                                "Identity, telemetry, logs, and policy stay inside your boundaries. Access the auditable "
                                "evidence of control that EU rules increasingly require.",
                                media=get_image_media("ent-b3-card2-media-img"),
                            ),
                            illustration_card(
                                block_id="ent-b3-card3",
                                headline="Escape the dependency.",
                                content="Add a governed browser layer with verifiable, auditable trust - and without vendor lock in, "
                                "new cloud dependency or rip-and-replace. Backed by a nonprofit and built on its own engine, "
                                "Firefox Enterprise avoids the single-engine risk every Chromium browser shares.",
                                media=get_image_media("ent-b3-card3-media-img"),
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


def two_column_list_card(block_id, heading_text, subheading_text, list_items, buttons):
    """A two-column card with a heading, a bulleted list, stacked buttons and an image."""
    list_html = "".join(f'<li data-block-key="{block_id}li{index}">{item}</li>' for index, item in enumerate(list_items))
    return two_column_card(
        block_id,
        [
            heading_block(f"{block_id}-heading", heading_text, subheading_text=subheading_text),
            rich_text(f"{block_id}-list", f"<ul>{list_html}</ul>"),
            button_row(f"{block_id}-btnrow", buttons=buttons, orientation="stacked"),
            {"type": "media", "value": get_image_media(f"{block_id}-media-img"), "id": f"{block_id}-media"},
        ],
        image_position="bottom-right",
    )


def two_ways_section():
    """Block 6 — section with a two-column card comparison."""
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": heading_value(
                block_key="enttwoways",
                heading_text="Ready to scale when you are.",
                subheading_text="Begin with the free managed browser and enterprise policy controls, then move to Premium for "
                "centralized management, built-in DLP, SIEM integration, and AI governance in a sovereign cloud "
                "or fully on-prem.",
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
                            two_column_list_card(
                                "ent-b6-card1",
                                heading_text="Firefox Enterprise - On-Prem",
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
                                    button(
                                        "ent-b6-card1-btn1",
                                        label="Request Early Access & Pricing",
                                        url=CONTACT_URL,
                                        analytics_id="2e585499-c15a-4880-855c-ec1a3af9e258",
                                    ),
                                    button(
                                        "ent-b6-card1-btn2",
                                        label="Learn more",
                                        url=PRODUCT_URL,
                                        analytics_id="d052ea9b-ef6a-4e3d-8e64-4c0b6cccfe0d",
                                        theme="link",
                                    ),
                                ],
                            ),
                            two_column_list_card(
                                "ent-b6-card2",
                                heading_text="Firefox Professional Support",
                                subheading_text="A direct line to Mozilla for teams running Firefox. Support covers:",
                                list_items=[
                                    "Firefox / Firefox ESR deployment, configuration, policies, and updates",
                                    "Compatibility diagnosis and operational guidance",
                                    "Advisory and rollout support where included in your plan",
                                ],
                                buttons=[
                                    button(
                                        "ent-b6-card2-btn1",
                                        label="Talk to an expert",
                                        url=CONTACT_URL,
                                        analytics_id="827bbc00-d5a9-4b9d-8d55-cc39b726bc4b",
                                    ),
                                    button(
                                        "ent-b6-card2-btn2",
                                        label="Learn more",
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


def browser_stat_media_content():
    """Block 9 — media_content: the "70% of working time" stat with a CTA."""
    return {
        "type": "media_content",
        "value": {
            "settings": {"media_after": False},
            "media": get_image_media(block_id="ent-b9-media"),
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
            ],
        },
        "id": "ent-b9-media-content",
    }


def enterprise_upper_content():
    return [
        featured_image_section(),
    ]


def enterprise_content():
    return [
        trusted_media_content(),
        control_layer_section(),
        showcase(
            block_id="ent-b4-showcase",
            headline="The browser has become the operating surface of modern work.",
            caption_description="It's where work, data, and identity converge. And where security has the least visibility and control. "
            "See our thoughts behind the shift and the analysis to help you read where it's headed.",
            media=get_image_media("ent-b4-showcase-media"),
        ),
        button_row(
            "ent-b5-btnrow",
            buttons=[
                button(
                    "ent-b5-btn1",
                    label="Get our thoughts",
                    url=PRODUCT_URL,
                    analytics_id="d3fcb24b-0675-4d2a-b0d2-7fcd8cf4a661",
                    theme="secondary",
                )
            ],
            spacing="small",
        ),
        two_ways_section(),
        showcase(
            block_id="ent-b7-showcase",
            headline="Transparent, compliant, and secure.",
            caption_description="Firefox Enterprise maps to the frameworks European regulators care about like GDPR, NIS2, DORA, and "
            "SecNumCloud. It also provides source-code access, customer-controlled telemetry boundaries, and "
            "self-hosted diagnostic logs.",
            media=get_image_media("ent-b7-showcase-media"),
        ),
        button_row(
            "ent-b8-btnrow",
            buttons=[
                button(
                    "ent-b8-btn1",
                    label="See the features",
                    url=PRODUCT_URL,
                    analytics_id="01b645c5-86fa-4363-8123-f947f49425f9",
                    theme="secondary",
                )
            ],
            spacing="small",
        ),
        browser_stat_media_content(),
        button_row(
            "ent-b10-btnrow",
            buttons=[
                button(
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
    page.upper_content = enterprise_upper_content()
    page.content = enterprise_content()
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Child pages of the enterprise sub-site (Product, Support, Download, Contact).
# Content reproduced verbatim from the saved firefox.com HTML pages, using the
# shared placeholder imagery. All use the enterprise theme and inherit the
# enterprise navigation from the parent page.
# ---------------------------------------------------------------------------


def enterprise_download(block_id):
    return get_enterprise_download(block_id=block_id, rich_text=get_enterprise_download_rich_text("ed260000-0003-0003-0003"))


def product_content(contact_page):
    return [
        hero(
            block_id="prod-hero",
            superheading_text="Product",
            heading_text="Your Browser. Your Business.",
            subheading_text="Firefox Enterprise gives IT and security teams control over browser policy, data movement, access, "
            "and visibility. Deploy it within the infrastructure your organization controls.",
            buttons=[
                button(
                    "prod-hero-btn",
                    label="Request Early Access",
                    analytics_id="c1000000-0000-0000-0000-000000000001",
                    page=contact_page,
                )
            ],
            media=get_image_media("prod-hero-media"),
        ),
        section(
            section_id="prod-security",
            heading_text="Security",
            subheading_text="Extend your threat defense to the place where work actually happens, while integrating with the DLP, "
            "SIEM, and security tools you already run. Give users secure access to what they need, without hindering "
            "their experience, or adding the infrastructure tax of VPNs, MDM, or virtual desktops.",
            content_blocks=[
                cards_list(
                    block_id="prod-security-cards",
                    cards=[
                        icon_card(
                            "prod-sec-card1",
                            icon="window",
                            headline="Control data at the point of use.",
                            content=(
                                "Stop sensitive data leaks where they happen, including through AI, with content-aware "
                                "inspection within the session, extending your existing DLP to the browser."
                            ),
                        ),
                        icon_card(
                            "prod-sec-card2",
                            icon="shield-cross",
                            headline="Defend against browser-borne threats.",
                            content=(
                                "Block phishing, malicious sites, and credential theft with extension control and policy "
                                "enforcement. Contain risky sites with native isolation that retains performance without "
                                "remote rendering tax or VDI bills."
                            ),
                        ),
                        icon_card(
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
        section(
            section_id="prod-sovereignty",
            heading_text="Sovereignty",
            subheading_text="Define the boundaries for telemetry and browsing data, and deploy on-prem or in an approved hosting "
            "environment. You own the infrastructure with no forced cloud dependency.",
            content_blocks=[
                cards_list(
                    block_id="prod-sovereignty-cards",
                    cards=[
                        icon_card(
                            "prod-sov-card1",
                            icon="warning",
                            headline="Extend DLP to where data actually moves.",
                            content=(
                                "Stop accidental and intentional data loss where it happens and deter what inspection can't "
                                "catch. Close the gap your network and endpoint tools can't see, without ripping out what "
                                "you've already bought."
                            ),
                        ),
                        icon_card(
                            "prod-sov-card2",
                            icon="settings",
                            headline="Close the browser blind spot for your SOC.",
                            content=(
                                "Give security teams real-time visibility into browser-level activity and admin actions, "
                                "where most tooling goes dark."
                            ),
                        ),
                        icon_card(
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
        section(
            section_id="prod-resilience",
            heading_text="Resilience",
            subheading_text="Break free from vendor lock-in, dependencies, and risks by leveraging the only independent, open-source "
            "browser that returns control and infrastructure to your organization.",
            content_blocks=[
                cards_list(
                    block_id="prod-resilience-cards",
                    cards=[
                        icon_card(
                            "prod-res-card1",
                            icon="globe",
                            headline="Stay running when the monoculture breaks.",
                            content=(
                                "Mitigate the risk that a Chromium incident, bad release, or unilateral decision takes your "
                                "workforce offline. True engine diversity plus disciplined change management keeps critical "
                                "workflows operating."
                            ),
                        ),
                        icon_card(
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
        showcase(
            block_id="prod-showcase",
            headline="See Firefox Enterprise in your environment.",
            caption_description="Tell us a bit about your environment and priorities. We'll route your request to the right next step.",
            media=get_image_media("prod-showcase-media"),
        ),
        button_row(
            "prod-close-btnrow",
            buttons=[
                button(
                    "prod-close-btn",
                    label="Request early access",
                    analytics_id="c1000000-0000-0000-0000-000000000002",
                    page=contact_page,
                    theme="secondary",
                )
            ],
        ),
    ]


def support_plans_table():
    """The Premium/Standard support tier table, with the Premium column highlighted."""
    return {
        "type": "comparison_table",
        "value": {
            "highlighted_column": 2,
            "mobile_behavior": "scroll",
            "header_row": [make_header_row("supp-plans")],
            "content_rows": make_content_rows("supp-plans"),
        },
        "id": "supp-plans-table",
    }


def support_content(contact_page):
    return [
        hero(
            block_id="supp-hero",
            superheading_text="Support",
            heading_text="Expert Firefox support, direct from Mozilla.",
            subheading_text="Firefox Professional Support gives your IT team a direct, private path to the people behind the product. "
            "Resolve issues faster with expert triage, guidance, and escalation.",
            buttons=[
                button(
                    "supp-hero-btn",
                    label="Contact Sales",
                    analytics_id="c2000000-0000-0000-0000-000000000001",
                    page=contact_page,
                )
            ],
            media=get_image_media("supp-hero-media"),
        ),
        section(
            section_id="supp-cards-section",
            heading_text="Real people. Faster answers.",
            content_blocks=[
                cards_list(
                    block_id="supp-cards",
                    cards=[
                        icon_card(
                            "supp-card1",
                            icon="arrow-trending",
                            content=("A direct escalation path with guaranteed response times to keep rollouts and critical work on track"),
                        ),
                        icon_card(
                            "supp-card2",
                            icon="closed-caption",
                            content="A private support portal for incident handling and diagnosis to ensure timely resolution",
                        ),
                        icon_card(
                            "supp-card3",
                            icon="applied-policy",
                            content=("Expert integration guidance across enterprise policies, supported apps, updates, extensions, and certificates"),
                        ),
                        icon_card(
                            "supp-card4",
                            icon="avatar-signed-out",
                            content="Named contacts, business reviews, and local-language support on higher tiers",
                        ),
                    ],
                    cards_per_row="2",
                )
            ],
        ),
        section(
            section_id="supp-plans-section",
            heading_text="Choose your level of coverage.",
            subheading_text="Paid support plans for the free-to-download Firefox and Firefox ESR your team already manages. "
            "No platform migration required.",
            content_blocks=[support_plans_table()],
        ),
        media_content(
            block_id="supp-feature",
            heading_text="Going further? Support comes built in.",
            subheading_text="Firefox Enterprise adds centralized management, built-in DLP, SIEM integration, and sovereign deployment "
            "with our highest tier of support included. No separate support contract.",
            body_blocks=[
                rich_text(
                    "supp-feature-body2",
                    '<ul><li data-block-key="suppfb2a">24×7 coverage</li>'
                    '<li data-block-key="suppfb2b">15-minute response for business-halting incidents</li>'
                    '<li data-block-key="suppfb2c">Named Success Lead</li>'
                    '<li data-block-key="suppfb2d">Monthly business reviews</li></ul>',
                ),
            ],
            media=get_image_media("supp-feature-media"),
        ),
        rich_text(
            "supp-fineprint",
            '<h2 data-block-key="suppfp0">The fine print.</h2>'
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
        banner(
            "supp-banner",
            theme="purple-radial-gradient",
            heading_text="Let's talk before your next rollout.",
            subheading_text="A short call will help us understand your Firefox footprint and which level of support fits.",
            buttons=[
                button(
                    "supp-banner-btn",
                    label="Talk to an expert",
                    analytics_id="c2000000-0000-0000-0000-000000000002",
                    page=contact_page,
                )
            ],
        ),
    ]


def download_content(contact_page):
    return [
        intro(
            block_id="dl-intro",
            heading_text="Use Firefox as your enterprise browser",
            subheading_text="Firefox delivers secure, resilient, and privacy-focused browsing at scale. With enterprise policies in "
            "both Firefox or Firefox Extended Support Release (ESR), organizations get flexibility, control, and "
            "transparency in a trusted, open-source browser.",
            content_blocks=[
                buttons_block(
                    "dl-intro-btns",
                    [
                        download_button(
                            "dl-intro-dlbtn",
                            label="Download",
                            analytics_id="c3000000-0000-0000-0000-000000000001",
                        )
                    ],
                )
            ],
            layout="right",
            remove_border_radius=True,
            media=get_image_media("dl-intro-media"),
        ),
        banner(
            "dl-banner-1",
            theme="purple-radial-gradient",
            heading_text="Firefox Professional Support",
            subheading_text=(
                "Early access is now open for our new support program. Built for organizations that use Firefox to ensure "
                "security, resilience, and data sovereignty, it provides private, reliable, and custom support for "
                "large-scale deployments."
            ),
            buttons=[
                button(
                    "dl-banner-1-btn",
                    label="Contact Sales",
                    analytics_id="c3000000-0000-0000-0000-000000000002",
                    page=contact_page,
                )
            ],
        ),
        section(
            section_id="dl-cards-section",
            heading_text="Enterprise-grade protection, powered by Firefox",
            content_blocks=[
                cards_list(
                    block_id="dl-cards",
                    cards=[
                        pictogram_card(
                            block_id="dl-card1",
                            headline="Your browser, your business",
                            content="Firefox combines open-source transparency with advanced security features and frequent "
                            "updates to help safeguard your organization's data.",
                            pictogram=get_image_variants(),
                        ),
                        pictogram_card(
                            block_id="dl-card2",
                            headline="Deploy when and how you want",
                            content="With install packages and a wide expansion of group policies and features, deployment is "
                            "faster and more flexible than ever — and a breeze for Windows, Linux, and macOS environments.",
                            pictogram=get_image_variants(),
                        ),
                        pictogram_card(
                            block_id="dl-card3",
                            headline="Release cycles that fit your organization",
                            content="Choose Firefox for the latest features and stable releases every four weeks, or Firefox ESR "
                            "for long-term stability, regular security updates, and annual major releases.",
                            pictogram=get_image_variants(),
                        ),
                    ],
                )
            ],
        ),
        banner(
            "dl-banner-2",
            theme="dark-purple-gradient-inverted",
            heading_text="Firefox Professional Support documentation",
            subheading_text=(
                "Firefox Professional Support is a dedicated offering for teams who need private issue triage and "
                "escalation, defined response times, custom development options, and close collaboration with Mozilla's "
                "engineering and product teams."
            ),
            buttons=[
                button(
                    "dl-banner-2-btn",
                    label="Support Plan",
                    analytics_id="c3000000-0000-0000-0000-000000000003",
                    url="https://www.mozilla.org/firefox/enterprise/",
                )
            ],
        ),
        enterprise_download("dl-enterprise-download"),
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
    page.content = product_content(contact_page)
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
    page.content = support_content(contact_page)
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
    page.content = download_content(contact_page)
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
            "basket_api_path": BASKET_CONTACT_ENTERPRISE_PATH,
            "form_fields": get_form_field_variants_with_fieldsets(),
            "thank_you_message": '<p data-block-key="entctty">Thanks for reaching out! We\'ll be in touch about early access.</p>',
        },
    )
    page.theme = "enterprise"
    page.intro = [
        intro(
            block_id="ent-contact-intro",
            heading_text="Request early access",
            subheading_text="Tell us about your organization and we'll get back to you about Firefox Enterprise.",
            content_blocks=[],
            layout="vertical",
            media=[],
        )
    ]
    page.form_fields = get_form_field_variants_with_fieldsets()
    page.basket_api_path = BASKET_CONTACT_ENTERPRISE_PATH
    page.thank_you_message = '<p data-block-key="entctty">Thanks for reaching out! We\'ll be in touch about early access.</p>'
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Enterprise navigation snippet + sub-site coordinator.
# ---------------------------------------------------------------------------


def get_enterprise_logo(title, filename) -> SpringfieldImage:
    """Load (idempotently) an enterprise logo from the media directory."""
    image = SpringfieldImage.objects.filter(title=title).first()
    if image:
        return image
    file_path = Path(settings.ROOT) / "media" / "img" / "logos" / "firefox-enterprise" / filename
    with file_path.open("rb") as logo_file:
        return SpringfieldImage.objects.create(title=title, file=ContentFile(logo_file.read(), name=filename))


def get_enterprise_navigation_snippet(parent, product_page, support_page, contact_page) -> NavigationSnippet:
    locale = Locale.get_default()
    snippet, _ = NavigationSnippet.objects.update_or_create(
        name="Enterprise navigation",
        locale=locale,
        defaults={
            "items": [
                nav_top_level_link(block_id="ent-nav-overview", label="Overview", page=parent, analytics_id="c5000000-0000-0000-0000-000000000005"),
                nav_top_level_link(
                    block_id="ent-nav-product", label="Product", page=product_page, analytics_id="c5000000-0000-0000-0000-000000000001"
                ),
                nav_top_level_link(
                    block_id="ent-nav-support", label="Support", page=support_page, analytics_id="c5000000-0000-0000-0000-000000000002"
                ),
            ],
            "logo": get_enterprise_logo("Firefox Enterprise Logo", "firefox-enterprise-orange.svg"),
            "logo_alt": "Firefox Enterprise",
            "logo_dark": None,
            "logo_link": [{"type": "link", "value": link_value(page=parent), "id": "ent-nav-logolink"}],
            "cta_button": [
                {
                    "type": "button",
                    "value": [
                        button(
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
