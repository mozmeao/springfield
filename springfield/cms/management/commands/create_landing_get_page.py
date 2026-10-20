# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Create the draft CMS scaffold for /landing/get/, from firefox/landing/get-new.html.

English text is copied from the *values* in l10n/en/firefox/download/desktop.ftl, not from the
message ids. build_text_to_msgid_mapping() matches translations by normalized English text, so text
that differs from the FTL value goes untranslated in silence.
"""

from springfield.cms.blocks import BUTTON_LINK, UITOUR_BUTTON_PROTECTIONS_REPORT
from springfield.cms.management.commands._page_scaffold import (
    FTL_TARGET_LOCALE_CODES,
    CreatePageCommand,
    PageSpec,
    build_rich_text,
    get_pretranslated_label,
    import_static_image,
)
from springfield.cms.models import FreeFormPage2026

LANDING_GET_IMAGE_DIRECTORY = "img/firefox/landing/get"

# get-new.html:15 appends these to every outbound link on the page.
CAMPAIGN_QUERY = "utm_source=www.firefox.com&utm_medium=referral&utm_campaign=firefox-landing-get-refresh"

EXTENSIONS_URL = f"https://addons.mozilla.org/firefox/extensions/?{CAMPAIGN_QUERY}"
# get-new.html:376 drops the trailing slash on this one. Kept as it is so the two links stay
# distinguishable in analytics, which is the only thing that tells them apart.
EXTENSIONS_NO_SLASH_URL = f"https://addons.mozilla.org/firefox/extensions?{CAMPAIGN_QUERY}"
FACEBOOK_CONTAINER_URL = f"https://addons.mozilla.org/firefox/addon/facebook-container?{CAMPAIGN_QUERY}"
MOZILLA_ACCOUNT_URL = f"https://accounts.firefox.com/signin?{CAMPAIGN_QUERY}"
MOZILLA_ABOUT_URL = f"https://www.mozilla.org/about/?{CAMPAIGN_QUERY}"
MOZILLA_PRIVACY_URL = f"https://www.mozilla.org/privacy/?{CAMPAIGN_QUERY}"
SCREENSHOTS_URL = f"https://support.mozilla.org/kb/firefox-screenshots?{CAMPAIGN_QUERY}"
FIREFOX_SUPPORT_URL = f"https://support.mozilla.org/products/firefox?{CAMPAIGN_QUERY}&utm_content=browser-support"
# get-new.html:456 and :463 — the heading reads "Get help with your installation", but the template
# points it at the marketing-data article. Copied as the template has it; see the task report.
INSTALLATION_HELP_URL = "https://support.mozilla.org/kb/marketing-data"

# LinkBlock stores every link type side by side and blanks the ones it is not using. Spelling the
# unused ones out keeps wagtail-localize away from the None an absent CharBlock would store.
EMPTY_LINK = {
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


def import_get_image(file_name: str, title: str, description: str = ""):
    """Import one of the page's illustrations, at the resolution get-new.html serves to 2x screens.

    Wagtail resizes down from whatever it is given, and the 1x file is too small for the widths the
    block templates ask for. Everything on this page carries an empty alt or aria-hidden except the
    two images described as "firefox.com", so an image with no description is decorative.
    """
    return import_static_image(
        static_path=f"{LANDING_GET_IMAGE_DIRECTORY}/{file_name}",
        title=title,
        description=description,
        is_decorative=not description,
    )


def build_link(url: str, text: str) -> str:
    """An <a> for rich text. The & separating query parameters has to be escaped in HTML."""
    return f'<a href="{url.replace("&", "&amp;")}">{text}</a>'


def build_heading(block_id: str, heading: str, subheading: str = "", superheading: str = "") -> dict:
    """HeadingBlock's three fields are optional RichTextBlocks, and an unset one stores None, which
    wagtail-localize's segment extractor rejects. Hence "" rather than an absent key."""
    return {
        "superheading_text": build_rich_text(f"{block_id}-sup", superheading) if superheading else "",
        "heading_text": build_rich_text(f"{block_id}-h", heading) if heading else "",
        "subheading_text": build_rich_text(f"{block_id}-sub", subheading) if subheading else "",
    }


