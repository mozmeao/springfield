# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import TYPE_CHECKING

from django.forms.utils import ErrorList

from wagtail import blocks
from wagtail.templatetags.wagtailcore_tags import richtext

from springfield.cms.blocks import HEADING_TEXT_FEATURES, ImageVariantsBlock, LocalizedLiveSnippetChooserBlock
from springfield.cms.templatetags.cms_tags import remove_p_tag

if TYPE_CHECKING:
    from springfield.blog.models import BlogArticlePage


class BlockArticleValue(blocks.StructValue):
    def get_article(self) -> BlogArticlePage | None:
        if not hasattr(self, "_article_cache"):
            chosen_article = self["article"]
            # Chosen article may have been deleted, leaving an empty chooser value
            article = chosen_article.localized if chosen_article else None
            self._article_cache = article.specific if article else None
        return self._article_cache

    def get_url(self):
        article_page = self.get_article()
        return article_page.url if article_page else ""

    def get_title(self) -> str:
        if title := self.get("overrides").get("title"):
            return remove_p_tag(richtext(title))
        article_page = self.get_article()
        return article_page.title if article_page else ""

    def get_description(self) -> str:
        from springfield.cms.templatetags.cms_tags import remove_p_tag

        if description := self.get("overrides").get("description"):
            description = remove_p_tag(richtext(description))
            if description:
                return description
        article_page = self.get_article()
        if article_page and article_page.description:
            return remove_p_tag(richtext(article_page.description))
        return ""

    def get_topic(self) -> str:
        if topic := self.get("overrides").get("topic"):
            return topic
        article_page = self.get_article()
        if article_page:
            if topic := article_page.get_topic():
                return topic.name
        return ""

    def get_image(self):
        article_page = self.get_article()
        image_override = self.get("overrides").get("image")
        if image := image_override.get("image"):
            return image
        if article_page:
            return article_page.get_listing_image()
        return None

    def get_dark_image(self):
        article_page = self.get_article()
        image_override = self.get("overrides").get("image")
        if image := image_override.get("settings").get("dark_mode_image"):
            return image
        if article_page:
            return article_page.get_listing_image_variants().dark_mode
        return None

    def get_mobile_image(self):
        article_page = self.get_article()
        image_override = self.get("overrides").get("image")
        if image := image_override.get("settings").get("mobile_image"):
            return image
        if article_page:
            return article_page.get_listing_image_variants().mobile
        return None

    def get_mobile_dark_image(self):
        article_page = self.get_article()
        image_override = self.get("overrides").get("image")
        if image := image_override.get("settings").get("dark_mode_mobile_image"):
            return image
        if article_page:
            return article_page.get_listing_image_variants().dark_mode_mobile
        return None


class BlogArticleOverrideBlock(blocks.StructBlock):
    image = ImageVariantsBlock(required=False)
    topic = blocks.CharBlock(required=False)
    title = blocks.CharBlock(required=False)
    description = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES, required=False)


class BlogArticleBlock(blocks.StructBlock):
    """Picks a blog article with optional field overrides for display on the index page."""

    article = blocks.PageChooserBlock(target_model="blog.BlogArticlePage")
    overrides = BlogArticleOverrideBlock(required=False)

    class Meta:
        label = "Blog Article"
        label_format = "{article}"
        icon = "doc-full"
        value_class = BlockArticleValue


class BlogRelatedArticleBlock(blocks.StructBlock):
    """Picks a blog article."""

    article = blocks.PageChooserBlock(target_model="blog.BlogArticlePage")

    class Meta:
        label = "Blog Article"
        label_format = "{article}"
        icon = "doc-full"
        value_class = BlockArticleValue


class BlogArticleSectionValue(blocks.StructValue):
    """A section whose articles the index page resolves before rendering."""

    def get_articles(self):
        return getattr(self, "_articles", [])

    def get_link_url(self):
        return getattr(self, "_link_url", "")


class BlogCardsListSourceBlock(blocks.StreamBlock):
    """Exactly one of topic or tag.

    A single-child StreamBlock enforces that structurally, so the parent needs no
    clean()."""

    topic = LocalizedLiveSnippetChooserBlock("blog.BlogTopic")
    tag = LocalizedLiveSnippetChooserBlock("blog.BlogTag")

    class Meta:
        min_num = 1
        max_num = 1


class BlogLatestArticlesBlock(blocks.StructBlock):
    """A titled grid of the newest articles."""

    heading_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    count = blocks.IntegerBlock(min_value=2, max_value=8, default=4, classname="compact-input")
    link_label = blocks.CharBlock(default="View all")

    class Meta:
        label = "Latest Articles"
        icon = "time"
        template = "blog/blocks/blog-latest-articles-section.html"
        value_class = BlogArticleSectionValue

    def get_source(self, value):
        """The latest section draws from every article, so it has no source."""
        return None

    def filter_articles(self, queryset, value):
        return queryset.order_by("-first_published_at")

    def get_exempt_exclusions(self, value):
        """Nothing is exempt: the latest section has no source of its own."""
        return set(), set()


class BlogCardsListBlock(blocks.StructBlock):
    """A titled grid of articles drawn from one topic or tag."""

    heading_text = blocks.RichTextBlock(features=HEADING_TEXT_FEATURES)
    source = BlogCardsListSourceBlock()
    count = blocks.IntegerBlock(min_value=2, max_value=4, default=4, classname="compact-input")
    link_label = blocks.CharBlock(default="View all")

    class Meta:
        label = "Blog Cards List"
        icon = "list-ul"
        template = "blog/blocks/blog-article-section.html"
        value_class = BlogArticleSectionValue

    def get_source(self, value):
        """The topic or tag this section draws from, or None when it no longer resolves.

        min_num is enforced only while the editor form is being cleaned, and a chooser
        reads a snippet that has since been deleted as None, so stored data can be
        rendered with an empty source."""
        source = value["source"][0] if value["source"] else None
        return source if source and source.value else None

    def filter_articles(self, queryset, value):
        source = self.get_source(value)
        if source is None:
            return queryset.none()
        if source.block_type == "topic":
            return queryset.filter(topic__translation_key=source.value.translation_key).order_by("-first_published_at")
        return queryset.filter(tags__slug=source.value.slug).order_by("-first_published_at")

    def get_exempt_exclusions(self, value):
        """The exclusion this section may override: the source it renders.

        Pointing a section at an excluded topic or tag surfaces it here on purpose.
        Articles excluded for any other reason still drop out."""
        source = self.get_source(value)
        if source is None:
            return set(), set()
        if source.block_type == "topic":
            return {source.value.translation_key}, set()
        return set(), {source.value.translation_key}


class BlogArticleSectionsBlock(blocks.StreamBlock):
    """The article sections of a blog index page.

    Sections are filled in order, each one dropping the articles an earlier section
    already used, and the latest section draws from every article — so anywhere but
    last it silently starves the sections below it. The page renders it last
    regardless, as a full-width band outside the container, so require it there."""

    cards_list = BlogCardsListBlock()
    latest = BlogLatestArticlesBlock()

    def clean(self, value, ignore_required_constraints=False):
        cleaned = super().clean(value, ignore_required_constraints=ignore_required_constraints)
        latest_positions = [position for position, child in enumerate(cleaned) if child.block_type == "latest"]
        if latest_positions and latest_positions[0] != len(cleaned) - 1:
            raise blocks.StreamBlockValidationError(
                block_errors={},
                non_block_errors=ErrorList(["The latest articles section must be the last section, and there can't be more than one."]),
            )
        return cleaned
