# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.core.exceptions import ValidationError

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail_link_block.blocks import LinkBlock
from wagtail_thumbnail_choice_block import ThumbnailChoiceBlock

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
    ("add-circle-fill", "Add Circle Fill"),
    ("add-text", "Add Text"),
    ("add-user", "Add User"),
    ("ai", "AI"),
    ("alert", "Alert"),
    ("all-tabs", "All Tabs"),
    ("android", "Android"),
    ("app-menu", "App Menu"),
    ("app-menu-space", "App Menu Space"),
    ("apple", "Apple"),
    ("applied-policy", "Applied Policy"),
    ("arrow-clockwise", "Arrow Clockwise"),
    ("arrow-counterclockwise", "Arrow Counterclockwise"),
    ("arrow-down", "Arrow Down"),
    ("arrow-down-line", "Arrow Down Line"),
    ("arrow-forward", "Arrow Forward"),
    ("arrow-left", "Arrow Left"),
    ("arrow-right", "Arrow Right"),
    ("arrow-trending", "Arrow Trending"),
    ("arrow-up", "Arrow Up"),
    ("audio", "Audio"),
    ("audio-muted", "Audio Muted"),
    ("authenticated-user", "Authenticated User"),
    ("auto-play", "Auto Play"),
    ("auto-play-off", "Auto Play Off"),
    ("avatar-signed-in-fill", "Avatar Signed In Fill"),
    ("avatar-signed-in-fill-custom-initial", "Avatar Signed In Fill Custom Initial"),
    ("avatar-signed-out", "Avatar Signed Out"),
    ("back", "Back"),
    ("barbell", "Barbell"),
    ("bell", "Bell"),
    ("bike", "Bike"),
    ("blocked-popup", "Blocked Popup"),
    ("blog", "Blog"),
    ("book", "Book"),
    ("bookmark", "Bookmark"),
    ("bookmark-fill", "Bookmark Fill"),
    ("bookmarks-tray", "Bookmarks Tray"),
    ("briefcase", "Briefcase"),
    ("calendar", "Calendar"),
    ("camera", "Camera"),
    ("canvas", "Canvas"),
    ("canvas-off", "Canvas Off"),
    ("caret-down", "Caret Down"),
    ("caret-up", "Caret Up"),
    ("chat", "Chat"),
    ("check", "Check"),
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
    ("cloud", "Cloud"),
    ("color-picker", "Color Picker"),
    ("comment", "Comment"),
    ("competitiveness", "Competitiveness"),
    ("copy", "Copy"),
    ("craft", "Craft"),
    ("critical", "Critical"),
    ("critical-fill", "Critical Fill"),
    ("cryptominer", "Cryptominer"),
    ("cryptominer-off", "Cryptominer No"),
    ("current-view", "Current View"),
    ("cursor-arrow", "Cursor Arrow"),
    ("dashboard", "Dashboard"),
    ("data-clearance", "Data Clearance"),
    ("data-insights", "Data Insights"),
    ("data-pie", "Data Pie"),
    ("delete", "Delete"),
    ("design", "Design"),
    ("device-mobile", "Device Mobile"),
    ("diamond", "Diamond"),
    ("download", "Download"),
    ("downloaded-file", "Downloaded File"),
    ("downloads", "Downloads"),
    ("earth", "Earth"),
    ("edit", "Edit"),
    ("edit-active", "Edit Active"),
    ("edit-squiggle", "Edit Squiggle"),
    ("edit-write", "Edit Write"),
    ("email", "Email"),
    ("email-mask", "Email Mask"),
    ("email-shield", "Email Shield"),
    ("error", "Error"),
    ("error-fill", "Error Fill"),
    ("even-spreads", "Even Spreads"),
    ("event", "Event"),
    ("export-data", "Export Data"),
    ("extension", "Extension"),
    ("extension-critical", "Extension Critical"),
    ("extension-fill", "Extension Fill"),
    ("extension-warning", "Extension Warning"),
    ("external-link", "External Link"),
    ("eye-closed", "Eye Closed"),
    ("eye-open", "Eye Open"),
    ("find-in-page", "Find In Page"),
    ("fingerprinter", "Fingerprinter"),
    ("fingerprinter-off", "Fingerprinter Off"),
    ("firefox-bridge", "Firefox Bridge"),
    ("firefox-browser-bridge", "Firefox Browser Bridge"),
    ("flower", "Flower"),
    ("folder", "Folder"),
    ("folder-arrow-down", "Folder Arrow Down"),
    ("folder-fill", "Folder Fill"),
    ("folder-plus", "Folder Plus"),
    ("footprints", "Footprints"),
    ("footprints-off", "Footprints Off"),
    ("forward", "Forward"),
    ("forward-small", "Forward Small"),
    ("fullscreen-disabled", "Fullscreen Disabled"),
    ("fullscreen-exit", "Fullscreen Exit"),
    ("fullscreen-expand", "Fullscreen Expand"),
    ("fx-view", "FX View"),
    ("gear", "Gear"),
    ("gift", "Gift"),
    ("globe", "Globe"),
    ("globe-slash", "Globe Slash"),
    ("hammer", "Hammer"),
    ("hand", "Hand"),
    ("hashtag", "Hashtag"),
    ("headphone", "Headphone"),
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
    ("information", "Information"),
    ("information-fill", "Information Fill"),
    ("language", "Language"),
    ("layer", "Layer"),
    ("leaf", "Leaf"),
    ("library", "Library"),
    ("lightbulb", "Lightbulb"),
    ("line-arrow-up", "Line Arrow Up"),
    ("list", "List"),
    ("list-arrow-left", "List Arrow Left"),
    ("location", "Location"),
    ("location-off", "Location Off"),
    ("lock", "Lock"),
    ("lock-document", "Lock Document"),
    ("lock-insecure", "Lock Insecure"),
    ("lock-warning", "Lock Warning"),
    ("login", "Login"),
    ("makeup", "Makeup"),
    ("megaphone", "Megaphone"),
    ("menu", "Menu"),
    ("mic", "Microphone"),
    ("mic-off", "Microphone Off"),
    ("midi", "Midi"),
    ("minus", "Minus"),
    ("mobile-phone", "Mobile Phone"),
    ("musical-note", "Musical Note"),
    ("newsfeed", "Newsfeed"),
    ("no-spreads", "No Spreads"),
    ("notifications", "Notifications"),
    ("notifications-off", "Notifications Off"),
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
    ("pause", "Pause"),
    ("pause-fill", "Pause Fill"),
    ("paw-print", "Paw Print"),
    ("payment-methods", "Payment Methods"),
    ("permission", "Permission"),
    ("picture-in-picture-closed", "Picture In Picture Closed"),
    ("picture-in-picture-open", "Picture In Picture Open"),
    ("pin", "Pin"),
    ("pin-fill", "Pin Fill"),
    ("plane", "Plane"),
    ("play", "Play"),
    ("play-fill", "Play Fill"),
    ("playback-forward", "Playback Forward"),
    ("playback-rewind", "Playback Rewind"),
    ("plugin", "Plugin"),
    ("plugin-off", "Plugin Off"),
    ("plus", "Plus"),
    ("pocket", "Pocket"),
    ("pocket-fill", "Pocket Fill"),
    ("policy", "Policy"),
    ("popup-subitem", "Popup Subitem"),
    ("presentation-mode", "Presentation Mode"),
    ("price", "Price"),
    ("print", "Print"),
    ("private-mode-circle-fill", "Private Mode Circle Fill"),
    ("private-mode-fill", "Private Mode Fill"),
    ("quality", "Quality"),
    ("quote", "Quote"),
    ("read", "Read"),
    ("reader-mode", "Reader Mode"),
    ("remove-user", "Remove User"),
    ("report", "Report"),
    ("screenshare", "Screenshare"),
    ("screenshare-off", "Screenshare Off"),
    ("search-in-circle", "Search In Circle"),
    ("search-in-circle-right", "Search In Circle Right"),
    ("search", "Search"),
    ("settings", "Settings"),
    ("share-mac-os", "Share Mac"),
    ("share-win-os", "Share Windows"),
    ("shield", "Shield"),
    ("shipping", "Shipping"),
    ("shopping", "Shopping"),
    ("shopping-cart", "Shopping Cart"),
    ("show-password", "Show Password"),
    ("show-password-off", "Show Password Off"),
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
    ("social-tracker", "Social Tracker"),
    ("social-tracker-off", "Social Tracker Off"),
    ("sort", "Sort"),
    ("sound-off", "Sound Off"),
    ("sound-on", "Sound On"),
    ("sparkle-single", "Sparkle Single"),
    ("sparkles", "Sparkles"),
    ("split-view", "Split View"),
    ("split-view-left", "Split View Left"),
    ("split-view-right", "Split View Right"),
    ("star", "Star"),
    ("storage", "Storage"),
    ("storage-off", "Storage Off"),
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
    ("thumbs-up", "Thumbs Up"),
    ("toggle-off", "Toggle Off"),
    ("toggle-on", "Toggle On"),
    ("top-sites", "Top Sites"),
    ("tracking-cookies", "Tracking Cookies"),
    ("tracking-cookies-off", "Tracking Cookies Off"),
    ("trash", "Trash"),
    ("trending", "Trending"),
    ("unauthenticated-user", "Unauthenticated User"),
    ("update", "Update"),
    ("update-circle-fill", "Update Circle Fill"),
    ("user", "User"),
    ("users", "Users"),
    ("vertical-scrolling", "Vertical Scrolling"),
    ("vertical-tabs", "Vertical Tabs"),
    ("video-game-controller", "Video Game Controller"),
    ("warning", "Warning"),
    ("warning-fill", "Warning Fill"),
    ("window", "Window"),
    ("window-firefox", "Window Firefox"),
    ("wrapped-scrolling", "Wrapped Scrolling"),
    ("xr", "XR"),
    ("xr-off", "XR Off"),
]