def build_bullet_list(block_id: str, items: list[str]) -> str:
    """EXPANDED_TEXT_FEATURES allows ul, and each li becomes its own translation segment."""
    list_items = "".join(f'<li data-block-key="{block_id}-{index}">{item}</li>' for index, item in enumerate(items, start=1))
    return f"<ul>{list_items}</ul>"


def build_image_media(block_id: str, image) -> list[dict]:
    return [{"type": "image", "id": f"{block_id}-media", "value": {"image": image.pk, "settings": {}}}]


def build_download_button(block_id: str) -> dict:
    return {
        "type": "download_button",
        "id": block_id,
        "value": {"pretranslated_label": get_pretranslated_label("download_firefox"), "custom_label": "", "settings": {}},
    }


def build_link_button(block_id: str, label: str, link: dict) -> dict:
    """get-new.html renders these as bare <a> text, which is what the "link" button theme is for."""
    return {
        "type": "button",
        "id": block_id,
        "value": {
            "settings": {"theme": BUTTON_LINK},
            "pretranslated_label": None,
            "custom_label": label,
            "link": {**EMPTY_LINK, **link},
        },
    }


def build_buttons(block_id: str, buttons: list[dict]) -> dict:
    return {"type": "buttons", "id": f"{block_id}-buttons", "value": buttons}


def build_media_content(*, block_id: str, image, heading: str, subheading: str, buttons: list[dict], media_after: bool = False) -> dict:
    """One panel of the "has got you" section.

    MediaContentBlock.content is a required StreamBlock (blocks.py:2070-2087), so a panel cannot be
    built without it. The buttons under each panel's copy in get-new.html are what it is for — see
    fixtures/block_factories.py:222-232, where the heading carries the copy and `content` the rest.
    """
    return {
        "type": "media_content",
        "id": block_id,
        "value": {
            "settings": {"media_after": media_after, "narrow": False, "remove_border_radius": False},
            "media": build_image_media(block_id, image),
            "heading": build_heading(block_id, heading, subheading),
            "content": [build_buttons(block_id, buttons)],
        },
    }


def build_image_caption(block_id: str, image) -> dict:
    """A standalone illustration. Its caption stays empty: get-new.html gives the image none."""
    return {
        "type": "image_caption",
        "id": block_id,
        "value": {
            "image": {"image": image.pk, "settings": {}},
            "caption": "",
            "link": dict(EMPTY_LINK),
            "layout": "default",
        },
    }


def build_card(*, block_id: str, heading: str, body: str, icon: str = "", image=None) -> dict:
    """One card of a cards_list: an icon or a pictogram, a heading, and a rich text body."""
    if icon:
        media = [{"type": "icon", "id": f"{block_id}-icon", "value": icon}]
    elif image is not None:
        media = [{"type": "pictogram", "id": f"{block_id}-pictogram", "value": {"image": image.pk, "settings": {}}}]
    else:
        media = []

    return {
        "type": "card",
        "id": block_id,
        "value": {
            "settings": {},
            "media": media,
            "content": [
                {"type": "heading", "id": f"{block_id}-heading", "value": build_heading(block_id, heading)},
                {"type": "content", "id": f"{block_id}-body", "value": body},
            ],
        },
    }


def build_cards_list(block_id: str, cards: list[dict], cards_per_row: str = "") -> dict:
    return {
        "type": "cards_list",
        "id": block_id,
        "value": {
            "settings": {"container_width": "", "cards_per_row": cards_per_row, "two_wide_xs": False},
            "cards": cards,
        },
    }


def build_section(*, block_id: str, heading: str, content: list[dict], cta: list[dict] | None = None) -> dict:
    return {
        "type": "section",
        "id": block_id,
        "value": {
            "settings": {"anchor_id": ""},
            "heading": build_heading(block_id, heading),
            "content": content,
            "cta": cta or [],
        },
    }


