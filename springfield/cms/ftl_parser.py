# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utilities for parsing FTL (Fluent) files and extracting translations.

This module provides functions to:
- Parse FTL files and extract message text
- Expand brand term references to their actual values
- Match English source strings to their translations
- Normalize text for fuzzy matching between FTL and Wagtail content
"""

import re
from pathlib import Path

from django.conf import settings

import polib
from fluent.syntax import parse
from fluent.syntax.ast import Message, Placeable, TextElement
from wagtail_localize.models import StringSegment

# Brand terms to expand in FTL strings.
# These match the terms defined in l10n/en/brands.ftl
BRAND_TERMS = {
    # Company names
    "-brand-name-apple": "Apple",
    "-brand-name-creative-commons": "Creative Commons",
    "-brand-name-facebook": "Facebook",
    "-brand-name-google": "Google",
    "-brand-name-microsoft": "Microsoft",
    "-brand-name-mozilla": "Mozilla",
    "-brand-name-mozilla-corporation": "Mozilla Corporation",
    "-brand-name-mozilla-foundation": "Mozilla Foundation",
    "-brand-name-netscape": "Netscape",
    "-brand-name-linkedin": "LinkedIn",
    "-brand-name-spotify": "Spotify",
    # Firefox browsers
    "-brand-name-firefox": "Firefox",
    "-brand-name-firefox-beta": "Firefox Beta",
    "-brand-name-firefox-browser": "Firefox Browser",
    "-brand-name-firefox-browsers": "Firefox Browsers",
    "-brand-name-firefox-developer-edition": "Firefox Developer Edition",
    "-brand-name-firefox-enterprise": "Firefox Enterprise",
    "-brand-name-firefox-esr": "Firefox ESR",
    "-brand-name-firefox-extended-support-release": "Firefox Extended Support Release",
    "-brand-name-firefox-focus": "Firefox Focus",
    "-brand-name-firefox-nightly": "Firefox Nightly",
    # Firefox browsers (short names)
    "-brand-name-beta": "Beta",
    "-brand-name-developer-edition": "Developer Edition",
    "-brand-name-enterprise": "Enterprise",
    "-brand-name-esr": "ESR",
    "-brand-name-focus": "Focus",
    "-brand-name-nightly": "Nightly",
    # Firefox browsers (legacy)
    "-brand-name-firefox-aurora": "Firefox Aurora",
    # Firefox products
    "-brand-name-facebook-container": "Facebook Container",
    "-brand-name-firefox-devtools": "Firefox DevTools",
    "-brand-name-firefox-relay": "Firefox Relay",
    "-brand-name-firefox-translations": "Firefox Translations",
    # Firefox products (short names)
    "-brand-name-relay": "Relay",
    # Firefox projects
    "-brand-name-firefox-labs": "Firefox Labs",
    # Pocket
    "-brand-name-pocket": "Pocket",
    # Fakespot
    "-brand-name-fakespot": "Fakespot",
    # Mozilla projects
    "-brand-name-bugzilla": "Bugzilla",
    "-brand-name-gecko": "Gecko",
    "-brand-name-mdn-plus": "MDN Plus",
    "-brand-name-mdn-web-docs": "MDN Web Docs",
    "-brand-name-mozilla-monitor": "Mozilla Monitor",
    "-brand-name-mozilla-vpn": "Mozilla VPN",
    "-brand-name-mozilla-account": "Mozilla account",
    "-brand-name-mozilla-accounts": "Mozilla accounts",
    "-brand-name-mozilla-ai-v2": "Mozilla.ai",
    "-brand-name-mozilla-ventures": "Mozilla Ventures",
    "-brand-name-thunderbird": "Thunderbird",
    # Mozilla projects (short names)
    "-brand-name-common-voice": "Common Voice",
    "-brand-name-mdn": "MDN",
    "-brand-name-monitor": "Monitor",
    # Other browsers
    "-brand-name-brave": "Brave",
    "-brand-name-chrome": "Chrome",
    "-brand-name-edge": "Edge",
    "-brand-name-ie": "Internet Explorer",
    "-brand-name-opera": "Opera",
    "-brand-name-safari": "Safari",
    # Platforms
    "-brand-name-android": "Android",
    "-brand-name-chromeos": "Chrome OS",
    "-brand-name-ios": "iOS",
    "-brand-name-linux": "Linux",
    "-brand-name-mac": "macOS",
    "-brand-name-mac-short": "Mac",
    "-brand-name-macos": "macOS",
    "-brand-name-windows": "Windows",
    # Apple products
    "-brand-name-app-store": "App Store",
    "-brand-name-ipad": "iPad",
    "-brand-name-iphone": "iPhone",
    "-brand-name-test-flight": "TestFlight",
    # Facebook products
    "-brand-name-instagram": "Instagram",
    # Google products
    "-brand-name-chromebook": "Chromebook",
    "-brand-name-chromium": "Chromium",
    "-brand-name-google-play": "Google Play",
    "-brand-name-youtube": "YouTube",
    # Enterprise
    "-brand-name-support-for-organizations": "Support for Organizations",
}


def expand_brand_terms(text: str) -> str:
    """
    Replace FTL brand term references with actual brand names.

    Args:
        text: Text containing brand term references like { -brand-name-firefox }

    Returns:
        Text with brand terms expanded to their actual values
    """
    result = text
    for term, replacement in BRAND_TERMS.items():
        # Match { -brand-name-xxx } with optional whitespace
        pattern = rf"\{{\s*{re.escape(term)}\s*\}}"
        result = re.sub(pattern, replacement, result)
    return result


def extract_text_from_pattern(pattern) -> str:
    """
    Extract plain text from an FTL pattern, handling placeholders.

    This extracts the text content from FTL patterns, converting
    variable references and term references appropriately.

    Args:
        pattern: An FTL pattern (from Message.value)

    Returns:
        The extracted text content
    """
    if pattern is None:
        return ""

    parts = []
    link_counter = [0]  # Use list to allow modification in nested function

    def get_next_link_id():
        link_counter[0] += 1
        return f"a{link_counter[0]}"

    for element in pattern.elements:
        if isinstance(element, TextElement):
            parts.append(element.value)
        elif isinstance(element, Placeable):
            expression = element.expression

            # Handle term references like { -brand-name-firefox }
            if hasattr(expression, "id") and hasattr(expression.id, "name"):
                if hasattr(expression, "arguments"):
                    # It's a term reference (starts with -)
                    term_name = f"-{expression.id.name}"
                    parts.append(f"{{ {term_name} }}")
                else:
                    # It's a variable reference like { $url }
                    var_name = expression.id.name
                    # Check if it looks like a URL/link variable
                    if any(x in var_name.lower() for x in ["url", "link", "href", "attrs"]):
                        # This is a link opening tag placeholder
                        # We'll handle this specially - for now just mark it
                        parts.append(f"{{${var_name}}}")
                    else:
                        parts.append(f"{{ ${var_name} }}")

    return "".join(parts)


def parse_ftl_file(ftl_path: Path) -> dict[str, str]:
    """
    Parse an FTL file and return a dict of message_id -> expanded text.

    Args:
        ftl_path: Path to the FTL file

    Returns:
        Dict mapping FTL message IDs to their text content (with brand terms expanded)
    """
    if not ftl_path.exists():
        return {}

    content = ftl_path.read_text(encoding="utf-8")
    resource = parse(content)

    messages = {}
    for entry in resource.body:
        if isinstance(entry, Message) and entry.value:
            text = extract_text_from_pattern(entry.value)
            # Expand brand terms to get final text
            expanded_text = expand_brand_terms(text)
            messages[entry.id.name] = expanded_text

    return messages


def get_ftl_path_for_locale(locale: str, ftl_filename: str) -> Path | None:
    """
    Get the path to an FTL file for a specific locale.

    Checks the external l10n repository first, then falls back to local.

    Args:
        locale: The locale code (e.g., "de", "fr", "es-ES")
        ftl_filename: The FTL filename (e.g., "fast-2024.ftl")

    Returns:
        Path to the FTL file, or None if not found
    """
    # Try the external l10n repository first
    external_path = settings.FLUENT_REPO_PATH / locale / "firefox" / "features" / ftl_filename
    if external_path.exists():
        return external_path

    # Fall back to local l10n directory
    local_path = settings.FLUENT_LOCAL_PATH / locale / "firefox" / "features" / ftl_filename
    if local_path.exists():
        return local_path

    return None


def get_ftl_translations(locale: str, ftl_filename: str) -> dict[str, str]:
    """
    Get translations for a specific locale from an FTL file.

    Args:
        locale: The locale code (e.g., "de", "fr", "es-ES")
        ftl_filename: The FTL filename (e.g., "fast-2024.ftl")

    Returns:
        Dict mapping FTL message IDs to translated text
    """
    ftl_path = get_ftl_path_for_locale(locale, ftl_filename)
    if ftl_path:
        return parse_ftl_file(ftl_path)
    return {}


def get_english_ftl_strings(ftl_filename: str) -> dict[str, str]:
    """
    Get English source strings from an FTL file.

    Args:
        ftl_filename: The FTL filename (e.g., "fast-2024.ftl")

    Returns:
        Dict mapping FTL message IDs to English text
    """
    # English source is in l10n/en/
    en_path = settings.FLUENT_LOCAL_PATH / "en" / "firefox" / "features" / ftl_filename
    return parse_ftl_file(en_path)


def get_ftl_path_for_locale_at_subpath(locale: str, ftl_relative_path: str) -> Path | None:
    """Like get_ftl_path_for_locale but accepts a full relative path.

    Args:
        locale: e.g. "de"
        ftl_relative_path: e.g. "firefox/browsers/compare/brave.ftl"
    """
    external_path = settings.FLUENT_REPO_PATH / locale / ftl_relative_path
    if external_path.exists():
        return external_path
    local_path = settings.FLUENT_LOCAL_PATH / locale / ftl_relative_path
    if local_path.exists():
        return local_path
    return None


def get_ftl_translations_at_subpath(locale: str, ftl_relative_path: str) -> dict[str, str]:
    """Get translations for a specific locale using a full relative FTL path."""
    ftl_path = get_ftl_path_for_locale_at_subpath(locale, ftl_relative_path)
    if ftl_path:
        return parse_ftl_file(ftl_path)
    return {}


def get_english_ftl_strings_at_subpath(ftl_relative_path: str) -> dict[str, str]:
    """Get English source strings using a full relative FTL path."""
    en_path = settings.FLUENT_LOCAL_PATH / "en" / ftl_relative_path
    return parse_ftl_file(en_path)


def get_ui_ftl_path_for_locale(locale: str) -> Path | None:
    """
    Get the path to ui.ftl for a specific locale.

    ui.ftl contains common UI strings like "Learn more" and is located
    directly in the locale directory (not under firefox/features/).

    Args:
        locale: The locale code (e.g., "de", "fr", "es-ES")

    Returns:
        Path to ui.ftl, or None if not found
    """
    # Try the external l10n repository first
    external_path = settings.FLUENT_REPO_PATH / locale / "ui.ftl"
    if external_path.exists():
        return external_path

    # Fall back to local l10n directory
    local_path = settings.FLUENT_LOCAL_PATH / locale / "ui.ftl"
    if local_path.exists():
        return local_path

    return None


def get_ui_translations(locale: str) -> dict[str, str]:
    """
    Get UI string translations for a specific locale.

    Args:
        locale: The locale code (e.g., "de", "fr", "es-ES")

    Returns:
        Dict mapping FTL message IDs to translated text
    """
    ftl_path = get_ui_ftl_path_for_locale(locale)
    if ftl_path:
        return parse_ftl_file(ftl_path)
    return {}


def get_english_ui_strings() -> dict[str, str]:
    """
    Get English UI strings from ui.ftl.

    Returns:
        Dict mapping FTL message IDs to English text
    """
    en_path = settings.FLUENT_LOCAL_PATH / "en" / "ui.ftl"
    return parse_ftl_file(en_path)


def get_shared_translations(locale: str) -> dict[str, str]:
    """
    Get shared string translations for a specific locale.

    shared.ftl contains strings shared across feature pages like
    "Do more with Firefox".

    Args:
        locale: The locale code (e.g., "de", "fr", "es-ES")

    Returns:
        Dict mapping FTL message IDs to translated text
    """
    return get_ftl_translations(locale, "shared.ftl")


def get_english_shared_strings() -> dict[str, str]:
    """
    Get English shared strings from shared.ftl.

    Returns:
        Dict mapping FTL message IDs to English text
    """
    return get_english_ftl_strings("shared.ftl")


def normalize_text_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching between FTL and Wagtail content.

    This function:
    - Decodes HTML entities (e.g., &amp; -> &, &gt; -> >)
    - Normalizes curly quotes to straight quotes
    - Strips leading/trailing whitespace
    - Normalizes internal whitespace
    - Normalizes various link formats to a common placeholder

    Args:
        text: The text to normalize

    Returns:
        Normalized text suitable for comparison
    """
    import html

    # Decode HTML entities (Wagtail segments may have &amp;, &gt;, etc.)
    text = html.unescape(text)

    # Normalize curly quotes/apostrophes to straight versions
    # This handles differences between FTL (which may use typography) and fixtures
    # Using Unicode escapes to ensure correct characters: U+2018, U+2019, U+201C, U+201D, U+2014, U+2013
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # Curly single quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # Curly double quotes
    text = text.replace("\u2014", "-").replace("\u2013", "-")  # Em/en dashes

    # Normalize whitespace (collapse multiple spaces, strip)
    text = " ".join(text.split())

    # Normalize Wagtail-style links: <a id="a1"> -> <a>
    text = re.sub(r'<a\s+id="[^"]*">', "<a>", text, flags=re.IGNORECASE)

    # Normalize FTL-style link variables: <a { $url }> -> <a>
    text = re.sub(r"<a\s*\{\s*\$[\w_]+\s*\}>", "<a>", text)

    # Also handle href-based links: <a href="..."> -> <a>
    text = re.sub(r'<a\s+href="[^"]*">', "<a>", text, flags=re.IGNORECASE)

    # Normalize any remaining link attributes
    text = re.sub(r"<a\s+[^>]*>", "<a>", text, flags=re.IGNORECASE)

    return text.strip()