CONDITIONAL_DISPLAY_CHOICES = [
    ("all", "All Users"),
    ("is-firefox", "Firefox Users"),
    ("not-firefox", "Non Firefox Users"),
    ("state-fxa-supported-signed-in", "Signed-in Users"),
    ("state-fxa-supported-signed-out", "Signed-out Users"),
    ("osx", "macOS Users"),
    ("linux", "Linux Users"),
    ("windows", "Windows Users"),
    ("windows-10-plus", "Windows 10+ Users"),
    ("windows-10-plus-signed-in", "Signed-in Windows 10+ Users"),
    ("windows-10-plus-signed-out", "Signed-out Windows 10+ Users"),
]


UITOUR_BUTTON_NEW_TAB = "open_new_tab"
UITOUR_BUTTON_CHOICES = ((UITOUR_BUTTON_NEW_TAB, "Open New Tab"),)
UITOUR_BUTTON_ABOUT_PREFERENCES = "open_about_preferences"
UITOUR_BUTTON_ABOUT_PREFERENCES_GENERAL = "open_about_preferences_general"
UITOUR_BUTTON_ABOUT_PREFERENCES_HOME = "open_about_preferences_home"
UITOUR_BUTTON_ABOUT_PREFERENCES_SEARCH = "open_about_preferences_search"
UITOUR_BUTTON_ABOUT_PREFERENCES_PRIVACY = "open_about_preferences_privacy"
UITOUR_BUTTON_PROTECTIONS_REPORT = "open_protections_report"
UITOUR_BUTTON_CHOICES = (
    (UITOUR_BUTTON_NEW_TAB, "Open New Tab"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES, "Open Preferences"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_GENERAL, "Open Preferences - General"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_HOME, "Open Preferences - Home"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_SEARCH, "Open Preferences - Search"),
    (UITOUR_BUTTON_ABOUT_PREFERENCES_PRIVACY, "Open Preferences - Privacy"),
    (UITOUR_BUTTON_PROTECTIONS_REPORT, "Open Protections Report"),
)