def build_hero_block() -> dict:
    """get-new.html:47-76 — the h1, the download CTA and the two text links beneath it."""
    block_id = "landing-get-hero"
    return {
        "type": "intro",
        "id": block_id,
        "value": {
            "settings": {"slim": True, "layout": "right", "full_width": False, "anchor_id": ""},
            "heading": build_heading(
                block_id,
                "Get the browser that protects what’s important",
                "Fast, reliable and private — for peace of mind online.",
                "Firefox Browser",
            ),
            "media": build_image_media(block_id, import_get_image("browser-high-res.png", "Firefox download page browser", "firefox.com")),
            "content": [
                {
                    "type": "buttons",
                    "id": f"{block_id}-buttons",
                    "value": [
                        build_download_button(f"{block_id}-download"),
                        build_link_button(
                            f"{block_id}-download-options",
                            "Download options and other languages",
                            {"link_to": "relative_url", "relative_url": "/download/all/desktop-release/"},
                        ),
                        build_link_button(
                            f"{block_id}-support",
                            "Firefox Browser support",
                            {"link_to": "custom_url", "custom_url": FIREFOX_SUPPORT_URL, "new_window": True},
                        ),
                    ],
                },
            ],
        },
    }


def build_has_got_you_section() -> dict:
    """get-new.html:82-141 — "Do what you do online", and its three media panels.

    Each panel keeps its own trailing control, as get-new.html has it. section.cta could not have
    held all three anyway: it is max_num=1 (blocks.py:2993-2999).
    """
    return build_section(
        block_id="landing-get-has-got-you",
        heading="Do what you do online.<br/> Firefox Browser has got you <strong>covered</strong>.",
        content=[
            build_media_content(
                block_id="landing-get-block-tracking",
                image=import_get_image("block-tracking-high-res.png", "Firefox download page ad tracker blocking illustration"),
                heading="We block the ad trackers. You explore the internet faster.",
                subheading=(
                    "Ads are distracting and make web pages load slower while their trackers watch every move you make "
                    "online. The Firefox Browser blocks most trackers automatically, so there’s no need to dig into your "
                    "security settings."
                ),
                buttons=[
                    {
                        "type": "uitour_button",
                        "id": "landing-get-protections-report-button",
                        "value": {
                            "settings": {"theme": "ghost"},
                            "button_type": UITOUR_BUTTON_PROTECTIONS_REPORT,
                            "wallpaper": "",
                            "pretranslated_label": None,
                            "custom_label": "See your protection report",
                        },
                    }
                ],
            ),
            build_media_content(
                block_id="landing-get-for-everyone",
                image=import_get_image("kit-heart-high-res.jpg", "Firefox download page Kit with a heart illustration"),
                heading="Firefox is for everyone",
                subheading=(
                    "Available in over 90 languages, and compatible with Windows, Mac and Linux machines, Firefox works "
                    "no matter what you’re using or where you are. Make sure your operating system is up to date for the "
                    "best experience."
                ),
                buttons=[
                    build_link_button(
                        "landing-get-system-requirements-link",
                        "Review system requirements",
                        {"link_to": "relative_url", "relative_url": "/firefox/system-requirements/"},
                    )
                ],
                media_after=True,
            ),
            build_media_content(
                block_id="landing-get-all-devices",
                image=import_get_image("all-devices-high-res.png", "Firefox download page all devices illustration"),
                heading="Put Firefox on all your devices",
                subheading=(
                    "Take your privacy with you everywhere. Firefox Browsers for iOS and Android have the same strong "
                    "privacy settings to block trackers from following you around the web, no matter where you are."
                ),
                buttons=[{"type": "store_button", "id": f"landing-get-store-{store}", "value": {"store": store}} for store in ("android", "ios")],
            ),
        ],
    )


def build_do_it_all_section() -> dict:
    """get-new.html:143-246 — six icon-list items, each a heading over a bullet list."""
    features = [
        (
            "search",
            "Search smarter, faster",
            ["Search from address bar", "Search engine options", "Smart search suggestions", "Bookmark, history and open tab in results"],
        ),
        (
            "arrow-trending",
            "Boost your productivity",
            [
                "Works with Google products",
                "Built-in screenshot tool",
                "Bookmarks manager",
                "Autosuggest URLs",
                "Sync across devices",
                "Reader mode",
                "Spell check",
                "Pinned Tabs",
            ],
        ),
        (
            "canvas-true",
            "Stream, share and play",
            ["Block Autoplay of video &amp; audio", "Picture-in-Picture", "Curated content on new tab", "Share links"],
        ),
        (
            "private-mode-fill",
            "Protect your privacy",
            ["Third Party Cookie Blocking", "Fingerprinter Blocking", "Private Browsing mode", "Individual protections report"],
        ),
        (
            "lock",
            "Secure your personal info",
            ["Breached website alerts", "Built-in password manager", "Clear history", "Form autofill", "Automatic updates"],
        ),
        (
            "edit",
            "Customize your browser",
            ["Themes", "Dark mode", "Library of extensions", "Adjust search bar settings", "Change new tab layout"],
        ),
    ]
    cards = [
        build_card(
            block_id=f"landing-get-do-it-all-{icon}",
            heading=heading,
            body=build_bullet_list(f"landing-get-do-it-all-{icon}", bullets),
            icon=icon,
        )
        for icon, heading, bullets in features
    ]
    return build_section(
        block_id="landing-get-do-it-all",
        heading="Do it <strong>all</strong> with Firefox",
        content=[build_cards_list("landing-get-do-it-all-cards", cards)],
        cta=[build_download_button("landing-get-do-it-all-download")],
    )


