# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.forms.widgets import CheckboxSelectMultiple
from django.urls import Resolver404, resolve
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail_link_block.blocks import LinkBlock, URLValue
from wagtail_thumbnail_choice_block import ThumbnailChoiceBlock

from lib.l10n_utils.fluent import ftl
from springfield.base.i18n import normalize_language, split_path_and_normalize_language
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.rich_text import RichTextBlock
from springfield.cms.views import wagtail_serve_with_locale_fallback

if TYPE_CHECKING:
    from springfield.cms.models import ArticleDetailPage, ArticleThemePage, SpringfieldImage

HEADING_TEXT_FEATURES = [
    "bold",
    "italic",
    "link",
    "superscript",
    "subscript",
    "strikethrough",
    "fxa",
    "fx-logo",
]

EXPANDED_TEXT_FEATURES = [
    *HEADING_TEXT_FEATURES,
    "blockquote",
    "ol",
    "ul",
]

HEADING_LEVEL_CHOICES = (
    ("h1", "H1"),
    ("h2", "H2"),
    ("h3", "H3"),
    ("h4", "H4"),
    ("h5", "H5"),
    ("h6", "H6"),
)

ICON_CHOICES = [
    ("activity", "Activity"),
    ("add", "Add"),
    ("android", "Android"),
    ("apple", "Apple"),
    ("add-circle-fill", "Add Circle Fill"),
    ("add-text", "Add Text"),
    ("add-user", "Add User"),
    ("all-tabs", "All Tabs"),
    ("app-menu", "App Menu"),
    ("app-menu-space", "App Menu Space"),
    ("applied-policy", "Applied Policy"),
    ("arrow-clockwise", "Arrow Clockwise"),
    ("arrow-counterclockwise", "Arrow Counterclockwise"),
    ("arrow-down-line", "Arrow Down Line"),
    ("arrow-trending", "Arrow Trending"),
    ("audio", "Audio"),
    ("audio-muted", "Audio Muted"),
    ("authenticated-user", "Authenticated User"),
    ("auto-play-false", "Auto Play False"),
    ("auto-play-true", "Auto Play True"),
    ("avatar-signed-in-fill", "Avatar Signed In Fill"),
    ("avatar-signed-in-fill-custom-initial", "Avatar Signed In Fill Custom Initial"),
    ("avatar-signed-in-fill-profile-picture", "Avatar Signed In Fill Profile Picture"),
    ("avatar-signed-out", "Avatar Signed Out"),
    ("back", "Back"),
    ("barbell", "Barbell"),
    ("bike", "Bike"),
    ("blocked-popup", "Blocked Popup"),
    ("block", "Block"),
    ("block-download", "Block Download"),
    ("book", "Book"),
    ("bookmark", "Bookmark"),
    ("bookmark-fill", "Bookmark Fill"),
    ("bookmarks-tray", "Bookmarks Tray"),
    ("briefcase", "Briefcase"),
    ("calendar", "Calendar"),
    ("camera-false", "Camera False"),
    ("camera-true", "Camera True"),
    ("canvas-false", "Canvas False"),
    ("canvas-true", "Canvas True"),
    ("checkmark", "Checkmark"),
    ("checkmark-circle-fill", "Checkmark Circle Fill"),
    ("chevron-double-right", "Chevron Double Right"),
    ("chevron-down", "Chevron Down"),
    ("chevron-down-small", "Chevron Down Small"),
    ("chevron-left", "Chevron Left"),
    ("chevron-right", "Chevron Right"),
    ("chevron-up", "Chevron Up"),
    ("close", "Close"),
    ("close-circle-fill", "Close Circle Fill"),
    ("closed-caption", "Closed Caption"),
    ("closed-tabs", "Closed Tabs"),
    ("color-picker", "Color Picker"),
    ("comment", "Comment"),
    ("competitiveness", "Competitiveness"),
    ("craft", "Craft"),
    ("critical", "Critical"),
    ("critical-fill", "Critical Fill"),
    ("cryptominer-false", "Cryptominer False"),
    ("cryptominer-true", "Cryptominer True"),
    ("current-view", "Current View"),
    ("cursor-arrow", "Cursor Arrow"),
    ("dashboard", "Dashboard"),
    ("data-clearance", "Data Clearance"),
    ("delete", "Delete"),
    ("device-mobile", "Device Mobile"),
    ("diamond", "Diamond"),
    ("downloaded-file", "Downloaded File"),
    ("downloads", "Downloads"),
    ("edit", "Edit"),
    ("edit-active", "Edit Active"),
    ("edit-squiggle", "Edit Squiggle"),
    ("email-mask", "Email Mask"),
    ("email-shield", "Email Shield"),
    ("error", "Error"),
    ("error-fill", "Error Fill"),
    ("even-spreads", "Even Spreads"),
    ("export-data", "Export Data"),
    ("extension", "Extension"),
    ("extension-critical", "Extension Critical"),
    ("extension-fill", "Extension Fill"),
    ("extension-warning", "Extension Warning"),
    ("external-link", "External Link"),
    ("find-in-page", "Find In Page"),
    ("firefox-bridge", "Firefox Bridge"),
    ("firefox-browser-bridge", "Firefox Browser Bridge"),
    ("flower", "Flower"),
    ("folder", "Folder"),
    ("folder-arrow-down", "Folder Arrow Down"),
    ("folder-fill", "Folder Fill"),
    ("fingerprinter-false", "Fingerprinter False"),
    ("fingerprinter-true", "Fingerprinter True"),
    ("footprints-false", "Footprints False"),
    ("footprints-true", "Footprints True"),
    ("forward", "Forward"),
    ("forward-small", "Forward Small"),
    ("fullscreen-disabled", "Fullscreen Disabled"),
    ("fullscreen-exit", "Fullscreen Exit"),
    ("fullscreen-expand", "Fullscreen Expand"),
    ("fx-view", "Fx View"),
    ("gift", "Gift"),
    ("globe", "Globe"),
    ("globe-slash", "Globe Slash"),
    ("hammer", "Hammer"),
    ("hand", "Hand"),
    ("heart", "Heart"),
    ("heart-rate", "Heart Rate"),
    ("help", "Help"),
    ("help-fill", "Help Fill"),
    ("highlighter", "Highlighter"),
    ("history", "History"),
    ("home", "Home"),
    ("horizontal-scrolling", "Horizontal Scrolling"),
    ("identity", "Identity"),
    ("import-data", "Import Data"),
    ("import-export", "Import Export"),
    ("image-tracker-false", "Image Tracker False"),
    ("image-tracker-true", "Image Tracker True"),
    ("information", "Information"),
    ("information-fill", "Information Fill"),
    ("layer", "Layer"),
    ("leaf", "Leaf"),
    ("library", "Library"),
    ("lightbulb", "Lightbulb"),
    ("line-arrow-up", "Line Arrow Up"),
    ("list", "List"),
    ("list-arrow-left", "List Arrow Left"),
    ("lock", "Lock"),
    ("lock-document", "Lock Document"),
    ("lock-insecure", "Lock Insecure"),
    ("lock-warning", "Lock Warning"),
    ("local-host-false", "Local Host False"),
    ("local-host-true", "Local Host True"),
    ("local-network-false", "Local Network False"),
    ("local-network-true2", "Local Network True2"),
    ("location-false", "Location False"),
    ("location-true", "Location True"),
    ("login", "Login"),
    ("makeup", "Makeup"),
    ("microphone-false", "Microphone False"),
    ("microphone-true", "Microphone True"),
    ("midi", "Midi"),
    ("musical-note", "Musical Note"),
    ("newsfeed", "Newsfeed"),
    ("notifications-false", "Notifications False"),
    ("notifications-true", "Notifications True"),
    ("no-spreads", "No Spreads"),
    ("odd-spreads", "Odd Spreads"),
    ("off", "Off"),
    ("open-tabs", "Open Tabs"),
    ("organizational-unit", "Organizational Unit"),
    ("packaging", "Packaging"),
    ("page-actions", "Page Actions"),
    ("page-landscape", "Page Landscape"),
    ("page-portrait", "Page Portrait"),
    ("page-scrolling", "Page Scrolling"),
    ("page-thumbnails", "Page Thumbnails"),
    ("palette", "Palette"),
    ("paperclip", "Paperclip"),
    ("passkey", "Passkey"),
    ("pause-fill", "Pause Fill"),
    ("paw-print", "Paw Print"),
    ("payment-methods", "Payment Methods"),
    ("picture-in-picture-closed", "Picture In Picture Closed"),
    ("picture-in-picture-open", "Picture In Picture Open"),
    ("pin", "Pin"),
    ("pin-fill", "Pin Fill"),
    ("plane", "Plane"),
    ("play-fill", "Play Fill"),
    ("playback-forward", "Playback Forward"),
    ("playback-rewind", "Playback Rewind"),
    ("plugin-false", "Plugin False"),
    ("plugin-true", "Plugin True"),
    ("popup-subitem", "Popup Subitem"),
    ("pocket", "Pocket"),
    ("pocket-fill", "Pocket Fill"),
    ("policy", "Policy"),
    ("presentation-mode", "Presentation Mode"),
    ("price", "Price"),
    ("print", "Print"),
    ("private-mode-circle-fill", "Private Mode Circle Fill"),
    ("private-mode-fill", "Private Mode Fill"),
    ("quality", "Quality"),
    ("reader-mode", "Reader Mode"),
    ("remove-user", "Remove User"),
    ("screenshot-camera", "Camera (Screenshot)"),
    ("search", "Search"),
    ("search-in-circle", "Search In Circle"),
    ("search-in-circle-right", "Search In Circle Right"),
    ("screesnshare-false", "Screesnshare False"),
    ("screesnshare-true", "Screesnshare True"),
    ("settings", "Settings"),
    ("share-macos", "Share Macos"),
    ("share-winos", "Share Winos"),
    ("shield", "Shield"),
    ("shipping", "Shipping"),
    ("shopping", "Shopping"),
    ("shopping-cart", "Shopping Cart"),
    ("show-password-false", "Show Password False"),
    ("show-password-true", "Show Password True"),
    ("sidebar-collapsed", "Sidebar Collapsed"),
    ("sidebar-collapsed-right", "Sidebar Collapsed Right"),
    ("sidebar-expanded", "Sidebar Expanded"),
    ("sidebar-expanded-right", "Sidebar Expanded Right"),
    ("sidebar-hidden", "Sidebar Hidden"),
    ("sidebar-left", "Sidebar Left"),
    ("sidebar-right", "Sidebar Right"),
    ("signature-properties", "Signature Properties"),
    ("single-user", "Single User"),
    ("soccer-ball", "Soccer Ball"),
    ("social-tracker-false", "Social Tracker False"),
    ("social-tracker-true", "Social Tracker True"),
    ("sort", "Sort"),
    ("sparkle-single", "Sparkle Single"),
    ("sparkles", "Sparkles"),
    ("split-view", "Split View"),
    ("split-view-left", "Split View Left"),
    ("split-view-right", "Split View Right"),
    ("storage-false", "Storage False"),
    ("storage-true", "Storage True"),
    ("subtract", "Subtract"),
    ("subtract-circle-fill", "Subtract Circle Fill"),
    ("sync", "Sync"),
    ("synced-tabs", "Synced Tabs"),
    ("tab", "Tab"),
    ("tab-group", "Tab Group"),
    ("tab-notes", "Tab Notes"),
    ("taskbar-add-tab", "Taskbar Add Tab"),
    ("taskbar-move-tab", "Taskbar Move Tab"),
    ("taskbar-remove-tab", "Taskbar Remove Tab"),
    ("text-cursor", "Text Cursor"),
    ("themes", "Themes"),
    ("top-sites", "Top Sites"),
    ("toggle-on", "Toggle On"),
    ("tracking-cookies-false", "Tracking Cookies False"),
    ("tracking-cookies-true", "Tracking Cookies True"),
    ("translate", "Translate"),
    ("trending", "Trending"),
    ("unauthenticated-user", "Unauthenticated User"),
    ("update", "Update"),
    ("update-circle-fill", "Update Circle Fill"),
    ("users", "Users"),
    ("vertical-scrolling", "Vertical Scrolling"),
    ("vertical-tabs", "Vertical Tabs"),
    ("video-game-controller", "Video Game Controller"),
    ("vpn-disconnected", "Vpn Disconnected"),
    ("vpn-off", "Vpn Off"),
    ("vpn-on", "Vpn On"),
    ("vpn-on-off-site", "Vpn On Off Site"),
    ("warning", "Warning"),
    ("warning-fill", "Warning Fill"),
    ("window", "Window"),
    ("window-firefox", "Window Firefox"),
    ("wrapped-scrolling", "Wrapped Scrolling"),
    ("xr-false", "XR False"),
    ("xr-true", "XR True"),
    ("add-to-homescreen", "Add To Homescreen"),
    ("help-circle", "Help Circle"),
    ("help-circle-fill", "Help Circle Fill"),
    ("update-circle", "Update Circle"),
    ("more-grid", "More Grid"),
    ("more-horizontal", "More Horizontal"),
    ("more-horizontal-round", "More Horizontal Round"),
    ("more-vertical", "More Vertical"),
    ("more-vertical-round", "More Vertical Round"),
    ("append-down-left", "Append Down Left"),
    ("append-up-right", "Append Up Right"),
    ("arrow-counter-clockwise", "Arrow Counter Clockwise"),
    ("avatar-circle-fill", "Avatar Circle Fill"),
    ("avatar-info-circle-fill", "Avatar Info Circle Fill"),
    ("avatar-warning-circle-fill", "Avatar Warning Circle Fill"),
    ("bookmark-slash", "Bookmark Slash"),
    ("bookmark-tray", "Bookmark Tray"),
    ("bookmark-tray-fill", "Bookmark Tray Fill"),
    ("cross-circle", "Cross Circle"),
    ("cross-circle-fill", "Cross Circle Fill"),
    ("device-desktop-fill", "Device Desktop Fill"),
    ("device-desktop-send", "Device Desktop Send"),
    ("device-tablet", "Device Tablet"),
    ("other-device-shortcuts", "Other Device Shortcuts"),
    ("save", "Save"),
    ("save-file", "Save File"),
    ("clipboard", "Clipboard"),
    ("copy", "Copy"),
    ("signature", "Signature"),
    ("extension-cog", "Extension Cog"),
    ("folder-add", "Folder Add"),
    ("folder-arrow-right", "Folder Arrow Right"),
    ("lightning-filled", "Lightning Filled"),
    ("lock-fill", "Lock Fill"),
    ("lock-slash", "Lock Slash"),
    ("lock-slash-fill", "Lock Slash Fill"),
    ("lock-warning-fill", "Lock Warning Fill"),
    ("logo-chrome", "Logo Chrome"),
    ("logo-safari", "Logo Safari"),
    ("night-mode-fill", "Night Mode Fill"),
    ("notification-dot", "Notification Dot"),
    ("blocked-false", "Blocked False"),
    ("blocked-true", "Blocked True"),
    ("eye-false", "Eye False"),
    ("eye-true", "Eye True"),
    ("location", "Location"),
    ("microphone-false-mobile", "Microphone False Mobile"),
    ("microphone-true-mobile", "Microphone True Mobile"),
    ("permission", "Permission"),
    ("pin-slash", "Pin Slash"),
    ("pin-slash-fill", "Pin Slash Fill"),
    ("pause", "Pause"),
    ("reader-view-customize", "Reader View Customize"),
    ("reader-view-fill", "Reader View Fill"),
    ("reading-list", "Reading List"),
    ("reading-list-add", "Reading List Add"),
    ("reading-list-slash", "Reading List Slash"),
    ("reading-list-slash-fill", "Reading List Slash Fill"),
    ("grid-plus", "Grid Plus"),
    ("tool", "Tool"),
    ("share-ios", "Share iOS"),
    ("shield-checkmark", "Shield Checkmark"),
    ("shield-cross", "Shield Cross"),
    ("shield-dot", "Shield Dot"),
    ("shield-exclamation-mark", "Shield Exclamation Mark"),
    ("shield-slash", "Shield Slash"),
    ("sun-fill", "Sun Fill"),
    ("cloud", "Cloud"),
    ("sync-tabs", "Sync Tabs"),
    ("tab-number", "Tab Number"),
    ("thumbs-down", "Thumbs Down"),
    ("thumbs-down-fill", "Thumbs Down Fill"),
    ("thumbs-up-fill", "Thumbs Up Fill"),
    ("cookies", "Cookies"),
    ("cookies-slash", "Cookies Slash"),
    ("fingerprinter", "Fingerprinter"),
    ("translate-active", "Translate Active"),
    ("translate-active-alt", "Translate Active Alt"),
    ("page-zoom-fill", "Page Zoom Fill"),
]