BUTTON_TYPE = "button"
UITOUR_BUTTON_TYPE = "uitour_button"
FXA_BUTTON_TYPE = "fxa_button"


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


def validate_video_url(value):
    if value and "youtube.com" not in value and "youtu.be" not in value and "assets.mozilla.net" not in value:
        raise ValidationError("Please provide a valid YouTube or assets.mozilla.net URL for the video.")
    return value


class IconChoiceBlock(ThumbnailChoiceBlock):
    def __init__(self, choices=None, thumbnails=None, thumbnail_templates=None, thumbnail_size=20, **kwargs):
        choices = choices or ICON_CHOICES
        thumbnail_templates = {choice[0]: "cms/wagtailadmin/icon-choice.html" for choice in choices}
        super().__init__(choices, thumbnails, thumbnail_templates, thumbnail_size, **kwargs)


# Element blocks
class HeadingBlock(blocks.StructBlock):
    superheading_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    heading_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    subheading_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)

    class Meta:
        icon = "title"
        label = "Heading"
        label_format = "{heading_text}"
        template = "cms/blocks/heading.html"


# Buttons


def get_button_types(allow_uitour=False):
    """Helper function to get button types based on allow_uitour flag.

    Args:
        allow_uitour: If True, includes UI Tour button type.

    Returns:
        List of button type strings.
    """
    if allow_uitour:
        return [BUTTON_TYPE, UITOUR_BUTTON_TYPE, FXA_BUTTON_TYPE]
    return [BUTTON_TYPE, FXA_BUTTON_TYPE]


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