def build_make_it_your_own_section() -> dict:
    """get-new.html:250-291 — three icon-list items. The illustration that closes the section in
    get-new.html:288 follows as a sibling block: section.content holds no image block."""
    items = [
        (
            "extension-fill",
            "Extensions for every interest",
            "From security to news to gaming, there’s an "
            f"{build_link(EXTENSIONS_URL, 'extension for everyone')}. Add as many as you want until your browser is just right.",
        ),
        (
            "edit-squiggle",
            "Change up your look",
            "Go from light mode to dark mode depending on your mood or preference, or liven things up with a custom theme "
            "(rainbow unicorn, perhaps).",
        ),
        (
            "settings",
            "Tweak your settings",
            "There’s no need to settle. Change up the new tab page, search bar, bookmarks and more to explore the internet the way you want.",
        ),
    ]
    cards = [
        build_card(
            block_id=f"landing-get-make-it-yours-{icon}",
            heading=heading,
            body=build_rich_text(f"landing-get-make-it-yours-{icon}-body", body),
            icon=icon,
        )
        for icon, heading, body in items
    ]
    return build_section(
        block_id="landing-get-make-it-yours",
        heading="Make <strong>Firefox</strong> your own",
        content=[build_cards_list("landing-get-make-it-yours-cards", cards)],
    )


def build_non_profit_section() -> dict:
    """get-new.html:293-339 — "Backed by the non-profit", as two cards.

    get-new.html builds this from the card-gallery component, but the card_gallery block requires a
    third "callout" card with its own headline and description, and an icon on each of the other
    two. get-new.html has none of those four strings, and inventing them would put English on the
    page that no FTL file can translate. Two cards carry the same content with nothing made up.
    """
    cards = [
        build_card(
            block_id="landing-get-non-profit-challenging",
            heading="Challenging the status quo since 1998",
            body=build_rich_text(
                "landing-get-non-profit-challenging-body",
                f"Firefox was created by {build_link(MOZILLA_ABOUT_URL, 'Mozilla')} as a faster, more private alternative "
                "to browsers like Internet Explorer, and now Chrome. Today, our mission-driven company and volunteer "
                "community continue to put your privacy above all else.",
            ),
            image=import_get_image("browser-kit-high-res.png", "Firefox download page browser with Kit illustration"),
        ),
        build_card(
            block_id="landing-get-non-profit-privacy",
            heading="Your privacy comes first",
            body=build_rich_text(
                "landing-get-non-profit-privacy-body",
                "As the internet grows and changes, Firefox continues to focus on your right to privacy — that’s always "
                f"been our thing. Learn more about our data practices in our {build_link(MOZILLA_PRIVACY_URL, 'Privacy Notice')}.",
            ),
            image=import_get_image("keyhole-high-res.png", "Firefox download page keyhole illustration"),
        ),
    ]
    return build_section(
        block_id="landing-get-non-profit",
        heading="Backed by the <strong>non-profit</strong> that puts people first",
        content=[build_cards_list("landing-get-non-profit-cards", cards)],
    )