PLATFORM_CHOICES = [
    ("osx", "macOS"),
    ("linux", "Linux"),
    ("windows", "Windows"),
    ("windows-10-plus", "Windows 10+"),
    ("android", "Android"),
    ("ios", "iOS"),
    ("other-os", "Other OS"),
    ("unsupported", "Unsupported OS"),
]
FIREFOX_CHOICES = [
    ("", "No restriction"),
    ("is-firefox", "Firefox only"),
    ("not-firefox", "Non-Firefox only"),
]
AUTH_CHOICES = [
    ("", "No restriction"),
    ("state-fxa-supported-signed-in", "Signed-in only"),
    ("state-fxa-supported-signed-out", "Signed-out only"),
]
DEFAULT_BROWSER_CHOICES = [
    ("", "No restriction"),
    ("is-default", "Firefox is default browser"),
    ("is-not-default", "Firefox is not default browser"),
]

UITOUR_BUTTON_NEW_TAB = "open_new_tab"
UITOUR_BUTTON_ABOUT_PREFERENCES = "open_about_preferences"
UITOUR_BUTTON_ABOUT_PREFERENCES_GENERAL = "open_about_preferences_general"
UITOUR_BUTTON_ABOUT_PREFERENCES_HOME = "open_about_preferences_home"
UITOUR_BUTTON_ABOUT_PREFERENCES_SEARCH = "open_about_preferences_search"
UITOUR_BUTTON_ABOUT_PREFERENCES_PRIVACY = "open_about_preferences_privacy"
UITOUR_BUTTON_ABOUT_PREFERENCES_AI = "open_about_preferences_ai"
UITOUR_BUTTON_ABOUT_PREFERENCES_EXPERIMENTAL = "open_about_preferences_experimental"
UITOUR_BUTTON_ABOUT_PREFERENCES_SYNC = "open_about_preferences_sync"
UITOUR_BUTTON_ABOUT_PREFERENCES_MORE_FROM_MOZILLA = "open_about_preferences_more_from_mozilla"
UITOUR_BUTTON_PROTECTIONS_REPORT = "open_protections_report"
UITOUR_BUTTON_SMART_WINDOW = "open_smart_window"
UITOUR_BUTTON_CHOICES = (
    (UITOUR_BUTTON_NEW_TAB, "Open New Tab"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES, "Open Preferences"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_GENERAL, "Open Preferences - General"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_HOME, "Open Preferences - Home"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_SEARCH, "Open Preferences - Search"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_PRIVACY, "Open Preferences - Privacy"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_AI, "Open Preferences - AI Control"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_EXPERIMENTAL, "Open Preferences - Experimental"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_SYNC, "Open Preferences - Sync"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_MORE_FROM_MOZILLA, "Open Preferences - More From Mozilla"),
    (UITOUR_BUTTON_PROTECTIONS_REPORT, "Open Protections Report"),
    (UITOUR_BUTTON_SMART_WINDOW, "Open Smart Window"),
)