def ButtonBlock(themes=None, **kwargs):
    """Factory function to create ButtonBlock with specified themes.

    Args:
        themes: List of theme strings to include in the button settings.
    """

    class _ButtonBlock(blocks.StructBlock):
        settings = BaseButtonSettings(themes=themes)
        label = blocks.CharBlock(label="Button Text")
        link = LinkBlock()

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
        if button_type == UITOUR_BUTTON_NEW_TAB:
            theme_classes += " ui-tour-open-new-tab"
        elif button_type == UITOUR_BUTTON_ABOUT_PREFERENCES:
            theme_classes += " ui-tour-open-about-preferences"
        elif button_type == UITOUR_BUTTON_ABOUT_PREFERENCES_GENERAL:
            theme_classes += " ui-tour-open-about-preferences-general"
        elif button_type == UITOUR_BUTTON_ABOUT_PREFERENCES_HOME:
            theme_classes += " ui-tour-open-about-preferences-home"
        elif button_type == UITOUR_BUTTON_ABOUT_PREFERENCES_SEARCH:
            theme_classes += " ui-tour-open-about-preferences-search"
        elif button_type == UITOUR_BUTTON_ABOUT_PREFERENCES_PRIVACY:
            theme_classes += " ui-tour-open-about-preferences-privacy"
        elif button_type == UITOUR_BUTTON_PROTECTIONS_REPORT:
            theme_classes += " ui-tour-open-protections-report"
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

    Example: min_num0 and max_num=2 allows up to 2 buttons, or up to 2 UI Tour
    buttons, or up to 1 of each.
    """
    button_blocks = {
        BUTTON_TYPE: ButtonBlock(themes=themes),
        UITOUR_BUTTON_TYPE: UITourButtonBlock(themes=themes),
        FXA_BUTTON_TYPE: FXAccountButtonBlock(themes=themes),
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
    link = LinkBlock()

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


class ImageVariantsBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    settings = ImageVariantsBlockSettings()

    class Meta:
        label = "Image"
        label_format = "Image - {image}"
        template = "cms/blocks/image-variants.html"


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


class QRCodeBlock(blocks.StructBlock):
    data = blocks.URLBlock(label="QR Code Data", help_text="The URL or text encoded in the QR code.")
    background = ImageChooserBlock(
        required=False,
        help_text="This QR Code background should be 1200x675, expecting a 300px square directly in the center. "
        "This image will be cropped to a square on mobile.",
    )

    class Meta:
        label = "QR Code"
        label_format = "QR Code - {data}"


class MediaContentSettings(blocks.StructBlock):
    media_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Media After",
        inline_form=True,
        help_text="Place media after text content on desktop",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Media After: {media_after}"
        form_classname = "compact-form struct-block"


def MediaContentBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create MediaContentBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _MediaContentBlock(blocks.StructBlock):
        settings = MediaContentSettings()
        media = blocks.StreamBlock(
            [
                ("image", ImageVariantsBlock()),
                ("video", VideoBlock()),
            ],
            label="Media",
            required=False,
            max_num=1,
        )
        eyebrow = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        tags = blocks.ListBlock(TagBlock(), min_num=0, max_num=3, default=[])
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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

        def clean(self, value):
            cleaned_data = super().clean(value)
            image = cleaned_data.get("image")
            qr_code = cleaned_data.get("qr_code")
            video = cleaned_data.get("video")

            if video and (qr_code or image):
                raise ValidationError("Please, either provide a video or an image, not both.")
            return cleaned_data

    return _MediaContentBlock(*args, **kwargs)


# Cards


class BaseCardSettings(blocks.StructBlock):
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Expand the link click area to the whole card",
    )
    show_to = blocks.ChoiceBlock(
        choices=CONDITIONAL_DISPLAY_CHOICES,
        default="all",
        label="Show To",
        inline_form=True,
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Expand Link: {expand_link} - Show To: {show_to}"
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
        superheading = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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
            label_format = "Cards List - {heading}"

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
            label_format = "Step Cards - {heading}"

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
        eyebrow = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
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
            label_format = "Step Cards - {heading}"

    return _StepCardListBlock(*args, **kwargs)


def StickerCardBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create StickerCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                        If False, only allows regular buttons.
    """

    class _StickerCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        image = ImageVariantsBlock()
        superheading = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            themes=BUTTON_THEMES_2026,
            min_num=0,
            max_num=1,
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
        image = ImageVariantsBlock()
        eyebrow = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
        headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
        content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
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