def convert_ftl_links_to_wagtail(translated: str, source: str) -> str:
    """
    Convert FTL link format to Wagtail link format.

    FTL uses: <a { $url_link }>text</a> or <a href="{ $url }">text</a>
    Wagtail uses: <a id="a1">text</a>

    We need to match the link IDs from the source to preserve
    the attrs that Wagtail-Localize stores separately.

    Args:
        translated: The translated text with FTL-style links
        source: The source text with Wagtail-style links

    Returns:
        Translated text with links converted to Wagtail format
    """
    # Find all link IDs in the source text
    source_link_ids = re.findall(r'<a id="(a\d+)">', source)

    if not source_link_ids:
        return translated

    # Find all FTL-style link placeholders in translated text
    # Match patterns like: <a { $url }>, <a { $link }>, <a href="{ $url }">
    ftl_link_pattern = r'<a\s*(?:\{\s*\$[\w_]+\s*\}|href="\{\s*\$[\w_]+\s*\}")>'

    # Replace each FTL link with corresponding Wagtail link ID
    result = translated
    for link_id in source_link_ids:
        # Replace the first FTL link found with this ID
        result = re.sub(
            ftl_link_pattern,
            f'<a id="{link_id}">',
            result,
            count=1,
        )

    return result


def build_po_from_ftl(translation, en_text_to_msgid: dict[str, str], translations: dict[str, str]):
    """Build a PO file by matching Wagtail segments to FTL translations.

    Args:
        translation: A wagtail_localize Translation instance.
        en_text_to_msgid: Mapping of normalized English text to FTL message IDs
            (built with build_text_to_msgid_mapping).
        translations: Mapping of FTL message IDs to translated text for the target locale.

    Returns:
        A polib.POFile populated with matched translation entries.
    """
    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=utf-8",
        "X-WagtailLocalize-TranslationID": str(translation.uuid),
    }

    string_segments = StringSegment.objects.filter(source=translation.source).select_related("string", "context")

    for segment in string_segments:
        source_text = segment.string.data
        normalized_source = normalize_text_for_matching(source_text)

        msgid = en_text_to_msgid.get(normalized_source)

        if msgid and msgid in translations:
            translated_text = translations[msgid]
            translated_text = convert_ftl_links_to_wagtail(translated_text, source_text)

            po.append(
                polib.POEntry(
                    msgid=source_text,
                    msgctxt=segment.context.path,
                    msgstr=translated_text,
                )
            )

    return po


def build_text_to_msgid_mapping(ftl_strings: dict[str, str]) -> dict[str, str]:
    """
    Build a mapping from normalized text to FTL message ID.

    This allows looking up the FTL message ID for a given piece of text,
    which is necessary for matching Wagtail segments to FTL translations.

    Args:
        ftl_strings: Dict mapping message IDs to text (from parse_ftl_file)

    Returns:
        Dict mapping normalized text to message ID
    """
    text_to_msgid = {}
    for msgid, text in ftl_strings.items():
        normalized = normalize_text_for_matching(text)
        text_to_msgid[normalized] = msgid
    return text_to_msgid
