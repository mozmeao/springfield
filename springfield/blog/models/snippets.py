# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from modelcluster.fields import ParentalKey
from taggit.models import ItemBase, TagBase
from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.models import TranslatableMixin
from wagtail_localize.fields import SynchronizedField

from springfield.cms.blocks import EXPANDED_TEXT_FEATURES
from springfield.cms.models.snippets import BaseDraftTranslatableSnippetMixin
from springfield.cms.rich_text import RichTextField


class BlogTopic(BaseDraftTranslatableSnippetMixin, models.Model):
    """A topic for categorizing blog articles."""

    name = models.CharField()
    slug = models.SlugField()

    panels = [
        TitleFieldPanel("name"),
        FieldPanel("slug"),
    ]

    override_translatable_fields = [
        SynchronizedField("slug"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Blog Topic"
        verbose_name_plural = "Blog Topics"
        unique_together = [*TranslatableMixin.Meta.unique_together, ("slug", "locale")]

    def __str__(self):
        return f"{self.name} – {self.locale}"


class BlogTag(BaseDraftTranslatableSnippetMixin, TagBase):
    """A tag for labelling blog articles. Articles reference default-locale tags; the
    localized name is resolved at render time by get_localized()."""

    free_tagging = False

    # Redeclared without taggit's global unique=True — uniqueness is per locale (see Meta),
    # so one concept can exist once per language. max_length stays at taggit's 100 because
    # Wagtail's tag-length validation reads it.
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, allow_unicode=True)

    panels = [
        TitleFieldPanel("name"),
        FieldPanel("slug"),
    ]

    override_translatable_fields = [
        SynchronizedField("slug"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Blog Tag"
        verbose_name_plural = "Blog Tags"
        unique_together = [
            *TranslatableMixin.Meta.unique_together,
            ("slug", "locale"),
            ("name", "locale"),
        ]

    def __str__(self):
        return f"{self.name} – {self.locale}"


class TaggedBlogArticle(ItemBase):
    """Join model between BlogArticlePage and BlogTag."""

    tag = models.ForeignKey(BlogTag, related_name="tagged_articles", on_delete=models.CASCADE)
    content_object = ParentalKey("blog.BlogArticlePage", related_name="tagged_items", on_delete=models.CASCADE)


class BlogAuthor(BaseDraftTranslatableSnippetMixin, models.Model):
    """A person credited on blog articles. Articles reference default-locale authors;
    the localized name is resolved at render time by BlogArticlePage.get_authors()."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True)
    bio = RichTextField(features=EXPANDED_TEXT_FEATURES, blank=True)
    image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    email = models.EmailField(blank=True)

    panels = [
        TitleFieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("job_title"),
        FieldPanel("bio"),
        FieldPanel("image"),
        FieldPanel("email"),
    ]

    override_translatable_fields = [
        SynchronizedField("slug"),
        SynchronizedField("email"),
        SynchronizedField("image"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Blog Author"
        verbose_name_plural = "Blog Authors"
        unique_together = [*TranslatableMixin.Meta.unique_together, ("slug", "locale")]

    def __str__(self):
        return f"{self.name} – {self.locale}"
