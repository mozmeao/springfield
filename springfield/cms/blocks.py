# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# from django.core.exceptions import ValidationError

from wagtail import blocks

# from wagtail.embeds.blocks import EmbedBlock
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


class InlineNotificationBlock(blocks.StructBlock):
    message = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/inline-notification.html"
        label = "Inline Notification"
        label_format = "{message}"
        form_classname = "compact-form struct-block"


class MediaContentBlock(blocks.StructBlock):
    # TODO: re-enable the embed block and make the image optional
    # when this issue with Wagtail Localize is resolved
    # https://github.com/wagtail/wagtail-localize/issues/875
    image = ImageChooserBlock(
        # required=False,
        # help_text="Either an image or embed is required.",
        inline_form=True,
    )
    # embed = EmbedBlock(
    #     required=False,
    #     help_text="Either an image or embed is required.",
    #     max_width=800,
    #     max_height=400,
    #     inline_form=True,
    # )
    media_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Media After",
        inline_form=True,
        help_text="Place media after text content on desktop",
    )
    eyebrow = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    buttons = blocks.ListBlock(ButtonBlock(), max_num=2, min_num=0)

    class Meta:
        label = "Media + Content"
        label_format = "{headline}"
        form_classname = "compact-form struct-block"
        template = "cms/blocks/media-content.html"

    # def clean(self, value):
    #     cleaned_data = super().clean(value)
    #     if not cleaned_data.get("image") and not cleaned_data.get("embed"):
    #         raise ValidationError(
    #             "Either an image or embed is required.",
    #         )
    #     return cleaned_data


# Cards


class StickerCardBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Expand the link click area to the whole card",
    )
    buttons = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)

    class Meta:
        label = "Sticker Card"
        label_format = "{headline}"
        form_classname = "compact-form struct-block"
        template = "cms/blocks/sticker-card.html"


class TagCardBlock(blocks.StructBlock):
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    buttons = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)
    tags = blocks.ListBlock(TagBlock(), min_num=1, max_num=3)

    class Meta:
        template = "cms/blocks/tag-card.html"
        label = "Tag Card"
        label_format = "Tag Card - {headline}"
        form_classname = "compact-form struct-block"


class IconCardBlock(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=ICON_CHOICES, inline_form=True)
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        inline_form=True,
        help_text="Expand the link click area to the whole card",
    )
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)

    class Meta:
        template = "cms/blocks/icon-card.html"
        label = "Icon Card"
        label_format = "Icon Card - {headline}"
        form_classname = "compact-form struct-block"


class IllustrationCardBlock(blocks.StructBlock):
    image = ImageChooserBlock(inline_form=True)
    image_after = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Image After",
        inline_form=True,
        help_text="Place image after text content",
    )
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        inline_form=True,
        help_text="Expand the link click area to the whole card",
    )
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    buttons = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)

    class Meta:
        template = "cms/blocks/illustration-card.html"
        label = "Illustration Card"
        label_format = "{headline}"
        form_classname = "compact-form struct-block"


class StepCardBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    expand_link = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Expand the link click area to the whole card",
    )
    buttons = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)

    class Meta:
        template = "cms/blocks/step-card.html"
        label = "Step Card"
        label_format = "{headline}"
        form_classname = "compact-form struct-block"


class CardsListBlock(blocks.StructBlock):
    cards = blocks.StreamBlock(
        [
            ("sticker_card", StickerCardBlock()),
            ("tag_card", TagCardBlock()),
            ("icon_card", IconCardBlock()),
            ("illustration_card", IllustrationCardBlock()),
        ]
    )

    class Meta:
        template = "cms/blocks/cards-list.html"
        label = "Cards List"
        label_format = "Cards List - {heading}"
        form_classname = "compact-form struct-block"


class StepCardListBlock(blocks.StructBlock):
    cards = blocks.ListBlock(StepCardBlock())

    class Meta:
        template = "cms/blocks/cards-list.html"
        label = "Step Cards List"
        label_format = "Step Cards - {heading}"
        form_classname = "compact-form struct-block"


# Section blocks


class IntroBlock(blocks.StructBlock):
    image = ImageChooserBlock(
        required=False,
        inline_form=True,
        # help_text="Either enter an image or embed, or leave both blank.",
    )
    # TODO: re-enable the block when this issue with Wagtail Localize is resolved
    # https://github.com/wagtail/wagtail-localize/issues/875
    # embed = EmbedBlock(
    #     required=False,
    #     max_width=800,
    #     max_height=400,
    #     inline_form=True,
    #     help_text="Either enter an image or embed, or leave both blank.",
    # )
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
        label_format = "{heading}"
        form_classname = "compact-form struct-block"


class SectionBlock(blocks.StructBlock):
    heading = HeadingBlock()
    content = blocks.StreamBlock(
        [
            ("media_content", MediaContentBlock()),
            ("cards_list", CardsListBlock()),
            ("step_cards", StepCardListBlock()),
        ]
    )
    cta = blocks.ListBlock(LinkBlock(), min_num=0, max_num=1, label="Call to Action")

    class Meta:
        template = "cms/blocks/section.html"
        label = "Section"
        label_format = "{heading}"
        form_classname = "compact-form struct-block"


# Banners


class SubscriptionBlock(blocks.StructBlock):
    heading = HeadingBlock()

    class Meta:
        template = "cms/blocks/subscription.html"
        label = "Subscription"
        label_format = "Subscription - {heading}"
        form_classname = "compact-form struct-block"


class BannerBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    qr_code = blocks.CharBlock(
        required=False,
        help_text="Content to encode in the QR code, e.g., a URL or text. If an image is added, it will be used as the QR code background.",
    )
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)

    class Meta:
        template = "cms/blocks/banner.html"
        label = "Banner"
        label_format = "{headline}"
