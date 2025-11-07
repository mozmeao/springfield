# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import re
from pathlib import Path

from django.db import migrations

from wagtail_localize.models import Translation, TranslationSource

from springfield.firefox.models import FeaturesDetailPage


def create_page_translation(translation_source, locale):
    """
    Create a translation of the page for the given locale.

    This creates both the Translation object and the actual translated page instance,
    similar to what translate_object does in wagtail_localize.operations.

    Args:
        translation_source: The TranslationSource object for the page
        locale: The target Locale object

    Returns:
        The Translation object
    """
    # Get or create the Translation object
    translation, _ = Translation.objects.get_or_create(
        source_id=translation_source.id,
        target_locale_id=locale.id,
        defaults={"enabled": True},
    )

    # Save the target to create the actual translated page
    # This creates the page instance in the target locale
    translation.save_target(user=None, publish=False)

    return translation


def fill_po_translations_from_ftl_file(po, ftl_path, variables_path, original_locale_ftl_path):
    """
    Fill in the blank strings in a po file with translations from an FTL file.

    Args:
        po: The PO file object exported from the translation
        ftl_path: Path to the translated FTL file (e.g., 'data/www-firefox-l10n/fr/firefox/features/fingerprinting.ftl')
        variables_path: Path to the variables file (brands.ftl) for the locale (e.g., 'data/www-firefox-l10n/fr/brands.ftl')
        original_locale_ftl_path: Path to the original locale (usually English) FTL file (e.g., 'l10n/en/firefox/features/fingerprinting.ftl')

    Returns:
        The modified PO file object with translations filled in
    """

    # 1. Locate the appropriate FTL file for the locale
    if not ftl_path.exists():
        # If the FTL file doesn't exist, raise an error
        raise FileNotFoundError(f"FTL file not found: {ftl_path}")

    # Read the FTL file
    with open(ftl_path, "r", encoding="utf-8") as f:
        ftl_content = f.read()

    # 2. Find all variables from the variables_path file
    variables_dict = {}
    if variables_path.exists():
        with open(variables_path, "r", encoding="utf-8") as f:
            variables_file_content = f.read()

        # Parse variables in the variables file, handling complex selectors.
        # For example, the pl variables file includes differences based on case
        # and capitalization.
        current_variable_key = None
        in_selector = False
        selector_depth = 0  # Track nesting level

        for line in variables_file_content.split("\n"):
            line_stripped = line.strip()

            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith("#"):
                continue

            # Check if this is a new brand variable definition
            if line_stripped.startswith("-brand-name-") and "=" in line_stripped:
                # Reset state for new brand
                in_selector = False
                selector_depth = 0

                key, value = line_stripped.split("=", 1)
                current_variable_key = key.strip()
                value = value.strip()

                # Check if this is a selector (contains { $case or { $capitalization)
                # OR if value is empty (selector on next line)
                if value.startswith("{ $") or value == "":
                    in_selector = True
                    selector_depth = 1
                else:
                    # Simple value
                    variables_dict[current_variable_key] = value
                    current_variable_key = None

            # If we're in a selector, look for the default value (marked with *)
            elif in_selector and current_variable_key:
                # Check if this line opens a nested selector
                if "{ $" in line_stripped:
                    selector_depth += 1

                # Check if this line closes a selector
                if "}" in line_stripped and "{ $" not in line_stripped:
                    selector_depth -= 1
                    if selector_depth == 0:
                        # We've closed all selectors without finding a simple default
                        # This shouldn't happen, but reset state
                        current_variable_key = None
                        in_selector = False

                # Look for default value marked with *
                if "*[" in line_stripped:
                    # Extract default value from lines like "*[nom] Firefox"
                    match = re.match(r"\*\[[^\]]+\]\s*(.+)", line_stripped)
                    if match:
                        default_value = match.group(1).strip()

                        # Check if this is nested (contains another selector)
                        if default_value.startswith("{ $"):
                            # Keep looking for the nested default
                            continue
                        else:
                            # Found a simple default value
                            variables_dict[current_variable_key] = default_value
                            current_variable_key = None
                            in_selector = False
                            selector_depth = 0

    # Parse FTL file to extract translations
    ftl_entries = {}
    current_key = None
    current_value = []

    for line in ftl_content.split("\n"):
        # Skip empty lines and license headers
        if (
            not line.strip()
            or line.startswith("# This Source Code")
            or line.startswith("# License")
            or line.startswith("# file,")
            or line.startswith("###")
        ):
            continue

        # Skip comment lines but not variable definitions
        if line.startswith("#") and not line.startswith("# $"):
            continue

        # Check if this is a new key-value pair (starts with a letter/number and has =)
        if "=" in line and not line.startswith(" ") and not line.startswith("#"):
            # Save previous entry if exists
            if current_key:
                ftl_entries[current_key] = " ".join(current_value).strip()

            # Parse new entry - split on first = only
            key, value = line.split("=", 1)
            current_key = key.strip()
            current_value = [value.strip()]
        elif line.startswith(" ") and current_key:
            # Continuation of previous line
            current_value.append(line.strip())

    # Save last entry
    if current_key:
        ftl_entries[current_key] = " ".join(current_value).strip()

    # 3. Replace brand variables with their appropriate values
    def replace_variables(text):
        """Replace brand name variables with actual text from variables file."""
        # Pattern to match both simple and complex brand variables
        # e.g., { -brand-name-firefox } or { -brand-name-firefox-browser(case: "nom", capitalization: "lower") }
        pattern = r"\{ (-brand-name-[\w-]+)(?:\([^)]+\))? \}"

        def replace_brand(match):
            brand_key = match.group(1)
            replacement = variables_dict.get(brand_key, match.group(0))
            return replacement

        return re.sub(pattern, replace_brand, text)

    # 4. Convert FTL links to their expected format
    def convert_links(text):
        """Convert FTL link syntax to PO format with sequential anchor IDs."""
        pattern = r"<a \{ \$\w+ \}>([^<]+)</a>"
        anchor_counter = [0]

        def replace_link(match):
            anchor_counter[0] += 1
            link_text = match.group(1)
            return f'<a id="a{anchor_counter[0]}">{link_text}</a>'

        return re.sub(pattern, replace_link, text)

    # 5. Load the English FTL file to create a mapping from English text to FTL keys
    # Parse English FTL to create msgid -> ftl_key mapping
    english_ftl_entries = {}
    if original_locale_ftl_path.exists():
        with open(original_locale_ftl_path, "r", encoding="utf-8") as f:
            english_ftl_content = f.read()

        current_key = None
        current_value = []

        for line in english_ftl_content.split("\n"):
            # Skip empty lines, comments (except variable definitions), and license headers
            if (
                not line.strip()
                or line.startswith("# This Source Code")
                or line.startswith("# License")
                or line.startswith("# file,")
                or line.startswith("###")
                or (line.startswith("#") and not line.startswith("# $"))
            ):
                continue

            # Check if this is a new key-value pair
            if "=" in line and not line.startswith(" ") and not line.startswith("#"):
                # Save previous entry if exists
                if current_key:
                    english_ftl_entries[current_key] = " ".join(current_value).strip()

                # Parse new entry
                key, value = line.split("=", 1)
                current_key = key.strip()
                current_value = [value.strip()]
            elif line.startswith(" ") and current_key:
                # Continuation of previous line
                current_value.append(line.strip())

        # Save last entry
        if current_key:
            english_ftl_entries[current_key] = " ".join(current_value).strip()

    # 6. Create a mapping from normalized English text to FTL keys
    def normalize_text(text):
        """Normalize text for comparison by removing brand names, links, and extra whitespace."""
        # Remove brand variables (both simple and with parameters) from FTL
        text = re.sub(r"\{ -brand-name-[\w-]+(?:\([^)]+\))? \}", "", text)
        # Remove common brand names that appear in PO files (already substituted)
        text = re.sub(r"\bFirefox\b", "", text, flags=re.IGNORECASE)
        # Remove link variables from FTL: { $url_xxx }
        text = re.sub(r"\{ \$\w+ \}", "", text)
        # Remove link tags from PO: <a id="a1"> and </a>
        text = re.sub(r'<a id="a\d+">', "", text)
        text = re.sub(r"</a>", "", text)
        # Remove <a> and </a> without id
        text = re.sub(r"<a[^>]*>", "", text)
        # Normalize whitespace
        text = " ".join(text.split())
        return text.strip()

    english_to_ftl_key = {}
    for ftl_key, english_text in english_ftl_entries.items():
        normalized = normalize_text(english_text)
        if normalized:
            english_to_ftl_key[normalized] = ftl_key

    # 7. Go through the PO file sections and fill in the appropriate empty text
    for entry in po:
        # Process entries that have a msgid (including those with existing msgstr)
        if entry.msgid:
            # Normalize the msgid for comparison
            normalized_msgid = normalize_text(entry.msgid)

            # Find the matching FTL key from the English mapping
            if normalized_msgid in english_to_ftl_key:
                ftl_key = english_to_ftl_key[normalized_msgid]

                # Get the translated text from the locale's FTL file
                if ftl_key in ftl_entries:
                    translated_text = ftl_entries[ftl_key]
                    translated_text = replace_variables(translated_text)
                    translated_text = convert_links(translated_text)
                    entry.msgstr = translated_text

    return po


