# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.core.exceptions import ValidationError

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail_link_block.blocks import LinkBlock

HEADING_TEXT_FEATURES = [
    "bold",
    "italic",
    "link",
    "superscript",
    "subscript",
    "strikethrough",
    "fxa",
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
    ("ai", "AI"),
    ("alert", "Alert"),
    ("android", "Android"),
    ("apple", "Apple"),
    ("arrow-down", "Arrow Down"),
    ("arrow-left", "Arrow Left"),
    ("arrow-right", "Arrow Right"),
    ("arrow-up", "Arrow Up"),
    ("bell", "Bell"),
    ("blog", "Blog"),
    ("bookmark", "Bookmark"),
    ("calendar", "Calendar"),
    ("caret-down", "Caret Down"),
    ("caret-up", "Caret Up"),
    ("chat", "Chat"),
    ("check", "Check"),
    ("close", "Close"),
    ("cloud", "Cloud"),
    ("copy", "Copy"),
    ("data-insights", "Data Insights"),
    ("data-pie", "Data Pie"),
    ("design", "Design"),
    ("download", "Download"),
    ("earth", "Earth"),
    ("edit-write", "Edit Write"),
    ("email", "Email"),
    ("event", "Event"),
    ("external-link", "External Link"),
    ("eye-closed", "Eye Closed"),
    ("eye-open", "Eye Open"),
    ("folder-plus", "Folder Plus"),
    ("folder", "Folder"),
    ("gear", "Gear"),
    ("globe", "Globe"),
    ("hashtag", "Hashtag"),
    ("headphone", "Headphone"),
    ("heart", "Heart"),
    ("home", "Home"),
    ("language", "Language"),
    ("lock", "Lock"),
    ("megaphone", "Megaphone"),
    ("menu", "Menu"),
    ("minus", "Minus"),
    ("mobile-phone", "Mobile Phone"),
    ("paperclip", "Paperclip"),
    ("pause", "Pause"),
    ("play", "Play"),
    ("plus", "Plus"),
    ("quote", "Quote"),
    ("read", "Read"),
    ("report", "Report"),
    ("search", "Search"),
    ("shield", "Shield"),
    ("sound-off", "Sound Off"),
    ("sound-on", "Sound On"),
    ("star", "Star"),
    ("thumbs-up", "Thumbs Up"),
    ("toggle-off", "Toggle Off"),
    ("toggle-on", "Toggle On"),
    ("trash", "Trash"),
    ("update", "Update"),
    ("user", "User"),
]

CONDITIONAL_DISPLAY_CHOICES = [
    ("all", "All Users"),
    ("is-firefox", "Firefox Users"),
    ("not-firefox", "Non Firefox Users"),
    ("state-fxa-supported-signed-in", "Signed-in Users"),
    ("state-fxa-supported-signed-out", "Signed-out Users"),
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


def validate_video_url(value):
    if value and "youtube.com" not in value and "youtu.be" not in value and "assets.mozilla.net" not in value:
        raise ValidationError("Please provide a valid YouTube or assets.mozilla.net URL for the video.")
    return value


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
        }
        return classes.get(self.get("settings", {}).get("theme"), "")


class UUIDBlock(blocks.CharBlock):
    def clean(self, value):
        return super().clean(value) or str(uuid4())


class BaseButtonSettings(blocks.StructBlock):
    theme = blocks.ChoiceBlock(
        (
            ("secondary", "Secondary"),
            ("tertiary", "Tertiary"),
            ("ghost", "Ghost"),
        ),
        required=False,
        inline_form=True,
    )
    icon = blocks.ChoiceBlock(required=False, choices=ICON_CHOICES, inline_form=True)
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


class ButtonBlock(blocks.StructBlock):
    settings = BaseButtonSettings()
    label = blocks.CharBlock(label="Button Text")
    link = LinkBlock()

    class Meta:
        template = "cms/blocks/button.html"
        label = "Button"
        label_format = "Button - {label}"
        value_class = BaseButtonValue


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


class UITourButtonBlock(blocks.StructBlock):
    settings = BaseButtonSettings()
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


class FXAccountButtonBlock(blocks.StructBlock):
    settings = BaseButtonSettings()
    label = blocks.CharBlock(label="Button Text")

    class Meta:
        template = "cms/blocks/fxa_button.html"
        label = "Firefox Account Button"
        label_format = "Firefox Account Button"
        value_class = BaseButtonValue


