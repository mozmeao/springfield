# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# ruff: noqa: E501

"""
Fixtures for Firefox feature pages.

These fixtures create ArticleDetailPage instances for each feature page,
allowing them to be served via the CMS instead of Django views.

IMPORTANT: The content in FEATURE_PAGES must match the FTL source strings exactly
(after brand term expansion) for translation import to work correctly.

FTL brand terms are expanded as follows:
    { -brand-name-firefox } -> Firefox
    { -brand-name-firefox-browser } -> Firefox Browser
    { -brand-name-mozilla } -> Mozilla
    { -brand-name-mozilla-account } -> Mozilla account
    { -brand-name-gecko } -> Gecko
    { -brand-name-firefox-translations } -> Firefox Translations

Links use standard HTML <a href="..."> format. Wagtail-Localize extracts the href
as an OverridableSegment, allowing translators to modify the URL if needed.
The FTL import script normalizes both <a href="..."> and <a { $url }> to <a>
for matching purposes.

Images use placeholders like {IMG:eyedropper} in content. These are replaced
with actual Wagtail image embed tags after images are imported.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.files.images import ImageFile

from wagtail.models import Locale, Site

from springfield.cms.models import ArticleDetailPage, ArticleIndexPage, SpringfieldImage

# =============================================================================
# Image Definitions
# =============================================================================
#
# Images are imported from static files into Wagtail's media library.
# Alt text is sourced from FTL files (with brand terms expanded).
# Content uses {IMG:key} placeholders that are replaced with actual embed tags.
# =============================================================================

FEATURE_IMAGES = {
    # fast (featured image)
    "fast": {
        "file": "img/firefox/features/fast.png",
        "title": "Firefox speed illustration",
        "alt": "",
    },
    # eyedropper
    "eyedropper": {
        "file": "img/firefox/features/eyedropper.png",
        "title": "Eyedropper tool screenshot",
        "alt": "Screenshot of the eyedropper tool in Firefox showing the hexadecimal color value of a single pixel on a web page.",
    },
    # pinned-tabs
    "pinned-tabs": {
        "file": "img/firefox/features/pinned-tabs.png",
        "title": "Pinned tabs screenshot",
        "alt": "",
    },
    "pinned-tab-notification": {
        "file": "img/firefox/features/pinned-tab-notification.png",
        "title": "Pinned tab notification screenshot",
        "alt": "",
    },
    # add-ons
    "addons": {
        "file": "img/firefox/features/addons.png",
        "title": "Firefox add-ons screenshot",
        "alt": "",
    },
    # customize
    "default-themes": {
        "file": "img/firefox/features/default-themes.jpg",
        "title": "Default Firefox themes",
        "alt": "Image of the default themes that come with Firefox, showing light, dark and colorful variations.",
    },
    "custom-themes": {
        "file": "img/firefox/features/custom-themes.jpg",
        "title": "Custom Firefox themes",
        "alt": "Image of three custom Firefox themes: a dark purple and pink theme with white and orange accents, a light beige theme featuring a watercolor painting of birds and cherry blossoms, and a dark black and green theme featuring a high-tech circuitry pattern.",
    },
    # private-browsing
    "private-browsing": {
        "file": "img/firefox/features/private-browsing.png",
        "title": "Private browsing window screenshot",
        "alt": "A Firefox browser window in private browsing mode.",
    },
    # bookmarks
    "bookmark-manager": {
        "file": "img/firefox/features/bookmark-manager.png",
        "title": "Bookmark manager screenshot",
        "alt": "Image of the bookmark manager window in Firefox.",
    },
    "import-wizard": {
        "file": "img/firefox/features/import-wizard.png",
        "title": "Import wizard screenshot",
        "alt": "Image of the Firefox import wizard dialog, showing options to import settings and data from other browsers.",
    },
    "bookmark-toolbar": {
        "file": "img/firefox/features/bookmark-toolbar.png",
        "title": "Bookmark toolbar screenshot",
        "alt": "Image of Firefox showing a collection of bookmarks in a toolbar at the top of the browser window.",
    },
    # sync
    "sync": {
        "file": "img/firefox/features/sync.jpg",
        "title": "Firefox sync illustration",
        "alt": "",
    },
    "send-tab": {
        "file": "img/firefox/features/send-tab.png",
        "title": "Send tab screenshot",
        "alt": 'An image of a Firefox application menu highlighting the "Send Tab to Device" option.',
    },
    # password-manager
    "password-autofill": {
        "file": "img/firefox/features/password-autofill.png",
        "title": "Password autofill screenshot",
        "alt": "Image of a website's login form with Firefox showing multiple saved accounts to choose from when logging in.",
    },
    "password-suggest": {
        "file": "img/firefox/features/password-suggest.png",
        "title": "Password suggestion screenshot",
        "alt": "Image of a website's sign up form with Firefox suggesting a strong password that it will automatically store for future use.",
    },
    "password-breach-alert": {
        "file": "img/firefox/features/password-breach-alert.png",
        "title": "Password breach alert screenshot",
        "alt": 'Image of the Firefox password manager displaying an alert message that reads "This password has been used on another account that was likely in a data breach. Reusing credentials puts all your accounts at risk. Change this password."',
    },
    # adblocker
    "content-blocking-title": {
        "file": "img/firefox/features/adblocker/content-blocking-title.png",
        "title": "Content blocking title screenshot",
        "alt": "",
    },
    "content-blocking": {
        "file": "img/firefox/features/adblocker/content-blocking.png",
        "title": "Content blocking screenshot",
        "alt": "",
    },
    "content-blocking-custom": {
        "file": "img/firefox/features/adblocker/content-blocking-custom.png",
        "title": "Custom content blocking screenshot",
        "alt": "",
    },
    "custom-trackers": {
        "file": "img/firefox/features/adblocker/custom-trackers.png",
        "title": "Custom trackers screenshot",
        "alt": "",
    },
    "third-party-cookies": {
        "file": "img/firefox/features/adblocker/third-party-cookies.png",
        "title": "Third-party cookies screenshot",
        "alt": "",
    },
    # pdf-editor
    "edit-pdf-text": {
        "file": "img/firefox/features/edit-pdf/edit-pdf-text.png",
        "title": "PDF editor text tool screenshot",
        "alt": "",
    },
    "edit-pdf-draw": {
        "file": "img/firefox/features/edit-pdf/edit-pdf-draw.png",
        "title": "PDF editor draw tool screenshot",
        "alt": "",
    },
    "edit-pdf-alt-text": {
        "file": "img/firefox/features/edit-pdf/edit-pdf-alt-text.png",
        "title": "PDF editor alt text tool screenshot",
        "alt": "",
    },
    "edit-pdf-highlight": {
        "file": "img/firefox/features/edit-pdf/edit-pdf-highlight.png",
        "title": "PDF editor highlight tool screenshot",
        "alt": "",
    },
    "edit-pdf-signature": {
        "file": "img/firefox/features/edit-pdf/edit-pdf-signature.png",
        "title": "PDF editor signature tool screenshot",
        "alt": "",
    },
    "edit-pdf-comment": {
        "file": "img/firefox/features/edit-pdf/edit-pdf-comment.png",
        "title": "PDF editor comment tool screenshot",
        "alt": "",
    },
    # picture-in-picture
    "picture-in-picture-video-poster": {
        "file": "img/firefox/features/pip/video-poster.jpg",
        "title": "Picture-in-Picture video poster",
        "alt": "",
    },
    "pip-lecture": {
        "file": "img/firefox/features/pip/pip-lecture.svg",
        "title": "Picture-in-Picture lecture icon",
        "alt": "",
    },
    "pip-cook": {
        "file": "img/firefox/features/pip/pip-cook.svg",
        "title": "Picture-in-Picture cooking icon",
        "alt": "",
    },
    "pip-entertain": {
        "file": "img/firefox/features/pip/pip-entertain.svg",
        "title": "Picture-in-Picture entertainment icon",
        "alt": "",
    },
}


def import_feature_images() -> dict[str, int]:
    """
    Import all feature images into Wagtail's media library.

    Returns:
        Dict mapping image keys to their database IDs

    Raises:
        FileNotFoundError: If any image file is not found
    """
    image_ids = {}

    for key, info in FEATURE_IMAGES.items():
        # Check if image already exists by title (for idempotency)
        existing = SpringfieldImage.objects.filter(title=info["title"]).first()
        if existing:
            image_ids[key] = existing.id
            continue

        # Find the source file in static files
        static_path = Path(settings.ROOT) / "media" / info["file"]
        if not static_path.exists():
            raise FileNotFoundError(f"Feature image not found: {static_path}")

        # Create the image
        with open(static_path, "rb") as f:
            image = SpringfieldImage(title=info["title"])
            image.file.save(
                static_path.name,
                ImageFile(f, name=static_path.name),
                save=True,
            )
            image_ids[key] = image.id
            print(f"  Imported image: {info['title']}")

    return image_ids


def replace_image_placeholders(content: str, image_ids: dict[str, int]) -> str:
    """
    Replace {IMG:key} placeholders with Wagtail image embed tags.

    Args:
        content: HTML content with {IMG:key} placeholders
        image_ids: Dict mapping image keys to their database IDs

    Returns:
        Content with placeholders replaced by embed tags

    Raises:
        ValueError: If a placeholder references an unknown image key
    """

    def replace_placeholder(match):
        key = match.group(1)
        if key not in FEATURE_IMAGES:
            raise ValueError(f"Unknown image key in placeholder: {key}")
        if key not in image_ids:
            raise ValueError(f"Image not imported for placeholder: {key}")

        image_id = image_ids[key]
        alt = FEATURE_IMAGES[key]["alt"]
        # Escape quotes in alt text for the attribute
        alt_escaped = alt.replace('"', "&quot;")
        return f'<embed alt="{alt_escaped}" embedtype="image" format="fullwidth" id="{image_id}"/>'

    return re.sub(r"\{IMG:([^}]+)\}", replace_placeholder, content)


# Video definitions for pages that have embedded videos
# Format: {VIDEO:key} in content, where key maps to this dict
FEATURE_VIDEOS = {
    "picture-in-picture-video": {
        "url": "https://youtu.be/F-nFQryDB0s",
        # Use "Watch the video" to match ui-watch-the-video FTL string for translations
        "alt": "Watch the video",
        "poster_image_key": "picture-in-picture-video-poster",
    },
}


def build_content_blocks(content: str, image_ids: dict[str, int]) -> list[dict]:
    """
    Build StreamField content blocks from content string with placeholders.

    Handles both {IMG:key} placeholders (converted to embed tags in text blocks)
    and {VIDEO:key} placeholders (converted to separate video blocks).

    Args:
        content: HTML content with {IMG:key} and {VIDEO:key} placeholders
        image_ids: Dict mapping image keys to their database IDs

    Returns:
        List of StreamField block dicts (text and video blocks)
    """
    blocks = []

    # Split content on video placeholders.
    # When re.split() has a capturing group, the captured text is included in the result,
    # so the list alternates: [text, captured_key, text, captured_key, ...]
    # Even indices (0, 2, 4...) = text content, odd indices (1, 3, 5...) = video keys
    video_pattern = r"\{VIDEO:([^}]+)\}"
    parts = re.split(video_pattern, content)

    for i, part in enumerate(parts):
        if i % 2 == 0:
            # This is text content
            text = part.strip()
            if text:
                # Replace image placeholders in the text
                text_with_images = replace_image_placeholders(text, image_ids)
                blocks.append({"type": "text", "value": text_with_images})
        else:
            # This is a video key
            video_key = part
            if video_key not in FEATURE_VIDEOS:
                raise ValueError(f"Unknown video key in placeholder: {video_key}")

            video_info = FEATURE_VIDEOS[video_key]
            poster_key = video_info["poster_image_key"]
            if poster_key not in image_ids:
                raise ValueError(f"Poster image not imported for video: {video_key}")

            blocks.append(
                {
                    "type": "video",
                    "value": {
                        "video_url": video_info["url"],
                        "alt": video_info["alt"],
                        "poster": image_ids[poster_key],
                    },
                }
            )

    return blocks


# =============================================================================
# Index Page Fixture
# =============================================================================


def get_features_index_page(publish: bool = True) -> ArticleIndexPage:
    """
    Get or create the ArticleIndexPage at /features/.

    This page serves as the parent for all feature ArticleDetailPages
    and displays them in a card layout.

    Content matches FTL strings from index-2023.ftl:
    - features-index-firefox-browser-features: "Firefox browser features"
    - features-index-firefox-is-the-fast-lightweight: "Firefox is the fast,
      lightweight, privacy-focused browser that works across all your devices."
    """
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    source_locale = Locale.objects.get(language_code="en-US")

    # Filter by locale to avoid finding pages in other locales
    index_page = ArticleIndexPage.objects.filter(
        slug="features",
        locale=source_locale,
        # Get the ArticleIndexPage that is a direct child of the root page
        path__startswith=root_page.path,
        depth=root_page.depth + 1,
    ).first()
    if not index_page:
        index_page = ArticleIndexPage(
            slug="features",
            locale=source_locale,
            # From: features-index-firefox-browser-features
            title="Firefox browser features",
            # From: features-index-firefox-is-the-fast-lightweight
            sub_title="Firefox is the fast, lightweight, privacy-focused browser that works across all your devices.",
            other_articles_heading="Do more with Firefox",
            other_articles_subheading="",
        )
        root_page.add_child(instance=index_page)

    if publish:
        index_page.save_revision().publish()
    else:
        index_page.live = False
        index_page.has_unpublished_changes = True
        index_page.save_revision()
        index_page.save()
    return index_page


# =============================================================================
# Feature Page Content
# =============================================================================
#
# IMPORTANT: The content below MUST match the FTL source strings exactly
# (after brand term expansion) for translation import to work correctly.
#
# Each entry includes:
#   - ftl_file: The source FTL file for reference
#   - title: Page title (from FTL page title string)
#   - description: Page description (from FTL HTML description)
#   - content: Rich text content matching FTL strings exactly
#   - featured: Whether to show prominently on index page
# =============================================================================

FEATURE_PAGES = {
    "fast": {
        "ftl_file": "fast-2024.ftl",
        "title": "Firefox keeps getting faster",
        "description": "<p>The latest browser speed benchmarks prove Firefox is faster than ever.</p>",
        "index_page_heading": "",
        "featured": True,
        "featured_image": "fast",  # This value is the key from the FEATURE_IMAGES dictionary.
        "content": """