UI_TOUR_CLASSES = {
    UITOUR_BUTTON_NEW_TAB: "ui-tour-open-new-tab",
    UITOUR_BUTTON_ABOUT_PREFERENCES: "ui-tour-open-about-preferences",
    UITOUR_BUTTON_ABOUT_PREFERENCES_GENERAL: "ui-tour-open-about-preferences-general",
    UITOUR_BUTTON_ABOUT_PREFERENCES_HOME: "ui-tour-open-about-preferences-home",
    UITOUR_BUTTON_ABOUT_PREFERENCES_SEARCH: "ui-tour-open-about-preferences-search",
    UITOUR_BUTTON_ABOUT_PREFERENCES_PRIVACY: "ui-tour-open-about-preferences-privacy",
    UITOUR_BUTTON_ABOUT_PREFERENCES_AI: "ui-tour-open-about-preferences-ai",
    UITOUR_BUTTON_ABOUT_PREFERENCES_EXPERIMENTAL: "ui-tour-open-about-preferences-experimental",
    UITOUR_BUTTON_ABOUT_PREFERENCES_SYNC: "ui-tour-open-about-preferences-sync",
    UITOUR_BUTTON_ABOUT_PREFERENCES_MORE_FROM_MOZILLA: "ui-tour-open-about-preferences-moreFromMozilla",
    UITOUR_BUTTON_PROTECTIONS_REPORT: "ui-tour-open-protections-report",
    UITOUR_BUTTON_SMART_WINDOW: "ui-tour-open-smart-window",
}

BUTTON_TYPE = "button"
UITOUR_BUTTON_TYPE = "uitour_button"
FXA_BUTTON_TYPE = "fxa_button"
SET_AS_DEFAULT_BUTTON = "set_as_default_button"
DOWNLOAD_BUTTON_TYPE = "download_button"
STORE_BUTTON_TYPE = "store_button"
FOCUS_BUTTON_TYPE = "focus_button"


BUTTON_PRIMARY = ""
BUTTON_SECONDARY = "secondary"
BUTTON_TERTIARY = "tertiary"
BUTTON_GHOST = "ghost"
BUTTON_LINK = "link"
BUTTON_THEME_CHOICES = {
    BUTTON_PRIMARY: "Primary",
    BUTTON_SECONDARY: "Secondary",
    BUTTON_TERTIARY: "Tertiary",
    BUTTON_GHOST: "Ghost",
    BUTTON_LINK: "Link",
}
BUTTON_THEMES_2025 = [BUTTON_PRIMARY, BUTTON_SECONDARY, BUTTON_TERTIARY, BUTTON_GHOST]
BUTTON_THEMES_2026 = [BUTTON_PRIMARY, BUTTON_SECONDARY, BUTTON_GHOST, BUTTON_LINK]


def validate_animation_url(value):
    if value and "assets.mozilla.net" not in value:
        raise ValidationError("Please provide a valid assets.mozilla.net URL for the animation.")
    return value


def validate_video_url(value):
    if value and "youtube.com" not in value and "youtu.be" not in value and "assets.mozilla.net" not in value:
        raise ValidationError("Please provide a valid YouTube or assets.mozilla.net URL for the video.")
    return value


class LocalizedLiveSnippetChooserBlock(SnippetChooserBlock):
    """A SnippetChooserBlock that renders the live localized version of the selected snippet."""

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        if value and hasattr(value, "get_localized"):
            localized_instance = value.get_localized()
            context[self.TEMPLATE_VAR] = localized_instance
            context["self"] = localized_instance
        return context

    def clean(self, value):
        if value and not value.live:
            raise ValidationError("The selected snippet is not published.")
        return super().clean(value)


class IconChoiceBlock(ThumbnailChoiceBlock):
    def __init__(self, choices=None, thumbnails=None, thumbnail_templates=None, thumbnail_size=20, **kwargs):
        choices = choices or ICON_CHOICES
        thumbnail_templates = {choice[0]: "cms/wagtailadmin/icon-choice.html" for choice in choices}
        super().__init__(choices, thumbnails, thumbnail_templates, thumbnail_size, **kwargs)


class ConditionalDisplayBlock(blocks.StructBlock):
    platforms = blocks.MultipleChoiceBlock(
        choices=PLATFORM_CHOICES,
        required=False,
        help_text="Show to specific platforms. Leave empty to show to all platforms.",
        widget=CheckboxSelectMultiple,
    )
    firefox = blocks.ChoiceBlock(
        choices=FIREFOX_CHOICES,
        default="",
        required=False,
        label="Firefox",
        help_text="Filter by Firefox browser. Leave empty for no restriction.",
    )
    auth_state = blocks.ChoiceBlock(
        choices=AUTH_CHOICES,
        default="",
        required=False,
        label="Login state",
        help_text="Filter by login state. Leave empty for no restriction.",
    )
    default_browser = blocks.ChoiceBlock(
        choices=DEFAULT_BROWSER_CHOICES,
        default="",
        required=False,
        label="Default Browser",
        help_text="Filter by default browser state. Leave empty for no restriction.",
    )
    min_version = blocks.IntegerBlock(required=False, label="Minimum Firefox version")
    max_version = blocks.IntegerBlock(required=False, label="Maximum Firefox version")

    class Meta:
        label = "Conditional Display"
        label_format = "Conditions: {platforms} - {firefox} - {auth_state}"
        icon = "eye"
        collapsed = True
        form_classname = "compact-form struct-block"


# Element blocks


def HeadingBlock(required=True, all_required=False, **kwargs):
    class _HeadingBlock(blocks.StructBlock):
        superheading_text = RichTextBlock(features=HEADING_TEXT_FEATURES, required=all_required)
        heading_text = RichTextBlock(features=HEADING_TEXT_FEATURES, required=required)
        subheading_text = RichTextBlock(features=HEADING_TEXT_FEATURES, required=all_required)

        class Meta:
            icon = "title"
            label = "Heading"
            label_format = "{heading_text}"
            template = "cms/blocks/heading.html"

    return _HeadingBlock(**kwargs)


# Buttons


def get_button_types(allow_uitour=False):
    """Helper function to get button types based on allow_uitour flag.

    Args:
        allow_uitour: If True, includes UI Tour button type.

    Returns:
        List of button type strings.
    """
    base_button_types = [BUTTON_TYPE, FXA_BUTTON_TYPE, DOWNLOAD_BUTTON_TYPE, STORE_BUTTON_TYPE, FOCUS_BUTTON_TYPE]
    if allow_uitour:
        return [*base_button_types, UITOUR_BUTTON_TYPE, SET_AS_DEFAULT_BUTTON]
    return base_button_types


class BaseButtonValue(blocks.StructValue):
    def theme_class(self) -> str:
        classes = {
            "ghost": "button-ghost",
            "secondary": "button-secondary",
            "tertiary": "button-tertiary",
            "link": "button-link",
        }
        return classes.get(self.get("settings", {}).get("theme"), "")


class UUIDBlock(blocks.CharBlock):
    def clean(self, value):
        return super().clean(value) or str(uuid4())

    def get_translatable_segments(self, value):
        # UUIDs are analytics IDs, not user-facing content — exclude from translation.
        return []

    def restore_translated_segments(self, value, segments):
        return value


def BaseButtonSettings(themes=None, **kwargs):
    themes = themes or BUTTON_THEME_CHOICES.keys()

    class _BaseButtonSettings(blocks.StructBlock):
        theme = blocks.ChoiceBlock(
            choices=[(theme, BUTTON_THEME_CHOICES[theme]) for theme in themes],
            required=len(themes) == 1,
            inline_form=True,
        )
        icon = IconChoiceBlock(required=False)
        icon_position = blocks.ChoiceBlock(
            choices=(("left", "Left"), ("right", "Right")),
            default="right",
            label="Icon Position",
            inline_form=True,
        )
        analytics_id = UUIDBlock(
            label="Analytics ID",
            help_text="Unique identifier for analytics tracking. Leave blank to auto-generate.",
            required=False,
        )

        class Meta:
            icon = "cog"
            collapsed = True
            label = "Settings"
            label_format = "Theme: {theme} - Icon: {icon} ({icon_position}) - Analytics ID: {analytics_id}"
            form_classname = "compact-form struct-block"

    return _BaseButtonSettings(**kwargs)