def MixedButtonsBlock(button_types: list, min_num: int, max_num: int, *args, **kwargs):
    """
    Creates a StreamBlock that can contain either regular buttons or UI Tour buttons.

    The min_num and max_num parameters control the total number of buttons (combined).

    Example: min_num0 and max_num=2 allows up to 2 buttons, or up to 2 UI Tour
    buttons, or up to 1 of each.
    """
    button_blocks = {
        BUTTON_TYPE: ButtonBlock(),
        UITOUR_BUTTON_TYPE: UITourButtonBlock(),
        FXA_BUTTON_TYPE: FXAccountButtonBlock(),
    }
    return blocks.StreamBlock(
        [(button_type, button_blocks[button_type]) for button_type in button_types],
        max_num=max_num,
        min_num=min_num,
        label="Buttons",
        *args,
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


class TagButtonBlock(ButtonBlock):
    tag = blocks.CharBlock()

    class Meta:
        template = "cms/blocks/tag-button.html"
        label = "Tag Button"
        label_format = "Tag Button - {label}"


class TagBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    icon = blocks.ChoiceBlock(choices=ICON_CHOICES)
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


class LightDarkImageBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    dark_image = ImageChooserBlock(
        required=False,
        label="Dark Mode Image",
        help_text="Optional dark mode image",
    )

    class Meta:
        label = "Image"
        label_format = "Image - {image}"
        template = "cms/blocks/light-dark-image.html"


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
        image = ImageChooserBlock(
            required=False,
        )
        dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
        video = blocks.ListBlock(
            VideoBlock(),
            min_num=0,
            max_num=1,
            default=[],
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

    class Meta:
        icon = "cog"
        collapsed = True
        label = "Settings"
        label_format = "Expand Link: {expand_link}"
        form_classname = "compact-form struct-block"


def StickerCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create StickerCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _StickerCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        image = ImageChooserBlock()
        dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
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


def TagCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create TagCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _TagCardBlock(blocks.StructBlock):
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
            template = "cms/blocks/tag-card.html"
            label = "Tag Card"
            label_format = "Tag Card - {headline}"

    return _TagCardBlock(*args, **kwargs)


def IconCardBlock(allow_uitour=False, *args, **kwargs):
    """Factory function to create IconCardBlock with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons.
                      If False, only allows regular buttons.
    """

    class _IconCardBlock(blocks.StructBlock):
        settings = BaseCardSettings()
        icon = blocks.ChoiceBlock(choices=ICON_CHOICES, inline_form=True)
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
        image = ImageChooserBlock(inline_form=True)
        dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
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
                ("tag_card", TagCardBlock(allow_uitour=allow_uitour)),
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


# Section blocks


class InlineNotificationSettings(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=ICON_CHOICES, required=False, inline_form=True)
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
        image = ImageChooserBlock(
            required=False,
        )
        dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
        video = blocks.ListBlock(
            VideoBlock(),
            min_num=0,
            max_num=1,
            default=[],
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
                ("image", LightDarkImageBlock()),
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
    preheading_button = blocks.ListBlock(TagButtonBlock(), min_num=0, max_num=1, default=[])
    heading = HeadingBlock()
    buttons = MixedButtonsBlock(
        button_types=get_button_types(),
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
    image = ImageChooserBlock()


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
    desktop_image = LightDarkImageBlock(label="Desktop Image")
    mobile_image = LightDarkImageBlock(label="Mobile Image")
    caption_title = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    caption_description = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/sections/showcase.html"
        label = "Showcase"
        label_format = "{heading}"


class CardGalleryCard(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=ICON_CHOICES)
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    description = blocks.RichTextBlock(features=EXPANDED_TEXT_FEATURES)
    buttons = MixedButtonsBlock(
        button_types=get_button_types(),
        min_num=0,
        max_num=1,
        required=False,
    )
    image = ImageChooserBlock()


class CardGalleryCallout(blocks.StructBlock):
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    description = blocks.RichTextBlock(features=EXPANDED_TEXT_FEATURES)
    buttons = MixedButtonsBlock(
        button_types=get_button_types(),
        min_num=0,
        max_num=1,
        required=False,
    )


class CardGalleryBlock(blocks.StructBlock):
    heading = HeadingBlock()
    main_card = CardGalleryCard()
    secondary_card = CardGalleryCard()
    callout_card = CardGalleryCallout()
    cta = blocks.ListBlock(CTABlock(), min_num=0, max_num=1, default=[], label="Call to Action")

    class Meta:
        template = "cms/blocks/sections/card-gallery.html"
        label = "Card Gallery"
        label_format = "{heading}"
