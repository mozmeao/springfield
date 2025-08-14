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

HEADING_SIZE_CHOICES = (
    ("h1", "H1"),
    ("h2", "H2"),
    ("h3", "H3"),
    ("h4", "H4"),
    ("h5", "H5"),
    ("h6", "H6"),
)


# Element blocks

class HeadingBlock(blocks.StructBlock):
    accent_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    subheadline_text = blocks.RichTextBlock(
        features=HEADING_TEXT_FEATURES, required=False
    )
    alignment = blocks.ChoiceBlock(
        choices=(("text-center", "Center"), ("text-left", "Left")),
        default="text-left",
    )
    heading_size = blocks.ChoiceBlock(
        choices=HEADING_SIZE_CHOICES,
        default="h2",
    )

    class Meta:
        icon = "title"
        label = "Heading"
        label_format = "{headline_text}"
        template = "cms/blocks/heading.html"


class ButtonValue(blocks.StructValue):
    def theme_class(self) -> str:
        classes = {
            "outline": "wnp-button wnp-button-outline",
            "secondary": "wnp-button wnp-button-secondary",
        }
        return classes.get(self.get("theme"), "")

    def size_class(self) -> str:
        """TODO"""
        return ""

    def center_class(self) -> str:
        """TODO"""
        return "" if self.get("center", False) else ""


class ButtonBlock(blocks.StructBlock):
    link = blocks.CharBlock()
    label = blocks.CharBlock(label="Button Text")
    external = blocks.BooleanBlock(
        required=False, default=False, label="External link"
    )
    theme = blocks.ChoiceBlock(
        (
            ("outline", "Outline"),
            ("secondary", "Secondary"),
        ),
        default="outline",
        required=False,
    )
    size = blocks.ChoiceBlock(
        (
            ("xs", "X-Small"),
            ("sm", "Small"),
            ("md", "Medium"),
            ("lg", "Large"),
        ),
        default="md",
        required=False,
    )
    center = blocks.BooleanBlock(required=False, default=False)
    # TODO: implement an icons system
    icon = blocks.ChoiceBlock(
        required=False,
        choices=[
            ("arrow-right", "Arrow Right"),
        ]
    )

    class Meta:
        template = "cms/blocks/button.html"
        label = "Button"
        label_format = "Button - {label}"
        value_class = ButtonValue


class LinkBlock(blocks.StructBlock):
    link = blocks.CharBlock()
    label = blocks.CharBlock(label="Link Text")
    external = blocks.BooleanBlock(
        required=False, default=False, label="External link"
    )


# class TagBlock(blocks.StructBlock):
#     title = blocks.CharBlock()
#     icon = blocks.ChoiceBlock(
#         choices=[
#             ("tag-icon-1", "Tag Icon 1"),
#             ("tag-icon-2", "Tag Icon 2"),
#             ("tag-icon-3", "Tag Icon 3"),
#         ]
#     )
#     color = blocks.ChoiceBlock(
#         choices=[
#             ("tag-color-1", "Tag Color 1"),
#             ("tag-color-2", "Tag Color 2"),
#             ("tag-color-3", "Tag Color 3"),
#         ]
#     )

# Section blocks

class HeroBlock(blocks.StructBlock):
    heading = HeadingBlock()
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)
    image = ImageChooserBlock()

    class Meta:
        template = "cms/blocks/hero.html"
        label = "Hero"
        label_format = "Hero - {heading}"


class FeatureRowBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    eyebrow = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)


class FeaturesBlock(blocks.StructBlock):
    heading = HeadingBlock()
    cta = blocks.ListBlock(LinkBlock(), min_num=0, max_num=1)
    rows = blocks.ListBlock(FeatureRowBlock())

    class Meta:
        template = "cms/blocks/features.html"
        label = "Features"
        label_format = "Features - {heading}"


class HighlightCardBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    dark_image = ImageChooserBlock(required=False, help_text="Optional dark mode image")
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)


class HighlightsBlock(blocks.StructBlock):
    heading = HeadingBlock()
    cards = blocks.ListBlock(HighlightCardBlock())

    class Meta:
        template = "cms/blocks/highlights.html"
        label = "Highlights"
        label_format = "Highlights - {heading}"


class SubscribeBannerBlock(blocks.StructBlock):
    heading = HeadingBlock()

    class Meta:
        template = "cms/blocks/subscribe-banner.html"
        label = "Subscribe Banner"
        label_format = "Subscribe Banner - {heading}"


# class TagCard(blocks.StructBlock):
#     headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
#     content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
#     button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)
#     tags = blocks.ListBlock(TagBlock(), min_num=1, max_num=3)

#     class Meta:
#         template = "cms/blocks/tag-card.html"
#         label = "Tag Card"
#         label_format = "Tag Card - {headline}"


# TODO: find a name for this
class TagCardsBlock(blocks.StructBlock):
    heading = HeadingBlock()
    # cards = blocks.ListBlock(TagCard())

    class Meta:
        template = "cms/blocks/tag-cards.html"
        label = "Tag Cards"
        label_format = "Tag Cards - {heading}"


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