class SpringfieldLinkBlockURLValue(URLValue):
    @staticmethod
    def _with_locale_prefix(url, lang):
        """Replace the locale prefix in url with lang, or return url unchanged if unparseable."""
        if url:
            # page.url can return an absolute URL (e.g. http://host/en-US/path/)
            # when the page belongs to a different Wagtail site. Extract just the path.
            parsed = urlparse(url)
            path = parsed.path if parsed.scheme or parsed.netloc else url
            parts = path.lstrip("/").split("/", 1)
            if len(parts) == 2:
                return f"/{lang}/{parts[1]}"
        return url

    def get_url(self):
        """
        Override the get_url() method to:
            - provide logic for returning a locale-appropriate relative_url
            - provide logic for returning a locale-appropriate page URL
        """
        link_to = self.get("link_to")

        if link_to == "relative_url":
            path = self.get(link_to)
            if path:
                try:
                    locale = SpringfieldLocale.get_active()
                    # To make sure we return the URL prefixed with the user-facing locale,
                    # we reconstruct the URL using the URL-facing locale prefix.
                    active_lang = normalize_language(translation.get_language()) or locale.language_code
                    return f"/{active_lang}/{path.lstrip('/')}"
                except SpringfieldLocale.DoesNotExist:
                    return path
            return path

        if link_to == "page":
            page = self.get("page")
            if page:
                try:
                    locale = SpringfieldLocale.get_active()
                    # Get the active language, so we can use it to determine the URL to return.
                    active_lang = normalize_language(translation.get_language()) or locale.language_code
                    try:
                        translated_page = page.get_translation(locale)
                        # If the translated page matches the active language,
                        # then return the translated page's URL.
                        if translated_page.locale.language_code == active_lang:
                            return translated_page.url
                        # The translated page doesn not match the active language;
                        # we reconstruct the URL using the URL-facing locale prefix.
                        return self._with_locale_prefix(translated_page.url, active_lang)
                    except Page.DoesNotExist:
                        # This means that this page has no translation for this locale.
                        # In case this is rendered as a fallback page (the user
                        # requested /es-AR/somepage, but that page doesn't exist
                        # in the es-AR locale, so the user is served the content
                        # from the es-MX locale's somepage at the /es-AR/somepage URL),
                        # we want to make sure that the URL we return here matches
                        # the requested locale. For example, for a page link to
                        # the /features/control/ page, we want to return
                        # /es-AR/features/control/ (not /es-MX/features/control/).
                        return self._with_locale_prefix(page.url, active_lang)
                except SpringfieldLocale.DoesNotExist:
                    return page.url
            return None

        return super().get_url()


class SpringfieldLinkBlock(LinkBlock):
    """
    Extends LinkBlock with a ``relative_url`` link type.

    LinkBlock works well, but we also want to give CMS users a relative_url
    option, where they can type in a relative URL to a page on the site.
    The reason for this extra field is to allow CMS users to link to static pages,
    while also rendering those links in the appropriate locale for end users.
    For example, a CMS user may link to the /features/ page, and an end user
    browsing in en-US would see a link to /en-US/features/, while a user
    browsing in es-ES would see a link to /es-ES/features/.
    """

    link_to = blocks.ChoiceBlock(
        choices=[
            ("page", _("Page")),
            ("file", _("File")),
            ("custom_url", _("Custom URL")),
            ("relative_url", _("Relative URL")),
            ("email", _("Email")),
            ("anchor", _("Anchor")),
            ("phone", _("Phone")),
        ],
        required=False,
        classname="link_choice_type_selector",
        label=_("Link to"),
    )
    relative_url = blocks.CharBlock(
        required=False,
        classname="relative_url_link",
        label=_("Relative URL"),
        help_text=_(
            "Site-relative path without a locale prefix, e.g. /features/ — the "
            "locale is added automatically. Note: the Relative URL is meant for "
            "linking to static pages (not managed here). If you are linking to "
            "a page, please select 'Page', instead of 'Relative URL'."
        ),
    )

    class Meta:
        value_class = SpringfieldLinkBlockURLValue

    def __init__(self, *args, **kwargs):
        """Override __init__() to put relative_url field right after custom_url field."""
        super().__init__(*args, **kwargs)
        items = list(self.child_blocks.items())
        keys = [k for k, _ in items]
        relative_url_item = items.pop(keys.index("relative_url"))
        items.insert(keys.index("custom_url") + 1, relative_url_item)
        self.child_blocks = dict(items)

    def clean(self, value):
        # Full override of LinkBlock.clean() required: that method has a
        # hardcoded url_default_values dict, so we cannot inject relative_url
        # into it without rewriting the method. Without this override,
        # relative_url would not be cleared when a different link type is chosen.
        clean_values = blocks.StructBlock.clean(self, value)
        errors = {}

        url_default_values = {
            "page": None,
            "file": None,
            "custom_url": "",
            "relative_url": "",
            "anchor": "",
            "email": "",
            "phone": "",
        }
        url_type = clean_values.get("link_to")

        if url_type != "" and clean_values.get(url_type) in [None, ""]:
            errors[url_type] = ErrorList(["You need to add a {} link".format(url_type.replace("_", " "))])
        elif url_type == "relative_url":
            path = clean_values.get("relative_url", "")
            # If the relative URL has a locale prefix, raise an error.
            lang_code, _, _ = split_path_and_normalize_language(path)
            if lang_code:
                errors["relative_url"] = ErrorList(["Do not include a locale prefix (e.g. use /features/ not /en-US/features/)."])
            else:
                # Raise an error if either:
                #  - the relative URL does not exist on the site, or
                #  - the relative URL matches a Wagtail Page URL
                error_msg = "This URL does not match any existing static URL on the site. If linking to a page, select 'Page'"
                try:
                    path_to_check = f"/en-US/{path.lstrip('/')}"
                    with translation.override("en-US"):
                        match = resolve(path_to_check)
                    if match.func == wagtail_serve_with_locale_fallback:
                        errors["relative_url"] = ErrorList([error_msg])
                except Resolver404:
                    errors["relative_url"] = ErrorList([error_msg])
        if not errors:
            try:
                url_default_values.pop(url_type, None)
                for field in url_default_values:
                    clean_values[field] = url_default_values[field]
            except KeyError:
                errors[url_type] = ErrorList(["Enter a valid link type"])

        if errors:
            raise blocks.StreamBlockValidationError(block_errors=errors, non_block_errors=ErrorList([]))

        return clean_values


def ButtonBlock(themes=None, **kwargs):
    """Factory function to create ButtonBlock with specified themes.

    Args:
        themes: List of theme strings to include in the button settings.
    """

    class _ButtonBlock(blocks.StructBlock):
        settings = BaseButtonSettings(themes=themes)
        label = blocks.CharBlock(label="Button Text")
        link = SpringfieldLinkBlock()

        class Meta:
            template = "cms/blocks/button.html"
            label = "Button"
            label_format = "Button - {label}"
            value_class = BaseButtonValue

    return _ButtonBlock(**kwargs)


class UITourButtonValue(BaseButtonValue):
    def theme_class(self) -> str:
        """
        Give the button the appropriate CSS class, based on its button_type.
        """
        theme_classes = super().theme_class()
        button_type = self.get("button_type", "")
        theme_classes += " " + UI_TOUR_CLASSES.get(button_type, "")
        return theme_classes


def UITourButtonBlock(themes=None, **kwargs):
    class _UITourButtonBlock(blocks.StructBlock):
        settings = BaseButtonSettings(themes=themes)
        button_type = blocks.ChoiceBlock(
            default=UITOUR_BUTTON_NEW_TAB,
            choices=UITOUR_BUTTON_CHOICES,
            inline_form=True,
        )
        label = blocks.CharBlock(label="Button Text")

        class Meta:
            template = "cms/blocks/uitour_button.html"
            label = "UI Tour Button"
            label_format = "UI Tour Button - {label}"
            value_class = UITourButtonValue

    return _UITourButtonBlock(**kwargs)


def FXAccountButtonBlock(themes=None, **kwargs):
    class _FXAccountButtonBlock(blocks.StructBlock):
        settings = BaseButtonSettings(themes=themes)
        label = blocks.CharBlock(label="Button Text")

        class Meta:
            template = "cms/blocks/fxa_button.html"
            label = "Firefox Account Button"
            label_format = "Firefox Account Button"
            value_class = BaseButtonValue

    return _FXAccountButtonBlock(**kwargs)


def SetAsDefaultButtonBlock(themes=None, **kwargs):
    class _SetAsDefaultButtonBlock(blocks.StructBlock):
        settings = BaseButtonSettings(themes=themes)
        label = blocks.CharBlock(label="Button Text")
        snippet = LocalizedLiveSnippetChooserBlock("cms.SetAsDefaultSnippet", label="Set as Default Snippet")

        class Meta:
            template = "cms/blocks/set_as_default_button.html"
            label = "Set As Default Button"
            label_format = "Set As Default Button"
            value_class = BaseButtonValue

    return _SetAsDefaultButtonBlock(**kwargs)


def DownloadFirefoxButtonSettings(themes=None, **kwargs):
    themes = themes or BUTTON_THEME_CHOICES.keys()

    class _DownloadFirefoxButtonSettings(blocks.StructBlock):
        theme = blocks.ChoiceBlock(
            choices=[(theme, BUTTON_THEME_CHOICES[theme]) for theme in themes],
            required=len(themes) == 1,
            inline_form=True,
        )
        icon_position = blocks.ChoiceBlock(
            choices=(("left", "Left"), ("right", "Right")),
            default="right",
            label="Icon Position",
            inline_form=True,
        )
        icon = IconChoiceBlock(required=False)
        analytics_id = UUIDBlock(
            label="Analytics ID",
            help_text="Unique identifier for analytics tracking. Leave blank to auto-generate.",
            required=False,
        )
        show_default_browser_checkbox = blocks.BooleanBlock(
            required=False,
            default=False,
            help_text="Show 'Set as default browser' checkbox to Windows users. Attention! This will affect all download buttons on the page.",
        )
        show_extra_links = blocks.BooleanBlock(
            required=False,
            default=True,
            help_text="Display a link to the Privacy Notice and a note about usuported systems (for user in those systems) below the button.",
        )

        class Meta:
            icon = "cog"
            collapsed = True
            label = "Settings"
            label_format = (
                "Theme: {theme} - Icon: {icon} ({icon_position}) - Analytics ID: {analytics_id} - "
                "Show Default Browser Checkbox: {show_default_browser_checkbox}"
            )
            form_classname = "compact-form struct-block"

    return _DownloadFirefoxButtonSettings(**kwargs)


def DownloadFirefoxButtonBlock(themes=None, **kwargs):
    class _DownloadFirefoxButtonBlock(blocks.StructBlock):
        settings = DownloadFirefoxButtonSettings(themes=themes)
        label = blocks.CharBlock(label="Button Text", default="Get Firefox")

        class Meta:
            label = "Download Firefox Button"
            label_format = "Download Firefox Button - {label}"
            template = "cms/blocks/download-firefox-button.html"
            value_class = BaseButtonValue

    return _DownloadFirefoxButtonBlock(**kwargs)