def CardsListBlock2026(allow_uitour=False, *args, **kwargs):
    """Factory function to create CardsListBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _CardsListBlock(blocks.StructBlock):
        cards = blocks.StreamBlock(
            [
                ("sticker_card", StickerCardBlock2026(allow_uitour=allow_uitour)),
                ("illustration_card", IllustrationCard2026Block(allow_uitour=allow_uitour)),
            ]
        )

        class Meta:
            template = "cms/blocks/cards-list.html"
            label = "Cards List"
            label_format = "Cards List - {heading}"

    return _CardsListBlock(*args, **kwargs)


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
    show_to = blocks.ChoiceBlock(
        choices=CONDITIONAL_DISPLAY_CHOICES,
        default="all",
        label="Show To",
        inline_form=True,
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Color: {color} - Icon: {icon} - Inverted: {inverted} - Closable: {closable} - Show To: {show_to}"
        form_classname = "compact-form struct-block"


class InlineNotificationBlock(blocks.StructBlock):
    settings = InlineNotificationSettings()
    message = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/inline-notification.html"
        label = "Inline Notification"
        label_format = "{message}"
        form_classname = "compact-form struct-block"


class IntroBlockSettings(blocks.StructBlock):
    media_position = blocks.ChoiceBlock(
        choices=(("after", "After"), ("before", "Before")),
        default="after",
        label="Media Position",
        inline_form=True,
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Media Position: {media_position}"
        form_classname = "compact-form struct-block"


def IntroBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create IntroBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IntroBlock(blocks.StructBlock):
        settings = IntroBlockSettings()
        media = blocks.StreamBlock(
            [
                ("image", ImageVariantsBlock()),
                ("video", VideoBlock()),
            ],
            label="Media",
            required=False,
            max_num=1,
        )
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

        def clean(self, value):
            cleaned_data = super().clean(value)
            image = cleaned_data.get("image")
            qr_code = cleaned_data.get("qr_code")
            video = cleaned_data.get("video")

            if video and (qr_code or image):
                raise ValidationError("Please, either provide a video or an image, not both.")
            return cleaned_data

    return _IntroBlock(*args, **kwargs)


class SectionBlockSettings(blocks.StructBlock):
    show_to = blocks.ChoiceBlock(
        choices=CONDITIONAL_DISPLAY_CHOICES,
        default="all",
        label="Show To",
        inline_form=True,
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Show To: {show_to}"
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


def SectionBlock2026(allow_uitour=False, *args, **kwargs):
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
                ("cards_list", CardsListBlock2026(allow_uitour=allow_uitour)),
                ("step_cards", StepCardListBlock2026(allow_uitour=allow_uitour)),
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
            ("outlined", "Outlined"),
            ("purple", "Purple"),
        ),
        default="outlined",
        inline_form=True,
    )
    media_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Media After",
        inline_form=True,
        help_text="Place media after text content on desktop.",
    )
    show_to = blocks.ChoiceBlock(
        choices=CONDITIONAL_DISPLAY_CHOICES,
        default="all",
        label="Show To",
        inline_form=True,
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Theme: {theme} - Media After: {media_after} - Show To: {show_to}"
        form_classname = "compact-form struct-block"


def BannerBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create BannerBlock with appropriate button types."""

    class _BannerBlock(blocks.StructBlock):
        settings = BannerSettings()
        media = blocks.StreamBlock(
            [
                ("image", ImageVariantsBlock()),
                ("video", VideoBlock()),
                ("qr_code", QRCodeBlock()),
            ],
            label="Media",
            required=False,
            max_num=1,
        )
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
            min_num=0,
            max_num=2,
            required=False,
        )

        class Meta:
            template = "cms/blocks/sections/banner.html"
            label = "Banner"
            label_format = "{heading}"

        def clean(self, value):
            cleaned_data = super().clean(value)
            image = cleaned_data.get("image")
            qr_code = cleaned_data.get("qr_code")
            video = cleaned_data.get("video")

            if video and (qr_code or image):
                raise ValidationError("Please, either provide a video or an image/QR code, not both.")
            return cleaned_data

    return _BannerBlock(*args, **kwargs)