def create_fingerprinting_translations(apps, schema_editor):
    Page = apps.get_model("wagtailcore", "Page")
    Locale = apps.get_model("wagtailcore", "Locale")

    # 1. Find the en-US Page with title="Firefox blocks fingerprinting".
    fingerprinting_page = Page.objects.get(title="Firefox blocks fingerprinting", locale__language_code="en-US")
    fingerprinting_page_specific = FeaturesDetailPage.objects.get(id=fingerprinting_page.id)

    # 2. Load the metadata file and get the locale codes.
    metadata_path = (
        Path(__file__).parent.parent.parent.parent / "data" / "www-firefox-l10n" / "metadata" / "firefox" / "features" / "fingerprinting.json"
    )
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    locale_codes = metadata["active_locales"]

    # 3. Get or create a TranslationSource for the fingerprinting_page.
    # Use the proper method that extracts all content from the page.
    translation_source, _ = TranslationSource.get_or_create_from_instance(fingerprinting_page_specific)

    # Path to the English FTL file
    english_ftl_path = Path(__file__).parent.parent.parent.parent / "l10n" / "en" / "firefox" / "features" / "fingerprinting.ftl"

    for locale_code in locale_codes:
        # Get or create the Locale.
        locale, _ = Locale.objects.get_or_create(language_code=locale_code)

        # Create the page translation (creates both Translation object and translated page)
        translation = create_page_translation(translation_source, locale)

        # Get the PO file for the translation.
        po = translation.export_po()

        # Fill in the blank places in the po file with the translations from
        # the appropriate FTL file.
        ftl_path = (
            Path(__file__).parent.parent.parent.parent / "data" / "www-firefox-l10n" / locale_code / "firefox" / "features" / "fingerprinting.ftl"
        )
        brands_path = Path(__file__).parent.parent.parent.parent / "data" / "www-firefox-l10n" / locale_code / "brands.ftl"
        po = fill_po_translations_from_ftl_file(po, ftl_path, brands_path, english_ftl_path)

        # Import the PO file (which now has the translations).
        translation.import_po(po)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0020_auto_20251029_1054"),
    ]

    operations = [
        migrations.RunPython(create_fingerprinting_translations, migrations.RunPython.noop),
    ]