class StoreButtonBlock(blocks.StructBlock):
    store = blocks.ChoiceBlock(
        choices=[
            ("android", "Android (Google Play)"),
            ("ios", "iOS (App Store)"),
        ],
        label="Store",
    )

    class Meta:
        label = "Store Button"
        label_format = "Store Button - {store}"
        template = "cms/blocks/store-button.html"


def FirefoxFocusButtonBlock(themes=None, **kwargs):
    class _FirefoxFocusButtonBlock(blocks.StructBlock):
        settings = BaseButtonSettings(themes=themes)
        label = blocks.CharBlock(label="Button Text", default="Get Firefox Focus")
        store = blocks.ChoiceBlock(
            choices=[
                ("android", "Android (Google Play)"),
                ("ios", "iOS (App Store)"),
            ],
            label="Store",
        )

        class Meta:
            label = "Firefox Focus Button"
            label_format = "Firefox Focus Button - {label}"
            template = "cms/blocks/firefox-focus-button.html"
            value_class = BaseButtonValue

    return _FirefoxFocusButtonBlock(**kwargs)


def MixedButtonsBlock(
    button_types: list,
    min_num: int,
    max_num: int,
    themes=BUTTON_THEMES_2025,
    label="Buttons",
    **kwargs,
):
    """
    Creates a StreamBlock that can contain either regular buttons or UI Tour buttons.

    The min_num and max_num parameters control the total number of buttons (combined).

    Example: min_num=0 and max_num=2 allows up to 2 buttons, or up to 2 UI Tour
    buttons, or up to 1 of each.
    """
    button_blocks = {
        BUTTON_TYPE: ButtonBlock(themes=themes),
        UITOUR_BUTTON_TYPE: UITourButtonBlock(themes=themes),
        SET_AS_DEFAULT_BUTTON: SetAsDefaultButtonBlock(themes=themes),
        FXA_BUTTON_TYPE: FXAccountButtonBlock(themes=themes),
        DOWNLOAD_BUTTON_TYPE: DownloadFirefoxButtonBlock(themes=themes),
        STORE_BUTTON_TYPE: StoreButtonBlock(),
        FOCUS_BUTTON_TYPE: FirefoxFocusButtonBlock(themes=themes),
    }
    return blocks.StreamBlock(
        [(button_type, button_blocks[button_type]) for button_type in button_types],
        max_num=max_num,
        min_num=min_num,
        label=label,
        **kwargs,
    )


class CTASettings(blocks.StructBlock):
    analytics_id = UUIDBlock(
        label="Analytics ID",
        help_text="Unique identifier for analytics tracking. Leave blank to auto-generate.",
        required=False,
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Analytics ID: {analytics_id}"
        form_classname = "compact-form struct-block"


class CTABlock(blocks.StructBlock):
    settings = CTASettings()
    label = blocks.CharBlock(label="Link Text")
    link = SpringfieldLinkBlock()

    class Meta:
        label = "Link"
        label_format = "Link - {label}"
        template = "cms/blocks/cta-link.html"


class TagBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    icon = IconChoiceBlock()
    icon_position = blocks.ChoiceBlock(
        choices=(("before", "Before"), ("after", "After")),
        default="before",
        label="Icon Position",
        inline_form=True,
    )
    corners = blocks.ChoiceBlock(
        choices=(("round", "Round"), ("soft", "Soft")),
        default="round",
        inline_form=True,
    )
    color = blocks.ChoiceBlock(
        choices=[
            ("purple", "Purple"),
            ("blue", "Blue"),
            ("orange", "Orange"),
            ("yellow", "Yellow"),
            ("white", "White"),
            ("black", "Black"),
            ("outline", "Outline"),
        ],
        required=False,
    )

    class Meta:
        template = "cms/blocks/tag.html"
        label = "Tag"
        label_format = "Tag - {title}"
        form_classname = "compact-form struct-block"


class TagBlock2026(blocks.StructBlock):
    title = blocks.CharBlock()
    icon = IconChoiceBlock()
    icon_position = blocks.ChoiceBlock(
        choices=(("before", "Before"), ("after", "After")),
        default="before",
        label="Icon Position",
        inline_form=True,
    )
    color = blocks.ChoiceBlock(
        choices=[
            ("purple", "Purple"),
            ("red", "Red"),
            ("orange", "Orange"),
            ("green", "Green"),
        ],
        default="purple",
        required=False,
        inline_form=True,
    )

    class Meta:
        template = "cms/blocks/tag.html"
        label = "Tag"
        label_format = "Tag - {title}"
        form_classname = "compact-form struct-block"


class ImageVariantsBlockSettings(blocks.StructBlock):
    dark_mode_image = ImageChooserBlock(
        required=False,
        label="Dark Mode Image",
        help_text="Optional dark mode image variant",
    )
    mobile_image = ImageChooserBlock(
        required=False,
        label="Mobile Image",
        help_text="Optional mobile image variant",
    )
    dark_mode_mobile_image = ImageChooserBlock(
        required=False,
        label="Dark Mode Mobile Image",
        help_text="Optional dark mode mobile image variant",
    )

    class Meta:
        icon = "image"
        collapsed = True
        label = "Image variants"
        label_format = ""
        form_classname = "compact-form struct-block"


def ImageVariantsBlock(required=True, *args, **kwargs):
    class _ImageVariantsBlock(blocks.StructBlock):
        image = ImageChooserBlock(required=required)
        settings = ImageVariantsBlockSettings()

        class Meta:
            label = "Image"
            label_format = "Image - {image}"
            template = "cms/blocks/image-variants.html"

    return _ImageVariantsBlock(*args, **kwargs)


class VideoBlock(blocks.StructBlock):
    video_url = blocks.URLBlock(
        label="Video URL",
        help_text="Link to a video from YouTube or assets.mozilla.net.",
        validators=[validate_video_url],
    )
    alt = blocks.CharBlock(label="Alt Text", help_text="Text for screen readers describing the video.")
    poster = ImageChooserBlock(help_text="Poster image displayed before the video is played.")

    class Meta:
        label = "Video"
        label_format = "Video - {video_url}"
        template = "cms/blocks/video.html"


def AnimationBlock(required=True, *args, **kwargs):
    class _AnimationBlock(blocks.StructBlock):
        video_url = blocks.URLBlock(
            required=required,
            label="Animation URL",
            help_text="Link to a webm video from assets.mozilla.net.",
            validators=[validate_animation_url],
        )
        alt = blocks.CharBlock(required=required, label="Alt Text", help_text="Text for screen readers describing the video.")
        poster = ImageChooserBlock(required=required, help_text="Poster image displayed before the animation is played.")
        playback = blocks.ChoiceBlock(
            choices=[
                ("autoplay_loop", "Autoplay (loop)"),
                ("autoplay_once", "Autoplay (play once)"),
            ],
            default="autoplay_loop",
            label="Playback",
            help_text="Controls how the animation plays. Autoplay (loop) plays continuously. Autoplay (play once) plays on load then stops.",
            inline_form=True,
        )
        show_pause_button = blocks.BooleanBlock(default=False, required=False)

        class Meta:
            label = "Animation"
            label_format = "Animation - {video_url}"
            template = "cms/blocks/animation.html"

    return _AnimationBlock(*args, **kwargs)


class QRCodeBlock(blocks.StructBlock):
    data = blocks.CharBlock(label="QR Code Data", help_text="The URL or text encoded in the QR code.")
    background = ImageChooserBlock(
        required=False,
        help_text="This QR Code background should be 1200x675, expecting a 300px square directly in the center. "
        "This image will be cropped to a square on mobile.",
    )

    class Meta:
        label = "QR Code"
        label_format = "QR Code - {data}"
        template = "cms/blocks/qr-code.html"


class MediaBlock(blocks.StreamBlock):
    image = ImageVariantsBlock(required=False)
    video = VideoBlock(required=False)
    animation = AnimationBlock(required=False)
    qr_code = QRCodeBlock(required=False)

    class Meta:
        label = "Media"
        template = "cms/blocks/media.html"


class SmartWindowInstructionsBlock(blocks.StructBlock):
    pre_typewriter_text = blocks.CharBlock(default="Prompt to try", required=False)
    typewriter_text = blocks.CharBlock(required=False, help_text="This text will animated as if being typed, mimicing a Smart Window prompt.")
    instructions = RichTextBlock(features=HEADING_TEXT_FEATURES, label="Instructions")

    class Meta:
        label = "Smart Window Instructions"
        label_format = "Smart Window Instructions - {instructions}"
        template = "cms/blocks/smart-window-instructions.html"


class MediaContentSettings(blocks.StructBlock):
    media_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Media After",
        inline_form=True,
        help_text="Place media after text content on desktop",
    )
    narrow = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Narrow Layout",
        inline_form=True,
        help_text="Narrow the media element",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Media After: {media_after}"
        form_classname = "compact-form struct-block"


def MediaContentBlock(allow_uitour=False, is_2026=False, *args, **kwargs):
    """Factory function to create MediaContentBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
        is_2026: If True, uses the 2026 version of the block.
    """
    tag_block = TagBlock2026() if is_2026 else TagBlock()

    class _MediaContentBlock(blocks.StructBlock):
        settings = MediaContentSettings()
        media = MediaBlock(max_num=1)
        eyebrow = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        tags = blocks.ListBlock(tag_block, min_num=0, max_num=3, default=[])
        content = blocks.StreamBlock(
            [
                ("rich_text", RichTextBlock(features=HEADING_TEXT_FEATURES)),
                ("smart_window_instructions", SmartWindowInstructionsBlock()),
            ]
        )
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            label = "Media + Content"
            label_format = "{headline}"
            template = "cms/blocks/media-content.html"

    return _MediaContentBlock(*args, **kwargs)