class KitBannerSettings(blocks.StructBlock):
    theme = blocks.ChoiceBlock(
        (
            ("filled", "No Kit Image"),
            ("filled-small", "With Small Curious Kit"),
            ("filled-large", "With Large Curious Kit"),
            ("filled-face", "With Sitting Kit"),
            ("filled-tail", "With Kit Tail"),
        ),
        default="filled",
        inline_form=True,
    )
    show_to = blocks.ChoiceBlock(
        choices=CONDITIONAL_DISPLAY_CHOICES,
        default="all",
        label="Show To",
        inline_form=True,
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Theme: {theme} - Show To: {show_to}"
        form_classname = "compact-form struct-block"


def KitBannerBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create KitBannerBlock with appropriate button types."""

    class _KitBannerBlock(blocks.StructBlock):
        settings = KitBannerSettings()
        heading = HeadingBlock()
        buttons = MixedButtonsBlock(
            button_types=get_button_types(allow_uitour),
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


class HomeIntroBlock(blocks.StructBlock):
    heading = HeadingBlock()
    buttons = MixedButtonsBlock(
        button_types=get_button_types(),
        themes=BUTTON_THEMES_2026,
        min_num=0,
        max_num=2,
        required=False,
    )

    class Meta:
        template = "cms/blocks/home-intro.html"
        label = "Home Intro"
        label_format = "{heading}"


class HomeCarouselSlide(blocks.StructBlock):
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    image = ImageVariantsBlock()


class HomeCarouselBlock(blocks.StructBlock):
    heading = HeadingBlock()
    slides = blocks.ListBlock(HomeCarouselSlide(), min_num=2, max_num=5)

    class Meta:
        template = "cms/blocks/sections/home-carousel.html"
        label = "Home Carousel"
        label_format = "{heading}"


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
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    image = ImageVariantsBlock()
    caption_title = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    caption_description = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/sections/showcase.html"
        label = "Showcase"
        label_format = "{heading}"


class CardGalleryCard(blocks.StructBlock):
    icon = IconChoiceBlock()
    superheading = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    description = blocks.RichTextBlock(features=EXPANDED_TEXT_FEATURES)
    buttons = MixedButtonsBlock(
        button_types=get_button_types(),
        themes=BUTTON_THEMES_2026,
        min_num=0,
        max_num=1,
        required=False,
    )
    image = ImageVariantsBlock()


class CardGalleryCallout(blocks.StructBlock):
    superheading = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    description = blocks.RichTextBlock(features=EXPANDED_TEXT_FEATURES)


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
    show_to = blocks.ChoiceBlock(
        choices=CONDITIONAL_DISPLAY_CHOICES,
        default="all",
        label="Show To",
        inline_form=True,
        help_text="Control which users can see this content block",
    )

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Show To: {show_to}"
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


# Thanks Page


class DownloadSupportBlock(blocks.StaticBlock):
    class Meta:
        template = "cms/blocks/download-support.html"
        label = "Download Support Message"