def build_favourites_section() -> dict:
    """get-new.html:341-452 — six cards, three to a row (blocks.py:2371)."""
    favourites = [
        (
            "works-with-google",
            "kit-with-google-high-res.png",
            "Firefox download page Kit with Google illustration",
            "Works with Google products",
            "All your favorite Google tools (like Gmail and Docs) work seamlessly in the Firefox Browser.",
        ),
        (
            "tracking-protection",
            "etp-high-res.png",
            "Firefox download page Enhanced Tracking Protection illustration",
            "Enhanced Tracking Protection (ETP)",
            f"Firefox automatically {build_link(EXTENSIONS_NO_SLASH_URL, 'blocks many third party trackers')} from "
            "collecting and selling your web activity.",
        ),
        (
            "sync",
            "kit-running-high-res.png",
            "Firefox download page Kit running illustration",
            "Sync your devices",
            "Firefox is available on all your devices; take your tabs, history and bookmarks with you. All you need is a "
            f"{build_link(MOZILLA_ACCOUNT_URL, 'Mozilla account')} and you’ll get access to syncing and more Mozilla products.",
        ),
        (
            "screenshots",
            "screenshot-high-res.png",
            "Firefox download page screenshot tool illustration",
            "Screenshots",
            f"Grab a high-resolution image of anything online with our {build_link(SCREENSHOTS_URL, 'screenshot')} tool built right in the browser",
        ),
        (
            "facebook-container",
            "kit-plant-high-res.png",
            "Firefox download page Kit with a plant illustration",
            "Facebook Container",
            f"{build_link(FACEBOOK_CONTAINER_URL, 'Download this browser extension')} to stop Facebook (and Instagram) "
            "from tracking you around the web.",
        ),
        (
            "picture-in-picture",
            "picture-in-picture-high-res.png",
            "Firefox download page Picture-in-Picture illustration",
            "Picture-in-Picture",
            "From watching a web tutorial to keeping an eye on your favorite team, your video follows you while you multitask.",
        ),
    ]
    cards = [
        build_card(
            block_id=f"landing-get-favourite-{name}",
            heading=heading,
            body=build_rich_text(f"landing-get-favourite-{name}-body", body),
            image=import_get_image(file_name, title),
        )
        for name, file_name, title, heading, body in favourites
    ]
    return build_section(
        block_id="landing-get-favourites",
        heading="Keep all your favorite browser features — and <strong>discover</strong> new ones.",
        content=[build_cards_list("landing-get-favourite-cards", cards, cards_per_row="3")],
        cta=[build_download_button("landing-get-favourites-download")],
    )


def build_get_help_banner() -> dict:
    """get-new.html:456-467 — the closing banner, with the sitting Kit."""
    block_id = "landing-get-help"
    return {
        "type": "kit_banner",
        "id": block_id,
        "value": {
            "settings": {"theme": "filled-face", "background_theme": "purple-radial-gradient", "anchor_id": ""},
            "heading": build_heading(
                block_id,
                f"Having trouble? {build_link(INSTALLATION_HELP_URL, 'Get help with your installation')}.",
            ),
            "content": [],
        },
    }


def build_fields() -> dict:
    return {
        # get-new.html:9-11 and :28-36 — the opt-out checkbox, the firefox_marketing_opt_out
        # bundles, data-promoted-page and the noindex robots meta all hang off this one flag.
        "enable_marketing_attribution": True,
        "show_pre_footer": False,
        "upper_content": [build_hero_block()],
        "content": [
            build_has_got_you_section(),
            build_do_it_all_section(),
            build_make_it_your_own_section(),
            build_image_caption(
                "landing-get-make-it-yours-illustration",
                import_get_image("browser-kit-tail-high-res.png", "Firefox download page browser with Kit's tail", "firefox.com"),
            ),
            build_non_profit_section(),
            build_favourites_section(),
            build_get_help_banner(),
        ],
    }


class Command(CreatePageCommand):
    help = "Create the draft CMS scaffold for /landing/get/."

    spec = PageSpec(
        slug="get",
        page_model=FreeFormPage2026,
        parent_slugs=("landing",),
        title="Download Firefox",
        ftl_relative_paths=("firefox/download/desktop.ftl", "firefox/download/home.ftl"),
        target_locale_codes=FTL_TARGET_LOCALE_CODES,
        build_fields=build_fields,
        editor_notes=(
            "retarget the 'Get help with your installation' link: the live page points it at the "
            "marketing-data article, which the FTL comment contradicts. Migrated as-is rather than "
            "fixed, because changing behaviour is a separate decision from moving the page.",
            "check the imported images carry useful alt text",
        ),
    )