class IconListItemBlock(blocks.StructBlock):
    icon = IconChoiceBlock()
    text = RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        icon = "list-ul"
        label = "Icon List Item"
        label_format = "{text}"


class IconListWithImageBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    list_items = blocks.ListBlock(IconListItemBlock())

    class Meta:
        label = "Icon List with Image"
        label_format = "Icon List with Image"
        template = "cms/blocks/icon-list-with-image.html"


# Cards


class BaseCardSettings(blocks.StructBlock):
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Expand the link click area to the whole card",
    )
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Expand Link: {expand_link} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


def StickerCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create StickerCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _StickerCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        image = ImageVariantsBlock()
        tags = blocks.ListBlock(TagBlock(), min_num=0, max_num=3, default=[])
        superheading = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            label = "Sticker Card"
            label_format = "{headline}"
            template = "cms/blocks/sticker-card.html"

    return _StickerCardBlock(*args, **kwargs)


def FilledCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create FilledCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _FilledCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        tags = blocks.ListBlock(TagBlock(), min_num=1, max_num=3)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/filled-card.html"
            label = "Filled Card"
            label_format = "Filled Card - {headline}"

    return _FilledCardBlock(*args, **kwargs)


def IconCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create IconCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IconCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        icon = IconChoiceBlock(inline_form=True)
        tags = blocks.ListBlock(TagBlock(), min_num=0, max_num=3, default=[])
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/icon-card.html"
            label = "Icon Card"
            label_format = "Icon Card - {headline}"

    return _IconCardBlock(*args, **kwargs)


class IllustrationCardSettings(BaseCardSettings):
    image_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Image After",
        inline_form=True,
        help_text="Place image after text content",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Expand Link: {expand_link} - Image After: {image_after}"
        form_classname = "compact-form struct-block"


def IllustrationCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create IllustrationCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IllustrationCardBlock(blocks.StructBlock):
        settings = IllustrationCardSettings()
        image = ImageVariantsBlock()
        tags = blocks.ListBlock(TagBlock(), min_num=0, max_num=3, default=[])
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/illustration-card.html"
            label = "Illustration Card"
            label_format = "{headline}"

    return _IllustrationCardBlock(*args, **kwargs)


def StepCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create StepCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _StepCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        image = ImageChooserBlock()
        dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
        tags = blocks.ListBlock(TagBlock(), min_num=0, max_num=3, default=[])
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/step-card.html"
            label = "Step Card"
            label_format = "{headline}"

    return _StepCardBlock(*args, **kwargs)


def CardsListBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create CardsListBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _CardsListBlock(blocks.StructBlock):
        cards = blocks.StreamBlock(
            [
                ("sticker_card", StickerCardBlock(allow_uitour=allow_uitour)),
                ("filled_card", FilledCardBlock(allow_uitour=allow_uitour)),
                ("icon_card", IconCardBlock(allow_uitour=allow_uitour)),
                ("illustration_card", IllustrationCardBlock(allow_uitour=allow_uitour)),
            ]
        )

        class Meta:
            template = "cms/blocks/cards-list.html"
            label = "Cards List"
            label_format = "Cards List"

    return _CardsListBlock(*args, **kwargs)


def StepCardListBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create StepCardListBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _StepCardListBlock(blocks.StructBlock):
        cards = blocks.ListBlock(StepCardBlock(allow_uitour=allow_uitour))

        class Meta:
            template = "cms/blocks/cards-list.html"
            label = "Step Cards List"
            label_format = "Step Cards List"

    return _StepCardListBlock(*args, **kwargs)


# 2026 Cards


class StepCardSettings(blocks.StructBlock):
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Expand the link click area to the whole card",
    )


def StepCardBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create StepCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _StepCardBlock(blocks.StructBlock):
        settings = StepCardSettings()
        image = ImageVariantsBlock()
        eyebrow = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=[BUTTON_LINK],
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/step-card-2026.html"
            label = "Step Card"
            label_format = "{headline}"

    return _StepCardBlock(*args, **kwargs)


def StepCardListBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create StepCardListBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _StepCardListBlock(blocks.StructBlock):
        cards = blocks.ListBlock(StepCardBlock2026(allow_uitour=allow_uitour))

        class Meta:
            template = "cms/blocks/step-cards-list-2026.html"
            label = "Step Cards List"
            label_format = "Step Cards List"

    return _StepCardListBlock(*args, **kwargs)


def IconCardBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create IconCardBlock2026 with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IconCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        icon = IconChoiceBlock(inline_form=True)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/icon-card-2026.html"
            label = "Icon Card"
            label_format = "Icon Card - {headline}"

    return _IconCardBlock(*args, **kwargs)


def StickerCardBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create StickerCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                        If False, only allows regular buttons.
    """

    class _StickerCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        image = ImageVariantsBlock()
        superheading = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            label = "Sticker Card"
            label_format = "{headline}"
            template = "cms/blocks/sticker-card-2026.html"

    return _StickerCardBlock(*args, **kwargs)


def IllustrationCard2026Block(allow_uitour=False, *args, **kwargs):
    """Factory function to create IllustrationCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IllustrationCardBlock(blocks.StructBlock):
        settings = IllustrationCardSettings()
        media = MediaBlock()
        eyebrow = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=[BUTTON_LINK],
            min_num=0,
            max_num=1,
            required=False,
        )

        class Meta:
            template = "cms/blocks/illustration-card-2026.html"
            label = "Illustration Card"
            label_format = "{headline}"

    return _IllustrationCardBlock(*args, **kwargs)


def OutlinedCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create OutlinedCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _OutlinedCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        sticker = ImageVariantsBlock(required=False)
        headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=3,
            required=False,
        )

        class Meta:
            template = "cms/blocks/outlined-card.html"
            label = "Outlined Card"
            label_format = "Outlined Card - {headline}"

    return _OutlinedCardBlock(*args, **kwargs)


def TestimonialCardBlock(*args, **kwargs):
    class _TestimonialCardSettings(blocks.StructBlock):
        show_to = ConditionalDisplayBlock(
            label="Show To",
            help_text="Control which users can see this content block",
        )

        class Meta:
            icon = "cog"
            collapsed = True
            label = "Settings"
            form_classname = "compact-form struct-block"

    class _TestimonialCardBlock(blocks.StructBlock):
        settings = _TestimonialCardSettings()
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        attribution = RichTextBlock(features=HEADING_TEXT_FEATURES)
        attribution_role = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        attribution_image = ImageVariantsBlock(required=False)

        class Meta:
            template = "cms/blocks/testimonial-card.html"
            label = "Testimonial Card"
            label_format = "Testimonial - {attribution}"

    return _TestimonialCardBlock(*args, **kwargs)


def CardsListBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create CardsListBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _CardsListSettings(blocks.StructBlock):
        scroll = blocks.BooleanBlock(
            required=False,
            default=False,
            help_text="Display all cards in a single scrolling row",
        )

        class Meta:
            icon = "cog"
            collapsed = True
            label = "Settings"
            form_classname = "compact-form struct-block"

    class _CardsListBlock(blocks.StructBlock):
        settings = _CardsListSettings()
        cards = blocks.StreamBlock(
            [
                ("sticker_card", StickerCardBlock2026(allow_uitour=allow_uitour)),
                ("illustration_card", IllustrationCard2026Block(allow_uitour=allow_uitour)),
                ("outlined_card", OutlinedCardBlock(allow_uitour=allow_uitour)),
                ("icon_card", IconCardBlock2026(allow_uitour=allow_uitour)),
                ("testimonial_card", TestimonialCardBlock()),
            ]
        )

        class Meta:
            template = "cms/blocks/cards-list.html"
            label = "Cards List"
            label_format = "Cards List"

    return _CardsListBlock(*args, **kwargs)


class CardLineItemBlock(blocks.StructBlock):
    superheading = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = RichTextBlock(features=HEADING_TEXT_FEATURES)
    buttons = MixedButtonsBlock(
        button_types=get_button_types(allow_uitour=False),
        themes=BUTTON_THEMES_2026,
        min_num=0,
        max_num=2,
        required=False,
    )


class LineCardsBlock(blocks.StructBlock):
    cards = blocks.ListBlock(CardLineItemBlock())

    class Meta:
        template = "cms/blocks/line-cards.html"
        label = "Line Cards"
        label_format = "Line Cards"


# Article Cards


