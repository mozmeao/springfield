from django.templatetags.static import static

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

# TODO: Implement an icon system
ICON_CHOICES = [
    ("android", "Android"),
    ("apple", "Apple"),
    ("arrow-right", "Arrow Right"),
    ("design", "Design"),
    ("language", "Language"),
    ("shield", "Shield"),
]
ICON_FILES = {
    "android": "img/icons/cms/android-icon.png",
    "apple": "img/icons/cms/apple-icon.png",
    "arrow-right": "img/icons/cms/arrow-right.svg",
    "design": "img/icons/cms/design-icon.svg",
    "language": "img/icons/cms/language-icon.svg",
    "shield": "img/icons/cms/shield.svg",
}

# Element blocks

def get_icon_url(icon_name: str) -> str:
    return static(ICON_FILES.get(icon_name, ""))

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

    def icon_url(self) -> str:
        return get_icon_url(self.get("icon", ""))


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
    icon = blocks.ChoiceBlock(required=False, choices=ICON_CHOICES)

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


class TagValue(blocks.StructValue):
    def icon_url(self) -> str:
        return get_icon_url(self.get("icon", ""))


class TagBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    icon = blocks.ChoiceBlock(
        choices=ICON_CHOICES
    )
    color = blocks.ChoiceBlock(
        choices=[
            ("purple", "Purple"),
            ("blue", "Blue"),
            ("orange", "Orange"),
            ("yellow", "Yellow"),
        ],
        required=False,
    )

    class Meta:
        template = "cms/blocks/tag.html"
        label = "Tag"
        label_format = "Tag - {title}"
        value_class = TagValue


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


class TagCard(blocks.StructBlock):
    headline = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    content = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    button = blocks.ListBlock(ButtonBlock(), max_num=1, min_num=0)
    tags = blocks.ListBlock(TagBlock(), min_num=1, max_num=3)

    class Meta:
        template = "cms/blocks/tag-card.html"
        label = "Tag Card"
        label_format = "Tag Card - {headline}"


# TODO: find a better name for this
class TagCardsBlock(blocks.StructBlock):
    heading = HeadingBlock()
    cards = blocks.ListBlock(TagCard())

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