<h2>How is browser speed measured?</h2>
<p>The most widely used browser performance benchmark to measure web application responsiveness is called Speedometer. While other browser benchmarks exist, Speedometer 3 is the new standard for how we measure the speed of your browsing experience. The latest tests better reflect the web of today — working with visually rich charts, editing text, interacting with complicated and heavy web pages like news sites — and it measures a full picture of the browser's performance.</p>
<p>The new Speedometer 3 benchmark is the first major browser benchmark that's ever been developed through a collaboration supported by every major browser, designed to benefit the entire web.</p>

<h2>Faster every day</h2>
<p>Firefox is powered by the world-class Gecko engine, with shockingly fast styling and page layout, modern JavaScript features and a never-ending drumbeat of new performance improvements to keep our users happy and push the web platform forward.</p>
<p>All browsers had to make improvements in order to perform well on the new Speedometer 3 tests. Firefox in particular made huge strides, <a href="https://hacks.mozilla.org/2023/10/down-and-to-the-right-firefox-got-faster-for-real-users-in-2023/">getting noticeably faster</a> for our users as a direct result of this work. Firefox is faster than ever before, with speed you can really feel, including faster page loads and smoother interactions.</p>

<h2>Towards a faster web</h2>
<p>Mozilla is <a href="https://www.mozilla.org/about/webvision/full/#performance">committed</a> to continuously improving our own browser as well as the entire web. That's why we invested in the collaboration to develop Speedometer 3 which, in turn, has improved the performance of all browsers. So whatever browser you choose, Mozilla wants it to be fast.</p>
""",
    },
    "block-fingerprinting": {
        "ftl_file": "fingerprinting.ftl",
        "title": "Firefox blocks fingerprinting",
        "description": "<p>Ditch the sticky ads following you around with Firefox's built-in fingerprinting blockers.</p>",
        "index_page_heading": "Fingerprint blocking",
        "featured": False,
        "content": """