class BaseArticleOverridesBlock(blocks.StructBlock):
    image = ImageChooserBlock(
        required=False,
        help_text="Optional custom image to override the article's featured image.",
    )
    sticker = ImageChooserBlock(
        required=False,
        help_text="Optional custom sticker image to override the article's sticker.",
    )
    icon = IconChoiceBlock(required=False, inline_form=True, help_text="Optional icon to display on icon cards.")
    superheading = blocks.CharBlock(
        required=False,
        help_text="Optional custom superheading to override the article's original tag. Only available for illustration and sticker cards.",
    )
    title = RichTextBlock(
        features=HEADING_TEXT_FEATURES,
        required=False,
        help_text="Optional custom title to override the article's original title.",
    )
    description = RichTextBlock(
        features=HEADING_TEXT_FEATURES,
        required=False,
        help_text="Optional custom description to override the article's original description.",
    )
    link_label = blocks.CharBlock(
        required=False,
        help_text="Optional custom link label to override the article's original call to action text.",
    )
    link = LinkBlock(
        required=False,
        verbose_name="Link override",
        help_text="Optional custom link to override the article's original call to action link. Note: This field is meant to be temporary.",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Overrides"


class BaseArticleValue(blocks.StructValue):
    def get_article(self) -> ArticleDetailPage | ArticleThemePage:
        return self["article"].specific.localized

    def get_title(self) -> str:
        from springfield.cms.templatetags.cms_tags import remove_p_tag

        overrides = self.get("overrides", {})
        if title := overrides.get("title"):
            return remove_p_tag(richtext(title))
        article_page = self.get_article()
        return article_page.title if article_page else ""

    def get_description(self) -> str:
        from springfield.cms.templatetags.cms_tags import remove_p_tag

        overrides = self.get("overrides", {})
        if description := overrides.get("description"):
            return remove_p_tag(richtext(description))
        article_page = self.get_article()
        if article_page:
            article_page = article_page.specific
            if hasattr(article_page, "description") and article_page.description:
                return remove_p_tag(richtext(article_page.description))
        return ""

    def get_superheading(self) -> str:
        overrides = self.get("overrides", {})
        if superheading := overrides.get("superheading"):
            return superheading
        article_page = self.get_article()
        if article_page:
            article_page = article_page.specific
            if hasattr(article_page, "get_tag") and (tag := article_page.get_tag()):
                return tag.name
        return ""

    def get_link_label(self) -> str:
        overrides = self.get("overrides", {})
        if link_label := overrides.get("link_label"):
            return link_label
        article_page = self.get_article()
        if article_page:
            article_page = article_page.specific
            if hasattr(article_page, "link_text") and article_page.link_text:
                return article_page.link_text
        return ftl("ui-learn-more", ftl_files=["ui"])

    def get_featured_image(self) -> SpringfieldImage | None:
        overrides = self.get("overrides", {})
        if image := overrides.get("image"):
            return image
        article_page = self.get_article()
        if article_page:
            article_page = article_page.specific
            if hasattr(article_page, "featured_image"):
                return article_page.featured_image
        return None

    def get_sticker(self) -> SpringfieldImage | None:
        overrides = self.get("overrides", {})
        if sticker := overrides.get("sticker"):
            return sticker
        article_page = self.get_article()
        if article_page:
            article_page = article_page.specific
            if hasattr(article_page, "sticker"):
                return article_page.sticker
        return None

    def get_icon(self) -> str:
        overrides = self.get("overrides", {})
        if icon := overrides.get("icon"):
            return icon
        article_page = self.get_article()
        if article_page:
            article_page = article_page.specific
            if hasattr(article_page, "icon") and article_page.icon:
                return article_page.icon
        return "globe"

    def get_link_url(self) -> str:
        overrides = self.get("overrides", {})
        if link := overrides.get("link"):
            url = link.get_url()
            if url:
                return url

        article_page = self.get_article()
        return article_page.get_active_locale_url() if article_page else ""


class ArticleBlock(blocks.StructBlock):
    article = blocks.PageChooserBlock(target_model=("cms.ArticleDetailPage", "cms.ArticleThemePage"))
    overrides = BaseArticleOverridesBlock(required=False)

    class Meta:
        label = "Article"
        label_format = "{article}"
        form_classname = "compact-form struct-block"
        value_class = BaseArticleValue


class ArticlesListSettings(blocks.StructBlock):
    card_type = blocks.ChoiceBlock(
        choices=[
            ("sticker_card", "Sticker Card"),
            ("illustration_card", "Illustration Card"),
            ("icon_card", "Icon Card"),
            ("sticker_row", "Sticker Row"),
        ],
        default="sticker_card",
        label="Card Type",
        inline_form=True,
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Card Type: {card_type}"
        form_classname = "compact-form struct-block"


class ArticleCardsListBlock(blocks.StructBlock):
    settings = ArticlesListSettings()
    cards = blocks.ListBlock(ArticleBlock())

    class Meta:
        template = "cms/blocks/article-cards-list.html"
        label = "Article Cards List"
        label_format = "Article Cards List"


class RelatedArticleBlock(blocks.StructBlock):
    article = blocks.PageChooserBlock(target_model=("cms.ArticleDetailPage", "cms.ArticleThemePage"))
    overrides = BaseArticleOverridesBlock(required=False)
    tags = blocks.ListBlock(TagBlock(), min_num=0, max_num=3, default=[])

    class Meta:
        label = "Related Article"
        label_format = "{article}"
        form_classname = "compact-form struct-block"
        value_class = BaseArticleValue
        template = "cms/blocks/related-article-card.html"


class RelatedArticlesListBlock(blocks.StructBlock):
    cards = blocks.ListBlock(RelatedArticleBlock())

    class Meta:
        template = "cms/blocks/related-articles-list.html"
        label = "Related Articles List"
        label_format = "Related Articles List"


# Section blocks


class InlineNotificationSettings(blocks.StructBlock):
    icon = IconChoiceBlock(required=False, inline_form=True)
    color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("black", "Black"),
            ("blue", "Blue"),
            ("purple", "Purple"),
            ("orange", "Orange"),
            ("yellow", "Yellow"),
        ],
        required=False,
        inline_form=True,
    )
    inverted = blocks.BooleanBlock(
        required=False,
        default=False,
        inline_form=True,
        help_text="Inverted colors on icon background",
    )
    closable = blocks.BooleanBlock(
        required=False,
        default=False,
        inline_form=True,
        help_text="Show close button",
    )
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Color: {color} - Icon: {icon} - Inverted: {inverted} - Closable: {closable} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


class InlineNotificationBlock(blocks.StructBlock):
    settings = InlineNotificationSettings()
    message = RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/inline-notification.html"
        label = "Inline Notification"
        label_format = "{message}"
        form_classname = "compact-form struct-block"


class NotificationSettings(blocks.StructBlock):
    icon = IconChoiceBlock(required=False, inline_form=True)
    color = blocks.ChoiceBlock(
        choices=[
            ("purple", "Purple"),
            ("green", "Green"),
            ("orange", "Orange"),
            ("red", "Red"),
        ],
        required=False,
        inline_form=True,
    )
    stacked = blocks.BooleanBlock(
        required=False,
        default=False,
        inline_form=True,
        help_text="Stack icon above message",
    )
    closable = blocks.BooleanBlock(
        required=False,
        default=False,
        inline_form=True,
        help_text="Show close button. Not available for stacked layout.",
    )
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Color: {color} - Icon: {icon} - Stacked: {stacked} - Closable: {closable} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


class NotificationBlock(blocks.StructBlock):
    settings = NotificationSettings()
    headline = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    message = RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/notification.html"
        label = "Notification"
        label_format = "{message}"
        form_classname = "compact-form struct-block"


class IntroBlockSettings(blocks.StructBlock):
    media_position = blocks.ChoiceBlock(
        choices=(("after", "After"), ("before", "Before"), ("right", "Right"), ("left", "Left")),
        default="after",
        label="Media Position",
        inline_form=True,
    )
    anchor_id = blocks.CharBlock(
        required=False,
        help_text="Add an ID to make this section linkable from navigation (e.g., 'overview', 'features')",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Media Position: {media_position} - Anchor ID: {anchor_id}..."
        form_classname = "compact-form struct-block"


def IntroBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create IntroBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IntroBlock(blocks.StructBlock):
        settings = IntroBlockSettings()
        media = MediaBlock(max_num=1, min_num=0, required=False)
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            template = "cms/blocks/sections/intro.html"
            label = "Intro"
            label_format = "{heading}"

    return _IntroBlock(*args, **kwargs)


class IntroBlockSettings2026(blocks.StructBlock):
    layout = blocks.ChoiceBlock(
        choices=(("vertical", "Vertical"), ("right", "Media Right"), ("left", "Media Left")),
        default="vertical",
        label="Layout",
        inline_form=True,
    )
    full_width = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Full Width",
        inline_form=True,
        help_text="Renders content using all available horizontal space.",
    )
    slim = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Slim Layout",
        inline_form=True,
        help_text="Use a more compact layout with reduced spacing.",
    )
    anchor_id = blocks.CharBlock(
        required=False,
        help_text="Add an ID to make this section linkable from navigation (e.g., 'overview', 'features')",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Layout: {layout} - Slim: {slim} - Anchor ID: {anchor_id}"
        form_classname = "compact-form struct-block"


def IntroBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create IntroBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IntroBlock(blocks.StructBlock):
        settings = IntroBlockSettings2026()
        media = MediaBlock(max_num=1, min_num=0, required=False)
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=3,
            required=False,
        )

        class Meta:
            template = "cms/blocks/sections/intro-2026.html"
            label = "Intro"
            label_format = "{heading}"

    return _IntroBlock(*args, **kwargs)


