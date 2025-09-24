# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

HEADING_TEXT_FEATURES = [
    "bold",
    "italic",
    "link",
    "superscript",
    "subscript",
    "strikethrough",
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
    ("folder", "Folder"),
    ("folder-plus", "Folder Plus"),
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
        form_classname = "compact-form struct-block"


class ButtonValue(blocks.StructValue):
    def theme_class(self) -> str:
        classes = {
            "ghost": "button-ghost",
            "secondary": "button-secondary",
        }
        return classes.get(self.get("theme"), "")

    def center_class(self) -> str:
        """TODO"""
        return "" if self.get("center", False) else ""


class ButtonBlock(blocks.StructBlock):
    theme = blocks.ChoiceBlock(
        (
            ("secondary", "Secondary"),
            ("ghost", "Ghost"),
        ),
        required=False,
        inline_form=True,
    )
    external = blocks.BooleanBlock(required=False, default=False, label="External link", inline_form=True)
    center = blocks.BooleanBlock(required=False, default=False, inline_form=True)
    icon = blocks.ChoiceBlock(required=False, choices=ICON_CHOICES, inline_form=True)
    icon_position = blocks.ChoiceBlock(
        choices=(("left", "Left"), ("right", "Right")),
        default="right",
        label="Icon Position",
        inline_form=True,
    )
    link = blocks.CharBlock()
    label = blocks.CharBlock(label="Button Text")

    class Meta:
        template = "cms/blocks/button.html"
        form_classname = "compact-form struct-block"
        label = "Button"
        label_format = "Button - {label}"
        value_class = ButtonValue


class LinkBlock(blocks.StructBlock):
    link = blocks.CharBlock()
    label = blocks.CharBlock(label="Link Text")
    external = blocks.BooleanBlock(required=False, default=False, label="External link")


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


# Section blocks


class IntroBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False, inline_form=True)
    media_position = blocks.ChoiceBlock(
        choices=(("after", "After"), ("before", "Before")),
        default="after",
        label="Media Position",
        inline_form=True,
    )
    heading = HeadingBlock()
    buttons = blocks.ListBlock(ButtonBlock(), max_num=2, min_num=0)

    class Meta:
        template = "cms/blocks/intro.html"
        label = "Intro"
        label_format = "Intro - {heading}"
        form_classname = "compact-form struct-block"


class FeatureRowBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    eyebrow = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)

    class Meta:
        label = "Feature Row"
        label_format = "{headline}"
        form_classname = "compact-form struct-block"


class FeaturesBlock(blocks.StructBlock):
    heading = HeadingBlock()
    cta = blocks.ListBlock(LinkBlock(), min_num=0, max_num=1, label="Call to Action")
    rows = blocks.ListBlock(FeatureRowBlock())

    class Meta:
        template = "cms/blocks/features.html"
        label = "Features"
        label_format = "Features - {heading}"
        form_classname = "compact-form struct-block"


class HighlightCardBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)

    class Meta:
        label = "Highlight Card"
        label_format = "{headline}"
        form_classname = "compact-form struct-block"


class HighlightsBlock(blocks.StructBlock):
    heading = HeadingBlock()
    cards = blocks.ListBlock(HighlightCardBlock())

    class Meta:
        template = "cms/blocks/highlights.html"
        label = "Highlights"
        label_format = "Highlights - {heading}"
        form_classname = "compact-form struct-block"


class SubscribeBannerBlock(blocks.StructBlock):
    heading = HeadingBlock()

    class Meta:
        template = "cms/blocks/subscribe-banner.html"
        label = "Subscribe Banner"
        label_format = "Subscribe Banner - {heading}"
        form_classname = "compact-form struct-block"


class TagCard(blocks.StructBlock):
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)
    tags = blocks.ListBlock(TagBlock(), min_num=1, max_num=3)

    class Meta:
        template = "cms/blocks/tag-card.html"
        label = "Tag Card"
        label_format = "Tag Card - {headline}"
        form_classname = "compact-form struct-block"


# TODO: find a better name for this
class TagCardsBlock(blocks.StructBlock):
    heading = HeadingBlock()
    cards = blocks.ListBlock(TagCard())

    class Meta:
        template = "cms/blocks/tag-cards.html"
        label = "Tag Cards"
        label_format = "Tag Cards - {heading}"
        form_classname = "compact-form struct-block"


class QRCodeBannerBlock(blocks.StructBlock):
    qr_content = blocks.CharBlock(
        required=True,
        help_text="Content to encode in the QR code, e.g., a URL or text.",
    )
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/qr-code-banner.html"
        label = "QR Code Banner"
        label_format = "QR Code Banner - {headline}"