<h2>What is fingerprinting?</h2>
<p>Fingerprinting is a type of online tracking that's more invasive than ordinary cookie-based tracking. A digital fingerprint is created when a company makes a unique profile of you based on your computer hardware, software, add-ons, and even preferences. Your settings like the screen you use, the fonts installed on your computer, and even your choice of a web browser can all be used to create a fingerprint.</p>
<p>If you have a commonly used laptop, PC or smartphone, it may be harder to uniquely identify your device through fingerprinting. However, the more unique add-ons, fonts, and settings you have, the easier you'll be likely to find. Companies can use this unique combination of information to create your fingerprint. That's why Firefox blocks known fingerprinting, so you can still use your favorite extensions, themes and customization without being followed by ads.</p>

<h2>Fingerprinting is bad for the web</h2>
<p>The practice of fingerprinting allows you to be <a href="https://blog.mozilla.org/en/products/firefox/firefox-now-protects-you-from-supercookies/">tracked for months</a>, even when you clear your browser storage or use private browsing mode — disregarding clear indications from you that you don't want to be tracked. Despite a near complete agreement between <a href="https://www.w3.org/2001/tag/doc/unsanctioned-tracking/">standards</a> <a href="https://w3c.github.io/fingerprinting-guidance/#introduction">bodies</a> and <a href="https://webkit.org/tracking-prevention/">browser</a> <a href="https://www.chromium.org/Home/chromium-privacy/privacy-sandbox/">vendors</a> that fingerprinting is <a href="https://blog.mozilla.org/netpolicy/2023/07/31/eu-dma-joint-statement/">harmful</a>, its use on the web <a href="https://petsymposium.org/2016/files/papers/OpenWPM_1_million_site_tracking_measurement.pdf">has</a> <a href="https://webtransparency.cs.princeton.edu/webcensus/">steadily</a> <a href="https://www.securitee.org/files/pspray_dimva2019.pdf">increased</a> over the past decade.</p>
<p>The latest Firefox browser protects you against fingerprinting by blocking third-party requests to companies that are known to participate in fingerprinting. We've worked hard to enable this privacy protection while not breaking the websites you enjoy visiting. (Read more here, if you want the <a href="https://blog.mozilla.org/en/products/firefox/firefox-blocks-fingerprinting/">technical details</a>.)</p>
<p>And it's not a deep setting you need to dig around to find. In the latest Firefox browser, fingerprint blocking is the standard, default setting. Visit your <a href="about:protections">privacy protections dashboard</a> to see how you're being tracked behind the scenes and how Firefox prevents it.</p>
<p>You probably wouldn't appreciate someone tracking your moves in real life. There's no reason to accept it online. If you don't already have Firefox, <a href="https://www.mozilla.org/firefox/new/">download and protect yourself</a> from digital fingerprinting.</p>
""",
    },
    "private": {
        "ftl_file": "private-2023.ftl",
        "title": "Is Firefox a private browser?",
        "description": "<p>We're focused on your right to privacy. Your data, your web activity, your life online is protected with Firefox.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>Yes. Firefox protects your privacy with features like <a href="/firefox/features/private-browsing/">Private Browsing</a>. It allows you to keep your browsing history and passwords private, even when using a device that you share with other people, such as a home computer or iPad.</p>
<p>Firefox also protects your privacy with <a href="https://support.mozilla.org/kb/enhanced-tracking-protection-firefox-desktop">Enhanced Tracking Protection</a> to block trackers that follow you from site to site, collecting information about your browsing habits. It also includes protections against harmful scripts and malware.</p>
<p><em>Sidenote:</em> We are not big tech. We do things differently. Being independent (no shareholders) allows us to put people first, before profit. Unlike other companies, we don't sell access to your data.</p>

<h2>What information does Firefox collect?</h2>
<p>Mozilla (the maker of Firefox) takes privacy very seriously. <strong>Very seriously</strong>. In fact, every Firefox product we make honors our <a href="https://www.mozilla.org/privacy/principles/">Personal Data Promise</a>: Take less. Keep it safe. No secrets.</p>
<p>Read <a href="https://www.mozilla.org/privacy/firefox/">Firefox's Privacy Notice</a> for more info. Seriously, check it out. It's in normal-sized font and everything.</p>
""",
    },
    "add-ons": {
        "ftl_file": "add-ons-2023.ftl",
        "title": "Firefox add-ons and browser extensions",
        "description": "<p>Add new tools, capabilities and fun stuff to your browser.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>Extensions – also known as Firefox Add-ons – are extra features you can download and install to add more functionality and tools to your browser. Add-ons allow you to customize your Firefox browser and enhance the way you use the web.</p>
{IMG:addons}
<p>There are Firefox add-ons that <a href="https://addons.mozilla.org/firefox/addon/facebook-container/">stop Facebook from tracking you around the web</a>, <a href="https://addons.mozilla.org/firefox/addon/firefox-translations/">translate text into other languages</a>, <a href="https://addons.mozilla.org/firefox/addon/languagetool/">check your spelling or grammar</a>, or <a href="https://addons.mozilla.org/firefox/themes/">spruce up the way your browser looks</a>. You'll find these and thousands of other free extensions at <a href="https://addons.mozilla.org/firefox/">addons.mozilla.org</a>.</p>
""",
    },
    "customize": {
        "ftl_file": "customize-2023.ftl",
        "title": "Customize your Firefox browser",
        "description": "<p>Choose how your browser looks with thousands of free themes.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>Firefox themes let you change your browser's appearance. They set the color scheme for browser menus and Firefox system pages, and can even add a background image to your Firefox toolbar.</p>
<p>Firefox comes with a default system theme and is preloaded with light, dark and colorful variations.</p>
{IMG:default-themes}
<p>You can find more free custom themes at <a href="https://addons.mozilla.org/firefox/themes/">addons.mozilla.org</a>. Browse the <a href="https://addons.mozilla.org/firefox/themes/?sort=rating">top-rated</a>, <a href="https://addons.mozilla.org/firefox/themes/?sort=hotness">trending</a> and <a href="https://addons.mozilla.org/firefox/themes/?sort=recommended">most recommended</a> themes. Or look for themes by category, including <a href="https://addons.mozilla.org/firefox/themes/music/">music</a>, <a href="https://addons.mozilla.org/firefox/themes/seasonal/">seasonal</a>, <a href="https://addons.mozilla.org/firefox/themes/sports/">sports</a>, and <a href="https://addons.mozilla.org/firefox/themes/nature/">nature</a>. Tailor your experience to your tastes. Cute critters, evil robots, beautiful landscapes — there are thousands of options to make Firefox your own.</p>
{IMG:custom-themes}
""",
    },
    "private-browsing": {
        "ftl_file": "private-browsing-2023.ftl",
        "title": "Firefox private browsing mode",
        "description": "<p>Automatically delete cookies and erase your browser history when you close it.</p>",
        "index_page_heading": "Private browsing mode",
        "featured": False,
        "content": """
<p>If you share a computer with other people or if you want to limit how much data websites can collect about you, you can use private browsing mode in Firefox. Private browsing erases the digital tracks you leave behind when you browse online — think of them like footprints through the woods.</p>

<h2>What does private browsing do?</h2>
<p>Private browsing mode opens a new browser window. When you close the last private browsing window, your browsing history and any tracking cookies from websites you visited will be erased. <strong>Firefox Pro Tip:</strong> Don't forget to close all your private browsing windows when you're done!</p>
{IMG:private-browsing}

<h2>What private browsing doesn't do</h2>
<p>Private browsing mode will not delete any new bookmarks you make from a private browsing window, or protect you from malware or viruses. It also doesn't prevent the websites you visit from seeing where you are physically located or stop your internet service provider from logging what you do. You'll need a <a href="https://www.mozilla.org/products/vpn/">trustworthy VPN</a> for that.</p>
<p>Compare Firefox's private browsing with <a href="/firefox/browsers/compare/chrome/">Chrome's incognito mode</a>.</p>
""",
    },
    "bookmarks": {
        "ftl_file": "bookmarks-2023.ftl",
        "title": "Bookmark manager",
        "description": "<p>Organize your bookmarks with folders and tags.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>Bookmarks are links you save in your browser so you can quickly and easily get back to your favorite places on the web. Firefox includes a handy bookmark manager so you can organize, search, update and <a href="/firefox/features/sync/">synchronize all your saved links across all your devices</a>.</p>

<h2>Organize your bookmarks into searchable folders</h2>
<p>Collect your bookmarks in folders and tag them with more details. You can also sort your bookmarks to quickly find the ones you need.</p>
{IMG:bookmark-manager}

<h2>Easily import bookmarks</h2>
<p>You can import your bookmarks from Chrome, Safari or Edge with Firefox's import wizard. Just click Bookmarks > Manage Bookmarks and then select "Import and Backup".</p>
{IMG:import-wizard}

<h2>Bookmarks toolbar</h2>
<p>Get quick access to your favorite bookmarks in the menu at the top of Firefox or pin them to your toolbar.</p>
{IMG:bookmark-toolbar}
""",
    },
    "sync": {
        "ftl_file": "sync-2023.ftl",
        "title": "Firefox browser sync",
        "description": "<p>Access your Firefox bookmarks, passwords, open tabs and more from any device.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>With Firefox, you can pick up where you left off when you switch from your desktop computer to your mobile phone to your tablet. Firefox lets you see your bookmarks, your browsing history, your saved passwords and more, no matter which device you're using.</p>
<p><a href="/firefox/accounts/">Sign up for a free Mozilla account</a> and you'll be able to sync your data everywhere you use Firefox and other Mozilla products.</p>
<p>All your data is encrypted on our servers so we can't read it – only you can access it. We don't sell your info to advertisers because that would go against our <a href="https://www.mozilla.org/privacy/firefox/">data privacy promise</a>.</p>
{IMG:sync}

<h2>Send tabs from one device to another</h2>
<p>The Send Tab feature in Firefox lets you send pages from Firefox on one device to other devices (such as an iPhone, iPad or Android device). Did you find an article while browsing on your phone that you want to read when you get back to your desk? Or an important document from work that you want to save when you get home? Maybe you found a recipe on your laptop that you want to send to your tablet in the kitchen. Send that tab!</p>
{IMG:send-tab}
""",
    },
    "password-manager": {
        "ftl_file": "password-manager-2023.ftl",
        "title": "Free password manager",
        "description": "<p>Get help creating new passwords, auto-fill online forms and log in automatically.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>Firefox securely stores your usernames and passwords for accessing websites, automatically fills them in for you the next time you visit a website, and lets you manage your stored logins with its built-in password management feature.</p>
<p>With a <a href="/firefox/accounts/">free Mozilla account</a> you can securely sync your passwords across all your devices. You can also access all of Mozilla's other privacy-respecting products.</p>

<h2>Password autofill for easy logins</h2>
<p>Firefox can automatically fill in your saved username and password. If you have more than one login for a site, you can just select the account you want and we'll take it from there.</p>
{IMG:password-autofill}

<h2>Import passwords</h2>
<p>You can use the import wizard to easily (magically) import usernames and passwords stored on Chrome, Edge, Safari or any other browsers. Select Passwords from the menu, and then click "import them into Firefox" at the bottom of the Logins & Passwords page.</p>
{IMG:import-wizard}

<h2>No more reusing your passwords</h2>
<p>Have Firefox <a href="https://support.mozilla.org/kb/how-generate-secure-password-firefox">create a strong, unique password</a> for each login you have across the web — that way, if one of your passwords gets hacked through a security breach, it'll only impact that one account, not other accounts too.</p>
{IMG:password-suggest}

<h2>Password security alerts</h2>
<p>Firefox <a href="https://support.mozilla.org/kb/firefox-password-manager-alerts-breached-websites">alerts you if a password has been exposed</a> in a data breach so you can change it before hackers have a chance to do something like rent a Lambo with your credit card.</p>
{IMG:password-breach-alert}
""",
    },
    "picture-in-picture": {
        "ftl_file": "picture-in-picture.ftl",
        "title": "Get more done with pop-out videos",
        "description": "<p>Got things to do and things to watch? Do both using Picture-in-Picture in Firefox.</p>",
        "index_page_heading": "Picture-in-Picture",
        "featured": False,
        "content": """
<p>Got things to do and things to watch? Do both using Picture-in-Picture in Firefox. It lets you pop a video out of its webpage and pin it to your screen so you can keep watching while you're on other pages, tabs and apps.</p>
{VIDEO:picture-in-picture-video}

<h2>Here's how it works:</h2>
<ol>
<li><strong>Play any video</strong> in your Firefox browser, like this one.</li>
<li><strong>Click the Picture-in-Picture button</strong> that appears over the video, and it'll pop out.</li>
<li><strong>Cruise around to other tabs</strong> or even outside of Firefox. The video stays put!</li>
<li><strong>Repeat steps 1-3</strong> to have as many picture-in-picture videos as you'd like.</li>
</ol>

<h2>3 ways to use Picture-in-Picture</h2>
{IMG:pip-lecture}Watch a lecture or meeting while you take notes
{IMG:pip-cook}Keep a tutorial video open with a recipe while you cook
{IMG:pip-entertain}Entertain cats, dogs and kids while you get work done
""",
    },
    "translate": {
        "ftl_file": "translate.ftl",
        "title": "Translate a webpage with Firefox",
        "description": "<p>Translate websites to your language directly in your Firefox browser – without sharing your data with anyone else.</p>",
        "index_page_heading": "Translate the web",
        "featured": False,
        "content": """
<p>One of the best things about the internet is that we can access content worldwide. Whether it's news articles, blogs, or even a review of your latest tech gadget, you can find it all on the seemingly never-ending web. With Firefox's latest translation feature, this tool will continuously translate a webpage in real-time.</p>
<p>While other browsers rely on cloud services, the Firefox Translations language models are downloaded on the user's browser and translations are done locally, so Mozilla doesn't record what webpages you translate.</p>

<h2>When you translate a webpage, it stays private</h2>
<p>When your translations are processed locally, no data from your chosen device leaves your device or relies on cloud services for translation. This means that Mozilla doesn't know what web page you translate, and makes our translation feature stand out in comparison to other translation tools.</p>

<h2>What languages are currently supported?</h2>
<p>The languages below are currently supported by the Firefox Translations feature:</p>
<p>And more languages are in development!</p>

<h2>Firefox speaks your language</h2>
<p>The Firefox Translations feature is another way Mozilla keeps your internet personalized and more private. Mozilla doesn't track what webpages you translate. With millions of users worldwide, Mozilla wants to ensure that those who use Firefox are learning, communicating, sharing, and staying informed on their own terms. <a href="https://www.mozilla.org/firefox/new/">Get started in your preferred language by downloading Firefox.</a></p>
""",
    },
    "adblocker": {
        "ftl_file": "adblocker-2025.ftl",
        "title": "The ad blocker – a tool for a personalized & focused browsing experience.",
        "description": "<p>Firefox automatically blocks 2000+ ad trackers from following you around the internet.</p>",
        "index_page_heading": "Ad tracker blocking",
        "featured": False,
        "content": """
<p>In today's digital world, the web can be busy and cluttered. Ad blockers are powerful tools that put you in control of your browsing experience, letting you decide what appears on your screen.</p>
<p>Ad blockers work in two key ways: by preventing content, such as ads, from loading and by blocking sections of websites that host those elements. This can include video ads, personalized ads that follow you across the web, and even third-party trackers.</p>
<p>Using an ad blocker is straightforward. Many trusted options are available as browser add-ons, making it easy to find a solution that works for your needs. For instance, <a href="https://www.mozilla.org/firefox/new/">Firefox</a> offers <a href="https://addons.mozilla.org/firefox/extensions/category/privacy-security/">a list of approved extensions</a> designed to improve your browsing experience while respecting your privacy.</p>

<h2>Finding the Right Ad Blocker for You</h2>
<p>There are many ad-blocking tools to explore, each offering features to suit different preferences. Finding the right one for you depends on your desires and browsing habits. Here are a few tips to consider:</p>
<ul>
<li><strong>Blocking Ads:</strong> If you only want to block ads, choose a simple and lightweight option.</li>
<li><strong>Privacy Concerns:</strong> If you're worried about trackers, look for an ad blocker with built-in privacy features.</li>
<li><strong>Customizability:</strong> Some ad blockers allow fine-tuning to whitelist specific sites or block specific elements.</li>
<li><strong>Device Compatibility:</strong> Consider whether you need it for desktop, mobile, or both.</li>
<li><strong>Malware Blocking:</strong> Some ad blockers protect against malicious ads (e.g., AdGuard).</li>
<li><strong>Parental Controls:</strong> Useful if you want to block inappropriate content.</li>
</ul>
<p>It's important to note that some websites rely on ads to load content or provide functionality. Blocking ads may cause features to break, such as videos not playing or login options failing. Choose an ad blocker that is updated regularly and if you find one ad blocker causes significant issues, try another to find a better balance of performance and compatibility.</p>

<h2>Enhanced Privacy and Performance with Firefox</h2>
<p>Beyond ad blockers, Firefox includes built-in features to give you even greater control over your browsing. These tools help protect your privacy while allowing you to customize your experience:</p>
<ul>
<li><strong>Standard Mode:</strong> A balanced option that blocks common trackers while maintaining smooth website functionality.</li>
<li><strong>Strict Mode:</strong> Ideal for users who want stronger privacy protection by blocking more trackers and cookies. Note that some sites may require adjustments in this mode.</li>
<li><strong>Custom Mode:</strong> For those who want full control, Custom mode lets you select what to block, from cookies to trackers and more.</li>
</ul>
<p>To adjust these settings, click the shield icon to the left of the address bar on any webpage and select "Protection Settings." This will open a menu where you can choose the right level of protection for you.</p>
{IMG:content-blocking}
{IMG:content-blocking-custom}

<h2>Why Use an Ad Blocker?</h2>
<p>Ad blockers do more than manage ads – they can enhance your browsing speed and security by reducing unnecessary content. They empower you to create a tailored, distraction-free web experience, letting you focus on what matters most.</p>
<p>Explore hundreds of privacy-focused add-ons available for Firefox and find the right tools for you. <a href="https://www.mozilla.org/firefox/new/">Download Firefox</a> today to experience a browser designed with your privacy and performance in mind.</p>
""",
    },
    "pdf-editor": {
        "ftl_file": "pdf-editor-2023.ftl",
        "title": "Edit PDFs for free with Firefox PDF Editor",
        "description": "<p>View and edit PDF files right in Firefox.</p>",
        "index_page_heading": "PDF editor",
        "featured": False,
        "content": """
<p>If you need to add stuff to a PDF document, now you can do that online with Firefox. Open the PDF in Firefox and click the Text or Draw buttons in the upper right corner to make changes to your document. Download the file to save it with your changes.</p>

<h2>Fill in forms online without printing and scanning</h2>
<p>We've all faced this: you need to fill in a form that is a PDF, but it isn't editable. In the past, your only option was to print it on a dead tree, add things with ink, and then scan it back into your computer.</p>
<p>No more! Now, all you need to do is edit the PDF online with Firefox, save it, and email it from your computer.</p>

<h2>Add text</h2>
<p>Open the PDF in Firefox. Click the Text button to choose a color and text size before selecting where on the document you wish to add text. It's that easy!</p>
{IMG:edit-pdf-text}

<h2>Add drawings</h2>
<p>Open the PDF in Firefox. Click the Draw icon to choose a color, thickness and opacity before then being able to draw on the document.</p>
{IMG:edit-pdf-draw}

<h2>Add image with alt text</h2>
<p>Open the PDF in Firefox. Click the image icon, which will then prompt you to upload an image. Adjust size and placement of your image as needed. Click the "+Alt text" button on the image to add a photo description to make your PDF more accessible.</p>
{IMG:edit-pdf-alt-text}

<h2>Create a signature</h2>
<p>Open the PDF in Firefox. Click the signature icon and then click "Add new signature". Choose between Type, Draw or Image, and click the Add button to insert. You can also save your signatures and use them again later.</p>
{IMG:edit-pdf-signature}

<h2>Create a highlight</h2>
<p>Open the PDF in Firefox. Select the text you want to highlight, then click the highlight icon that appears below your selection, or right click to find the highlight option in the context menu. Click the icon in the top right to freehand highlight sections of the PDF.</p>
{IMG:edit-pdf-highlight}

<h2>Add comments</h2>
<p>Open the PDF in Firefox. Create a highlight, then click the Comment icon that appears below your selection, type your comment, and click Add to save. Lots of comments in a PDF? Click the Comment icon in the top right to open the sidebar and jump to the one you need.</p>
{IMG:edit-pdf-comment}
""",
    },
    "eyedropper": {
        "ftl_file": "eyedropper-2023.ftl",
        "title": "Select colors in Firefox with the eyedropper tool",
        "description": "<p>Identify the exact color on a page and copy its hex code.</p>",
        "index_page_heading": "Eyedropper tool",
        "featured": False,
        "content": """
<p>There are a lot of reasons you might want to know the exact hex color code of a specific color on a web page — maybe you build webpages or are a graphic designer. The eyedropper tool, in the desktop version of Firefox, lets you find exact hex color codes just by hovering over any color you see on a web page. A click will copy that color value to your clipboard.</p>
{IMG:eyedropper}
<p>You can find the eyedropper under "Browser Tools" in the Tools menu or under "More Tools" in the Firefox toolbar menu (at the end of the Firefox toolbar).</p>
""",
    },
    "pinned-tabs": {
        "ftl_file": "pinned-tabs-2023.ftl",
        "title": "Pinned browser tabs",
        "description": "<p>Keep your favorite pages open and just a click away. Use Pinned Tabs to keep an eye on your email or messaging apps.</p>",
        "index_page_heading": "",
        "featured": False,
        "content": """
<p>Pinning a tab in Firefox allows you to keep your favorite sites always open and a click away. They'll open automatically when you start Firefox. We've found them especially useful for keeping things like email and calendar websites always at hand.</p>
{IMG:pinned-tabs}
<p>They're small, and you can't close them accidentally because they don't have a close button. Instead, you have to unpin them.</p>
<p>You can see when your pinned tabs are updated, for example, if you get a new email or direct message.</p>
{IMG:pinned-tab-notification}
<p>If you click on a link from within your pinned tab, Firefox will automatically open the link in a separate, new tab so your pinned tab lives on forever (or until you unpin it).</p>
""",
    },
}


# =============================================================================
# Feature Page Fixtures
# =============================================================================


def get_feature_page(slug: str, image_ids: dict[str, int], publish: bool = True) -> ArticleDetailPage:
    """
    Get or create an ArticleDetailPage for a feature.

    Args:
        slug: The page slug (must match a key in FEATURE_PAGES)
        image_ids: Dict mapping image keys to their database IDs

    Returns:
        The ArticleDetailPage instance
    """
    if slug not in FEATURE_PAGES:
        raise ValueError(f"Unknown feature page slug: {slug}")

    page_data = FEATURE_PAGES[slug]
    index_page = get_features_index_page(publish=publish)

    # Filter by parent to avoid finding pages in other locales/parents
    page = ArticleDetailPage.objects.child_of(index_page).filter(slug=slug).first()
    if not page:
        page = ArticleDetailPage(
            slug=slug,
            title=page_data["title"],
        )
        index_page.add_child(instance=page)

    # Update page content
    page.title = page_data["title"]
    page.description = page_data["description"]
    page.featured = page_data.get("featured", False)
    # Use "Learn more" because it has existing translations via ui-learn-more in the l10n repo
    page.link_text = "Learn more"
    page.index_page_heading = page_data.get("index_page_heading", "")

    # Set featured image if specified
    featured_image_key = page_data.get("featured_image")
    if featured_image_key and featured_image_key in image_ids:
        page.featured_image_id = image_ids[featured_image_key]

    # Build content blocks (handles both image and video placeholders)
    # Before building new blocks, extract existing UUIDs by position so that
    # wagtail-localize segment context paths (which embed block UUIDs) remain
    # stable across fixture re-runs, preserving existing translations.
    existing_uuids = []
    if page.content:
        for block in page.content.raw_data:
            existing_uuids.append(block.get("id"))

    new_blocks = build_content_blocks(page_data["content"], image_ids)

    # Carry forward existing UUIDs where blocks match by position
    for i, block in enumerate(new_blocks):
        if i < len(existing_uuids) and existing_uuids[i]:
            block["id"] = existing_uuids[i]

    page.content = new_blocks

    if publish:
        page.save_revision().publish()
    else:
        page.live = False
        page.has_unpublished_changes = True
        page.save_revision()
        page.save()
    return page


def get_all_feature_pages(image_ids: dict[str, int], publish: bool = True) -> list[ArticleDetailPage]:
    """
    Get or create all feature pages.

    Args:
        image_ids: Dict mapping image keys to their database IDs

    Returns:
        List of ArticleDetailPage instances
    """
    pages = []
    for slug in FEATURE_PAGES:
        page = get_feature_page(slug, image_ids, publish=publish)
        pages.append(page)
    return pages


# =============================================================================
# Main Entry Point
# =============================================================================


def load_feature_page_fixtures(publish: bool = True):
    """
    Load all feature page fixtures.

    This is the main entry point called by the management command.

    Args:
        publish: If True (default), pages are published and live.
                 If False, pages are saved as drafts.
    """
    # Import images first
    print("Importing feature images...")
    image_ids = import_feature_images()
    print(f"  Imported {len(image_ids)} images")

    # Create index page
    index_page = get_features_index_page(publish=publish)
    print(f"Created/updated ArticleIndexPage: {index_page.url}")

    # Create all feature pages with images
    pages = get_all_feature_pages(image_ids, publish=publish)
    for page in pages:
        print(f"Created/updated ArticleDetailPage: {page.url}")

    return index_page, pages