class SectionBlockSettings(blocks.StructBlock):
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )
    anchor_id = blocks.CharBlock(
        required=False,
        help_text="Add an ID to make this section linkable from navigation (e.g., 'overview', 'features')",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Anchor ID: {anchor_id} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


def SectionBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create SectionBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _SectionBlock(blocks.StructBlock):
        settings = SectionBlockSettings()
        heading = HeadingBlock()
        content = blocks.StreamBlock(
            [
                ("media_content", MediaContentBlock(allow_uitour=allow_uitour)),
                ("cards_list", CardsListBlock(allow_uitour=allow_uitour)),
                ("step_cards", StepCardListBlock(allow_uitour=allow_uitour)),
            ]
        )
        cta = blocks.ListBlock(CTABlock(), min_num=0, max_num=1, default=[], label="Call to Action")

        class Meta:
            template = "cms/blocks/sections/section.html"
            label = "Section"
            label_format = "{heading}"

    return _SectionBlock(*args, **kwargs)


def SectionBlock2026(allow_uitour=False, require_heading=True, *args, **kwargs):
    """Factory function to create SectionBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _SectionBlock(blocks.StructBlock):
        settings = SectionBlockSettings()
        heading = HeadingBlock(required=require_heading)
        content = blocks.StreamBlock(
            [
                ("media_content", MediaContentBlock(allow_uitour=allow_uitour, is_2026=True)),
                ("cards_list", CardsListBlock2026(allow_uitour=allow_uitour)),
                ("step_cards", StepCardListBlock2026(allow_uitour=allow_uitour)),
                ("article_cards_list", ArticleCardsListBlock()),
                ("icon_list_with_image", IconListWithImageBlock()),
                ("banner", BannerBlock(allow_uitour=allow_uitour)),
                ("kit_banner", KitBannerBlock(allow_uitour=allow_uitour)),
                ("line_cards", LineCardsBlock(allow_uitour=allow_uitour)),
            ],
            required=False,
        )
        cta = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=1,
            required=False,
            label="Call to Action",
        )

        class Meta:
            template = "cms/blocks/sections/section.html"
            label = "Section"
            label_format = "{heading}"

    return _SectionBlock(*args, **kwargs)


# Topic list


def TopicBlock(allow_uitour=False, *args, **kwargs):
    class _TopicBlock(blocks.StructBlock):
        short_title = blocks.CharBlock(
            label="Short Title",
            help_text="Text to be used on the sidebar link.",
        )
        anchor_id = blocks.CharBlock(
            help_text="Add an ID to make this section linkable from the sidebar (e.g., 'privacy-online', 'data-control')",
        )
        image = ImageChooserBlock(
            label="Image",
            help_text="Image shown at the top of the topic heading.",
        )
        heading = HeadingBlock()
        content = RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=3,
            required=False,
        )

        class Meta:
            template = "cms/blocks/topic.html"
            label = "Topic"
            label_format = "{heading}"

    return _TopicBlock(*args, **kwargs)


def TopicListBlock(allow_uitour=False, *args, **kwargs):
    class _TopicListBlock(blocks.StructBlock):
        topics = blocks.ListBlock(TopicBlock(allow_uitour=allow_uitour), min=1)

        class Meta:
            template = "cms/blocks/sections/topic-list.html"
            label = "Topic List"
            label_format = "{heading}"

    return _TopicListBlock(*args, **kwargs)


# Banners


class SubscriptionBlock(blocks.StructBlock):
    heading = HeadingBlock()

    class Meta:
        template = "cms/blocks/sections/subscription.html"
        label = "Subscription"
        label_format = "Subscription - {heading}"
        form_classname = "compact-form struct-block"


class BannerSettings(blocks.StructBlock):
    theme = blocks.ChoiceBlock(
        (
            ("default", "Default"),
            ("outlined", "Outlined"),
            ("purple", "Purple"),
            ("dark-purple", "Dark Purple"),
        ),
        default="default",
        inline_form=True,
    )
    media_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Media After",
        inline_form=True,
        help_text="Place media after text content on desktop.",
    )
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )
    anchor_id = blocks.CharBlock(
        required=False,
        help_text="Add an ID to make this section linkable from navigation (e.g., 'overview', 'features')",
    )
    slim = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Slim Layout",
        inline_form=True,
        help_text="Use a more compact layout with reduced spacing and a smaller headline.",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Theme: {theme} - Media After: {media_after} - Anchor ID: {anchor_id} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


def BannerBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create BannerBlock with appropriate button types."""

    class _BannerBlock(blocks.StructBlock):
        settings = BannerSettings()
        media = MediaBlock(max_num=1, min_num=0, required=False)
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=3,
            required=False,
        )

        class Meta:
            template = "cms/blocks/sections/banner.html"
            label = "Banner"
            label_format = "{heading}"

    return _BannerBlock(*args, **kwargs)


class KitBannerSettings(blocks.StructBlock):
    theme = blocks.ChoiceBlock(
        (
            ("filled", "No Kit Image"),
            ("filled-small", "With Small Curious Kit"),
            ("filled-large", "With Large Curious Kit"),
            ("filled-face", "With Sitting Kit"),
            ("filled-tail", "With Kit Tail"),
            ("curious-animation", "With Curious Kit Animation"),
        ),
        default="filled",
        inline_form=True,
    )
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )
    anchor_id = blocks.CharBlock(
        required=False,
        help_text="Add an ID to make this section linkable from navigation (e.g., 'overview', 'features')",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Theme: {theme} - Anchor ID: {anchor_id} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


def KitBannerBlock(allow_uitour=False, button_themes=BUTTON_THEMES_2025, *args, **kwargs):
    """Factory function to create KitBannerBlock with appropriate button types."""

    class _KitBannerBlock(blocks.StructBlock):
        settings = KitBannerSettings()
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=button_themes,
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            template = "cms/blocks/sections/kit-banner.html"
            label = "Kit Banner"
            label_format = "{heading}"

    return _KitBannerBlock(*args, **kwargs)


# Homepage


class KitBlockSettings(blocks.StructBlock):
    slim = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Slim Layout",
        inline_form=True,
        help_text="Use a more compact layout with reduced spacing.",
    )


def KitIntroBlock(allow_uitour=False, *args, **kwargs):
    class _KitIntroBlock(blocks.StructBlock):
        settings = KitBlockSettings()
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            allow_uitour=allow_uitour,
            button_types=get_button_types(),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            template = "cms/blocks/kit-intro.html"
            label = "Kit Intro"
            label_format = "{heading}"

    return _KitIntroBlock(*args, **kwargs)


class CarouselSlide(blocks.StructBlock):
    headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
    image = ImageVariantsBlock()


class CarouselSettings(blocks.StructBlock):
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Show to: {show_to}"
        form_classname = "compact-form struct-block"


class CarouselBlock(blocks.StructBlock):
    settings = CarouselSettings()
    heading = HeadingBlock()
    buttons = MixedButtonsBlock(
        button_types=get_button_types(allow_uitour=False),
        min_num=0,
        max_num=2,
        required=False,
    )
    slides = blocks.ListBlock(CarouselSlide(), min_num=2, max_num=5)

    class Meta:
        template = "cms/blocks/sections/home-carousel.html"
        label = "Carousel"
        label_format = "{heading}"


class SlidingCarouselItemBlock(blocks.StructBlock):
    heading = HeadingBlock(all_required=True)
    media = MediaBlock(max_num=1)

    class Meta:
        label = "Slide"
        label_format = "{heading}"


class SlidingCarouselBlock(blocks.StructBlock):
    settings = CarouselSettings()
    slides = blocks.ListBlock(SlidingCarouselItemBlock(), min_num=2, max_num=6)

    class Meta:
        template = "cms/blocks/sliding-carousel.html"
        label = "Sliding Carousel"
        label_format = "Sliding Carousel"


class ShowcaseSettings(blocks.StructBlock):
    layout = blocks.ChoiceBlock(
        choices=[
            ("default", "Default"),
            ("expanded", "Expanded"),
            ("full", "Full Width"),
        ],
        default="default",
        inline_form=True,
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Layout: {layout}"
        form_classname = "compact-form struct-block"


class ShowcaseBlock(blocks.StructBlock):
    settings = ShowcaseSettings()
    headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
    media = MediaBlock(max_num=1)
    caption_title = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    caption_description = RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/sections/showcase.html"
        label = "Showcase"
        label_format = "{headline}"


class CardGalleryCard(blocks.StructBlock):
    icon = IconChoiceBlock()
    superheading = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
    description = RichTextBlock(features=EXPANDED_TEXT_FEATURES)
    buttons = MixedButtonsBlock(
        button_types=get_button_types(),
        themes=BUTTON_THEMES_2026,
        min_num=0,
        max_num=1,
        required=False,
    )
    image = ImageVariantsBlock()


class CardGalleryCallout(blocks.StructBlock):
    superheading = RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = RichTextBlock(features=HEADING_TEXT_FEATURES)
    description = RichTextBlock(features=EXPANDED_TEXT_FEATURES)


class CardGalleryBlock(blocks.StructBlock):
    heading = HeadingBlock()
    main_card = CardGalleryCard()
    secondary_card = CardGalleryCard()
    callout_card = CardGalleryCallout()
    cta = MixedButtonsBlock(
        button_types=get_button_types(),
        themes=BUTTON_THEMES_2026,
        min_num=0,
        max_num=1,
        required=False,
    )

    class Meta:
        template = "cms/blocks/sections/card-gallery.html"
        label = "Card Gallery"
        label_format = "{heading}"


class HomeKitBannerSettings(blocks.StructBlock):
    show_to = ConditionalDisplayBlock(
        label="Show To",
        help_text="Control which users can see this content block",
    )
    anchor_id = blocks.CharBlock(
        required=False,
        help_text="Add an ID to make this section linkable from navigation (e.g., 'overview', 'features')",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Anchor ID: {anchor_id} - Show to: {show_to}"
        form_classname = "compact-form struct-block"


def HomeKitBannerBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create KitBannerBlock with appropriate button types."""

    class _HomeKitBannerBlock(blocks.StructBlock):
        settings = HomeKitBannerSettings()
        heading = HeadingBlock()
        qr_code = blocks.CharBlock(required=False, help_text="QR Code Data or URL.")
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            template = "cms/blocks/sections/home-kit-banner.html"
            label = "Kit Banner"
            label_format = "{heading}"

    return _HomeKitBannerBlock(*args, **kwargs)


# Mobile


class MobileStoreQRCodeBlock(blocks.StructBlock):
    """Block for displaying mobile app store buttons with a QR code."""

    heading = HeadingBlock()
    qr_code_data = blocks.CharBlock(
        label="QR Code Data",
        help_text="The URL or text encoded in the QR code.",
    )
    mobile_image = ImageChooserBlock(
        label="Mobile Image",
        help_text="Image shown on mobile instead of the QR code.",
    )

    class Meta:
        template = "cms/blocks/sections/mobile-store-qr-code.html"
        label = "Mobile Store Button / QR Code"
        label_format = "{heading}"


# Thanks Page


class DownloadSupportBlock(blocks.StaticBlock):
    class Meta:
        template = "cms/blocks/download-support.html"
        label = "Download Support Message"
