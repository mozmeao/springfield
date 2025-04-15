# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from wagtail.fields import StreamField
from wagtail.models import TranslatableMixin
from wagtail.snippets.models import register_snippet

from springfield.cms.models.pages import ArticleDetailPageBase, ArticleIndexPageBase
from springfield.firefox.blocks.features import FeaturesVideoBlock


class FeaturesCallToActionSnippet(TranslatableMixin):
    heading = models.CharField(
        max_length=255,
    )

    desc = models.CharField(
        max_length=500,
    )

    image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        "heading",
        "desc",
        "image",
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Features Call To Action Snippet"
        verbose_name_plural = "Features Call To Action Snippets"

    def __str__(self):
        return f"{self.heading} – {self.locale}"


register_snippet(FeaturesCallToActionSnippet)


class FeaturesIndexPage(ArticleIndexPageBase):
    subpage_types = ["FeaturesDetailPage"]
    template = "firefox/features/cms/index.html"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request)
        article_data = FeaturesDetailPage.objects.filter(locale=self.locale).live().public().order_by("-first_published_at")

        featured_articles = article_data.filter(featured_article=True)
        list_articles = article_data.filter(featured_article=False)

        context["featured_articles"] = featured_articles
        context["list_articles"] = list_articles
        context["ftl_files"] = ["firefox/features/index-2023", "firefox/features/shared"]
        return context


class FeaturesDetailPage(ArticleDetailPageBase):
    parent_page_types = ["FeaturesIndexPage"]
    template = "firefox/features/cms/detail.html"

    article_media = StreamField(
        [("video", FeaturesVideoBlock(max_num=1))],
        blank=True,
        null=True,
        collapsed=True,
    )

    featured_article = models.BooleanField(
        default=False,
        help_text="Check to set as a featured article on the index page.",
    )

    call_to_action_bottom = models.ForeignKey(
        "firefox.FeaturesCallToActionSnippet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content_panels = ArticleDetailPageBase.content_panels + [
        "article_media",
        "featured_article",
        "call_to_action_bottom",
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request)
        context["ftl_files"] = ["firefox/features/index-2023", "firefox/features/shared"]
        return context
