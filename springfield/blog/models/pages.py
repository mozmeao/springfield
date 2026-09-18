# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace
from typing import NamedTuple

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Case, Count, Exists, OuterRef, Q, Value, When
from django.http import Http404

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.models import Orderable
from wagtail.search import index

from lib import l10n_utils
from springfield.blog.blocks import BlogArticleBlock, BlogArticleSectionsBlock, BlogRelatedArticleBlock
from springfield.blog.fields import LocalizedClusterTaggableManager
from springfield.blog.models.snippets import BlogTag, BlogTopic
from springfield.cms.blocks import (
    HEADING_TEXT_FEATURES,
    BannerBlock,
    CardsListBlock,
    CodeBlock,
    HeadingBlock,
    ImageCaptionBlock,
    LocalizedLiveSnippetChooserBlock,
    MediaBlock,
    QuoteBlock,
    VideoBlock,
)
from springfield.cms.fields import StreamField
from springfield.cms.models.base import AbstractSpringfieldCMSPage
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.models.pages import UTMParamsMixin
from springfield.cms.rich_text import RichTextBlock, RichTextField

ARTICLES_PER_PAGE = 10


def cache_localized_tags(articles, hidden_translation_keys=()):
    """Populate _tags_cache on each article from a single BlogTag lookup, so rendering
    localized tag names costs one query rather than one per tag.

    Tags in hidden_translation_keys are left out, so a tag kept out of the feed does not
    show on the cards either."""
    slugs = {tag.slug for article in articles for tag in article.tags.all()}
    localized_tags_by_slug = {
        tag.slug: tag
        for tag in BlogTag.objects.filter(slug__in=slugs, locale=SpringfieldLocale.get_active()).live()
        if tag.translation_key not in hidden_translation_keys
    }
    for article in articles:
        article._tags_cache = [localized_tags_by_slug[tag.slug] for tag in article.tags.all() if tag.slug in localized_tags_by_slug]


def cache_localized_topics(articles):
    """Populate _topic_cache on each article from a single BlogTopic lookup, so rendering
    a list costs one query rather than resolving each article's topic separately."""
    slugs = [article.topic.slug for article in articles if article.topic]
    localized_topics_by_slug = {topic.slug: topic for topic in BlogTopic.objects.filter(locale=SpringfieldLocale.get_active(), slug__in=slugs).live()}
    for article in articles:
        if article.topic and article.topic.slug in localized_topics_by_slug:
            article._topic_cache = localized_topics_by_slug[article.topic.slug]


MAX_HEADER_TOPICS = 8


class FeedExclusions(NamedTuple):
    """Translation keys of the topics and tags kept out of automatic feeds."""

    topic_keys: set
    tag_keys: set


def article_list_queryset(queryset):
    """Add everything the article list and card templates render to a BlogArticlePage
    queryset, so rendering does not fan out into a query per article."""
    return (
        queryset.select_related(
            "topic",
            "image",
            "image_dark_mode",
            "image_mobile",
            "image_dark_mode_mobile",
            "listing_image",
        )
        .prefetch_related(
            "tags",
            "image__renditions",
            "image_dark_mode__renditions",
            "image_mobile__renditions",
            "image_dark_mode_mobile__renditions",
            "listing_image__renditions",
        )
        .defer("content")
    )


def prefetch_article_blocks(values):
    """Bulk-fetch the BlogArticlePages referenced by a list of BlockArticleValues and
    populate _article_cache on each, so rendering does not issue a query per block.

    Topics and tags are swapped for their active-locale equivalents at the same time,
    because the referenced article is always the source-locale page."""
    pks = [value["article"].pk for value in values if value.get("article")]
    if not pks:
        return

    articles_by_pk = {article.pk: article for article in article_list_queryset(BlogArticlePage.objects.filter(pk__in=pks))}
    cache_localized_tags(articles_by_pk.values())
    cache_localized_topics(articles_by_pk.values())

    for value in values:
        page = value.get("article")
        if page and page.pk in articles_by_pk:
            value._article_cache = articles_by_pk[page.pk]


class BlogIndexPage(RoutablePageMixin, UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that lists blog posts."""

    subpage_types = ["blog.BlogArticlePage", "blog.BlogTopicPage"]
    ftl_files = ["blog/blog"]

    page_heading = StreamField(
        [("heading", HeadingBlock())],
        max_num=1,
        use_json_field=True,
        null=True,
        blank=True,
    )
    featured_articles = StreamField(
        [("article", BlogArticleBlock())],
        max_num=4,
        use_json_field=True,
        null=True,
        blank=True,
        help_text="Up to 4 featured articles shown at the top of the index page.",
    )
    featured_topics = StreamField(
        [("topic", LocalizedLiveSnippetChooserBlock("blog.BlogTopic"))],
        max_num=MAX_HEADER_TOPICS,
        use_json_field=True,
        null=True,
        blank=True,
        help_text=f"Up to {MAX_HEADER_TOPICS} topics shown at the top of the index page. If empty, the topics with the most articles are shown.",
    )
    feed_exclusions = StreamField(
        [
            ("topic", LocalizedLiveSnippetChooserBlock("blog.BlogTopic")),
            ("tag", LocalizedLiveSnippetChooserBlock("blog.BlogTag")),
        ],
        use_json_field=True,
        null=True,
        blank=True,
        help_text=(
            "Articles with these topics or tags are left out of the full article list and the "
            "latest-articles section, and these tags are hidden on article cards. Topic pages "
            "and ?tag= links are unaffected."
        ),
    )
    article_sections = StreamField(
        BlogArticleSectionsBlock(),
        use_json_field=True,
        null=True,
        blank=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("page_heading"),
        FieldPanel("featured_articles"),
        MultiFieldPanel(
            [
                FieldPanel("article_sections"),
            ],
            heading="Article Sections",
        ),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    blog_options_panels = [
        FieldPanel("featured_topics"),
        FieldPanel("feed_exclusions"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(blog_options_panels, heading="Blog Options"),
            ObjectList(AbstractSpringfieldCMSPage.promote_panels, heading="Promote"),
            ObjectList(settings_panels, heading="Settings"),
        ]
    )

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("page_heading"),
        index.SearchField("article_sections"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Blog Index Page"
        verbose_name_plural = "Blog Index Pages"

    def __str__(self):
        return f"BlogIndexPage: {self.title} - {self.locale}"

    # Index route

    def resolve_article_sections(self):
        """Fill each article section, in order, based on its source and count,
        excluding articles already used in earlier sections.

        Articles are tracked by translation_key, because a featured article block
        stores the page of its source locale while the sections draw from this
        page's own children."""

        seen_translation_keys = {block.value["article"].translation_key for block in (self.featured_articles or []) if block.value.get("article")}
        sections = list(self.article_sections or [])
        pks_by_section = []

        for block in sections:
            exempt_topic_keys, exempt_tag_keys = block.block.get_exempt_exclusions(block.value)
            block_queryset = block.block.filter_articles(
                self.exclude_from_feed(self.live_articles(), exempt_topic_keys, exempt_tag_keys),
                block.value,
            ).exclude(translation_key__in=seen_translation_keys)
            section_articles = list(block_queryset.values_list("pk", "translation_key")[: block.value["count"]])
            seen_translation_keys.update(translation_key for __, translation_key in section_articles)
            pks_by_section.append([pk for pk, __ in section_articles])

        wanted_pks = [pk for section_pks in pks_by_section for pk in section_pks]
        articles_by_pk = {}
        if wanted_pks:
            articles_by_pk = {article.pk: article for article in article_list_queryset(BlogArticlePage.objects.filter(pk__in=wanted_pks))}
            cache_localized_topics(articles_by_pk.values())

        all_url = (self.url or "") + self.reverse_subpage("all_route")
        for block, section_pks in zip(sections, pks_by_section):
            block.value._articles = [articles_by_pk[pk] for pk in section_pks if pk in articles_by_pk]
            block.value._link_url = self.get_section_link_url(block, all_url)

        return sections

    def get_section_link_url(self, block, all_url):
        """The "View all" destination for a section: its topic page, its tag filter, or
        the full list when the section has no source."""
        source = block.block.get_source(block.value)
        if source is None:
            return all_url
        if source.block_type == "topic":
            return (self.url or "") + self.reverse_subpage("topic_route", args=[source.value.slug])
        return f"{all_url}?tag={source.value.slug}"

    # Queries and filtering

    def live_articles(self):
        """Published, publicly visible articles under this index."""
        return BlogArticlePage.objects.child_of(self).live().public()

    def get_all_topics(self):
        """Topics that have at least one live article here, most-populated first."""
        return (
            BlogTopic.objects.filter(locale=self.locale, blog_articles__in=self.live_articles().values("pk"))
            .annotate(article_count=Count("blog_articles"))
            .live()
            .order_by("-article_count")
        )

    def get_feed_exclusions(self) -> FeedExclusions:
        """Topics and tags this page keeps out of automatic feeds, as translation keys.

        Matching by translation_key rather than pk keeps exclusions working in a locale
        whose feed_exclusions have not been translated yet."""
        if not hasattr(self, "_feed_exclusions_cache"):
            topic_keys = set()
            tag_keys = set()
            for block in self.feed_exclusions or []:
                if not block.value:
                    continue
                if block.block_type == "topic":
                    topic_keys.add(block.value.translation_key)
                else:
                    tag_keys.add(block.value.translation_key)
            self._feed_exclusions_cache = FeedExclusions(topic_keys, tag_keys)
        return self._feed_exclusions_cache

    def get_hidden_tag_keys(self, exempt_tag=None):
        """Excluded tags that should not render as chips, except if the tag is explicitly exempted."""
        tag_keys = self.get_feed_exclusions().tag_keys
        return tag_keys - {exempt_tag.translation_key} if exempt_tag else tag_keys

    def exclude_from_feed(self, queryset, exempt_topic_keys=(), exempt_tag_keys=()):
        """
        Exclude articles with topics or tags that are in the feed_exclusions, except for
        the ones explicitly exempted by the caller.
        """
        exclusions = self.get_feed_exclusions()
        topic_keys = exclusions.topic_keys - set(exempt_topic_keys)
        tag_keys = exclusions.tag_keys - set(exempt_tag_keys)
        if topic_keys:
            queryset = queryset.exclude(topic__translation_key__in=topic_keys)
        if tag_keys:
            queryset = queryset.exclude(tags__translation_key__in=tag_keys)
        return queryset

    def get_tag_filter(self, request):
        """The ?tag= snippet in this page's locale, or None if the parameter is absent
        or names no live tag."""
        tag_slug = request.GET.get("tag")
        if not tag_slug:
            return None
        return BlogTag.objects.filter(slug=tag_slug, locale=self.locale).live().first()

    # Context for routes

    def get_all_context(self, request):
        """Context for the all/ route: every live article, narrowed by ?topic= and ?tag=."""
        articles = article_list_queryset(self.live_articles())

        topic = None
        topic_slug = request.GET.get("topic")
        if topic_slug:
            topic = BlogTopic.objects.filter(slug=topic_slug, locale=self.locale).live().first()
            if topic:
                articles = articles.filter(topic=topic)

        tag = self.get_tag_filter(request)
        if tag:
            articles = articles.filter(tags__translation_key=tag.translation_key)

        articles = self.exclude_from_feed(
            articles,
            exempt_topic_keys={topic.translation_key} if topic else (),
            exempt_tag_keys={tag.translation_key} if tag else (),
        )

        paginator = Paginator(articles.order_by("-first_published_at"), ARTICLES_PER_PAGE)
        if topic:
            topic.article_count = paginator.count
        list_articles = paginator.get_page(request.GET.get("page", 1))
        cache_localized_tags(list_articles.object_list, self.get_hidden_tag_keys(tag))

        return {
            "list_articles": list_articles,
            "topic": topic,
            "tag": tag,
            "all_topics": self.get_all_topics(),
        }

    def get_topic_context(self, request, topic, topic_page=None):
        """Context for the topics/<slug>/ route, shared by the plain listing and by
        BlogTopicPage. Articles already shown in a curated header are dropped from the
        list before pagination, so the count matches what is rendered."""
        articles = article_list_queryset(self.live_articles()).filter(topic=topic)

        if topic_page:
            featured_values = [block.value for block in (topic_page.featured_articles or [])]
            prefetch_article_blocks(featured_values)
            featured_pks = [value["article"].pk for value in featured_values if value.get("article")]
            if featured_pks:
                articles = articles.exclude(pk__in=featured_pks)

        tag = self.get_tag_filter(request)
        if tag:
            articles = articles.filter(tags__translation_key=tag.translation_key)

        # This page's own topic is always exempt: applying its exclusion would leave
        # the page rendering nothing.
        articles = self.exclude_from_feed(
            articles,
            exempt_topic_keys={topic.translation_key},
            exempt_tag_keys={tag.translation_key} if tag else (),
        )

        paginator = Paginator(articles.order_by("-first_published_at"), ARTICLES_PER_PAGE)
        topic.article_count = paginator.count
        list_articles = paginator.get_page(request.GET.get("page", 1))
        cache_localized_tags(list_articles.object_list, self.get_hidden_tag_keys(tag))

        return {
            "blog_index": self,
            "topic": topic,
            "all_topics": self.get_all_topics(),
            "topic_page": topic_page,
            "list_articles": list_articles,
            "tag": tag,
        }

    def get_header_topics(self):
        """Topics for the page header: the editor-selected featured topics, or the
        topics with the most articles when none are selected.
        """
        selected_topics = [block.value for block in (self.featured_topics or []) if block.value]
        if not selected_topics:
            return list(self.get_all_topics()[:MAX_HEADER_TOPICS])

        localized_topics = BlogTopic.objects.filter(
            translation_key__in=[topic.translation_key for topic in selected_topics],
            locale_id=self.locale_id,
        ).live()
        localized_topics_by_key = {topic.translation_key: topic for topic in localized_topics}

        return [localized_topics_by_key[topic.translation_key] for topic in selected_topics if topic.translation_key in localized_topics_by_key]

    # Serving and routing

    def serve(self, request, view=None, args=None, kwargs=None):
        # Make sure to always go through the routes, so that each route is responsible for its own context.
        # No shared get_context method is used, so that each route only fetches what it needs.
        if view is None:
            view = self.index_route
        return super().serve(request, view=view, args=args, kwargs=kwargs)

    def serve_preview(self, request, *args, **kwargs):
        request.is_preview = True
        return super().serve_preview(request, *args, **kwargs)

    def _render_route(self, request, template, extra_context=None):
        request.is_preview = False
        request = self._patch_request_for_springfield(request)
        context = self.get_context(request)
        if extra_context:
            context.update(extra_context)
        return l10n_utils.render(request, template, context, ftl_files=self.ftl_files)

    @path("")
    def index_route(self, request):
        prefetch_article_blocks([block.value for block in (self.featured_articles or [])])
        sections = self.resolve_article_sections()
        extra_context = {
            "header_topics": self.get_header_topics(),
            "article_sections": [block for block in sections if block.block_type != "latest"],
            "latest_section": next((block for block in sections if block.block_type == "latest"), None),
            "is_preview": getattr(request, "is_preview", False),
        }
        return self._render_route(request, self.get_template(request), extra_context=extra_context)

    @path("topics/")
    def topics_route(self, request):
        extra_context = {"all_topics": self.get_all_topics()}
        return self._render_route(request, "blog/blog_topics_page.html", extra_context=extra_context)

    @path("topics/<slug:topic_slug>/")
    def topic_route(self, request, topic_slug):
        # Inline import: snippets and pages import from each other at module scope.
        topic = BlogTopic.objects.filter(slug=topic_slug, locale=self.locale).live().first()
        if topic is None:
            raise Http404

        topic_page = BlogTopicPage.objects.child_of(self).live().public().filter(topic=topic).first()
        if topic_page:
            return topic_page.serve(request)

        return self._render_route(request, "blog/blog_topic_page.html", self.get_topic_context(request, topic))

    @path("all/")
    def all_route(self, request):
        return self._render_route(request, "blog/blog_all_page.html", self.get_all_context(request))

    def get_sitemap_urls(self, request=None):
        """Add the URLs this page serves through its routes, which have no Page of their own
        for the sitemap to find.
        """
        urls = super().get_sitemap_urls(request=request)
        page_entry = urls[0]
        if not page_entry["location"]:
            return urls

        route_paths = ["topics/", "all/", *(f"topics/{topic.slug}/" for topic in self.get_all_topics())]
        urls.extend(page_entry | {"location": f"{page_entry['location']}{route_path}"} for route_path in route_paths)
        return urls


class BlogTopicPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """An editor-curated header for one blog topic.

    Served by BlogIndexPage.topic_route at topics/<slug>/ in place of the plain topic
    heading. The automatic article list still renders below it."""

    parent_page_types = ["blog.BlogIndexPage"]
    subpage_types = []
    ftl_files = ["blog/blog"]

    topic = models.ForeignKey(
        "blog.BlogTopic",
        on_delete=models.PROTECT,
        related_name="topic_pages",
    )
    page_heading = StreamField(
        [("heading", HeadingBlock())],
        max_num=1,
        use_json_field=True,
        blank=True,
    )
    featured_articles = StreamField(
        [("article", BlogArticleBlock())],
        max_num=4,
        use_json_field=True,
        blank=True,
        help_text="Up to 4 featured articles shown at the top. These are left out of the list below.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("topic"),
        FieldPanel("page_heading"),
        FieldPanel("featured_articles"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("page_heading"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Blog Topic Page"
        verbose_name_plural = "Blog Topic Pages"

    def __str__(self):
        return f"BlogTopicPage: {self.title} - {self.locale}"

    def clean(self):
        """Reject a second page for a topic another page already covers.

        A clean() check rather than a database constraint: Wagtail's copy and translate
        flows create rows that a hard constraint would reject with an opaque
        IntegrityError."""
        super().clean()
        if self.topic_id is None:
            return
        duplicate = BlogTopicPage.objects.filter(topic_id=self.topic_id, locale_id=self.locale_id).exclude(pk=self.pk).first()
        if duplicate:
            raise ValidationError({"topic": f'"{duplicate.title}" already covers this topic.'})

    def get_url_parts(self, request=None):
        """Report the topics/<slug>/ route URL rather than this page's own tree path, so
        page.url, the canonical tag, the admin's view-live link and the sitemap all agree
        with where the page is actually served."""
        parent = self.get_parent()
        if parent is None or self.topic_id is None:
            return super().get_url_parts(request)
        parent_parts = parent.get_url_parts(request)
        if parent_parts is None:
            return super().get_url_parts(request)
        site_id, root_url, parent_path = parent_parts
        return (site_id, root_url, f"{parent_path}topics/{self.topic.slug}/")

    def route(self, request, path_components):
        """Refuse to serve at this page's own tree path, so topics/<slug>/ is the only URL
        for this content. BlogIndexPage.topic_route reaches it through serve(), and the
        admin previews it through serve_preview(); neither goes through route()."""
        raise Http404

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        blog_index = self.get_parent().specific
        context.update(blog_index.get_topic_context(request, self.topic, topic_page=self))
        return context

    def get_template(self, request, *args, **kwargs):
        return "blog/blog_topic_page.html"


class HeroStyle(models.TextChoices):
    STANDARD_IMAGE = "standard_image", "Standard image"
    LARGE_IMAGE = "large_image", "Large featured image"
    TEXT_ONLY = "text_only", "No image, text only"
    VIDEO = "video", "Featured video"


MAX_RELATED_ARTICLES = 4


class BlogArticlePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays a single blog article."""

    parent_page_types = ["blog.BlogIndexPage"]
    ftl_files = ["blog/blog"]

    description = RichTextField(
        blank=True,
        features=HEADING_TEXT_FEATURES,
        help_text="A short description used on the index page.",
    )
    updated_date = models.DateField(
        null=True,
        blank=True,
        help_text="Shown as “Last updated on …”. Leave empty to show only the published date.",
    )
    hide_dates = models.BooleanField(
        default=False,
        help_text="Hide the published and updated dates on this article.",
    )
    hero_style = models.CharField(
        max_length=32,
        choices=HeroStyle,
        default=HeroStyle.STANDARD_IMAGE,
        help_text="Layout for the article header.",
    )
    hero_video = StreamField(
        [("video", VideoBlock())],
        max_num=1,
        use_json_field=True,
        null=True,
        blank=True,
        help_text="Video shown in the header when the hero style is “Featured video”.",
    )

    # Null so rows without a topic remain valid; blank stays False (the
    # default) so the Wagtail admin form still requires one.
    topic = models.ForeignKey(
        "blog.BlogTopic",
        null=True,
        on_delete=models.PROTECT,
        related_name="blog_articles",
    )
    tags = LocalizedClusterTaggableManager(through="blog.TaggedBlogArticle", blank=True)
    image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    image_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode variant of the article image.",
    )
    image_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional mobile variant of the article image.",
    )
    image_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode mobile variant of the article image.",
    )
    listing_image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional image for article cards and lists. Falls back to the featured image.",
    )
    content = StreamField(
        [
            ("text", RichTextBlock(features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL)),
            ("media", MediaBlock()),
            ("image_caption", ImageCaptionBlock()),
            ("code", CodeBlock()),
            ("quote", QuoteBlock()),
            (
                "cards_list",
                CardsListBlock(
                    template="blog/blocks/sections/blog-article-cards-list.html",
                    help_text="Some settings may be ignored in favor of the page layout.",
                ),
            ),
        ],
        use_json_field=True,
    )
    bottom_banner = StreamField(
        [
            ("banner", BannerBlock()),
        ],
        use_json_field=True,
        blank=True,
        max_num=1,
        help_text="Optional banner to be displayed at the bottom of the article content.",
    )
    related_articles = StreamField(
        [("article", BlogRelatedArticleBlock())],
        max_num=MAX_RELATED_ARTICLES,
        use_json_field=True,
        blank=True,
        help_text=(
            f"Up to {MAX_RELATED_ARTICLES} related articles shown at the bottom. Remaining empty slots are filled with articles "
            f"that match by topic and tag, then topic, then tag, up to {MAX_RELATED_ARTICLES}."
        ),
    )
    hide_related = models.BooleanField(
        default=False,
        help_text="Hide the Related Articles section on this article.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("description"),
        MultiFieldPanel(
            [
                FieldPanel("topic"),
                FieldPanel("tags"),
            ],
            heading="Topic & Tags",
        ),
        InlinePanel("article_authors", label="Authors"),
        MultiFieldPanel(
            [
                FieldPanel("first_published_at"),
                FieldPanel("updated_date"),
                FieldPanel("hide_dates"),
            ],
            heading="Dates",
        ),
        MultiFieldPanel(
            [
                FieldPanel("image"),
                FieldRowPanel(
                    [
                        FieldPanel("image_dark_mode"),
                        FieldPanel("image_mobile"),
                        FieldPanel("image_dark_mode_mobile"),
                    ]
                ),
                FieldPanel("listing_image"),
            ],
            heading="Featured Image",
        ),
        MultiFieldPanel(
            [
                FieldPanel("hero_style"),
                FieldPanel("hero_video"),
            ],
            heading="Hero Options",
            classname="collapsed",
        ),
        FieldPanel("content"),
        FieldPanel("bottom_banner"),
    ]

    related_articles_panels = [
        FieldPanel("hide_related"),
        FieldPanel("related_articles"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    # Drops show_in_menus, unused by the CMS
    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
            ],
            heading="For search engines",
        ),
        FieldPanel("og_image"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(related_articles_panels, heading="Related Articles"),
            ObjectList(promote_panels, heading="Promote & SEO"),
            ObjectList(settings_panels, heading="Settings"),
        ]
    )

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("description"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Blog Article Page"
        verbose_name_plural = "Blog Article Pages"

    def __str__(self):
        return f"BlogArticlePage: {self.title} - {self.locale}"

    def clean(self):
        """Reject a hero style whose asset is missing, keyed to the field the editor
        has to fill in."""
        super().clean()
        if self.hero_style in (HeroStyle.STANDARD_IMAGE, HeroStyle.LARGE_IMAGE) and not self.image_id:
            raise ValidationError({"image": "This hero style needs a featured image."})
        if self.hero_style == HeroStyle.VIDEO and not self.hero_video:
            raise ValidationError({"hero_video": "This hero style needs a video."})

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        if not self.hide_related:
            related = self.get_related_articles()
            context["related_articles"] = list(related)
        else:
            context["related_articles"] = []
        return context

    def get_topic(self):
        if not hasattr(self, "_topic_cache"):
            if self.topic:
                self._topic_cache = self.topic.get_localized()
            else:
                self._topic_cache = None
        return self._topic_cache

    def get_tags(self):
        if not hasattr(self, "_tags_cache"):
            self._tags_cache = [localized for tag in self.tags.all() if (localized := tag.get_localized())]
        return self._tags_cache

    def get_authors(self):
        """The article's authors in editor order, localized where a live translation
        exists and falling back to the stored author otherwise. Authors that are not
        live in any usable locale are omitted."""
        if not hasattr(self, "_authors_cache"):
            self._authors_cache = [
                resolved
                for placement in self.article_authors.select_related("author")
                if (resolved := placement.author.get_localized() or (placement.author if placement.author.live else None))
            ]
        return self._authors_cache

    def get_listing_image(self):
        """The image for cards and list items. Fall back to the featured image."""
        return self.listing_image or self.image

    def get_listing_image_variants(self):
        """Dark and mobile variants for the listing image. Only available for the featured image."""
        if self.listing_image_id:
            return SimpleNamespace(dark_mode=None, mobile=None, dark_mode_mobile=None)
        return SimpleNamespace(
            dark_mode=self.image_dark_mode,
            mobile=self.image_mobile,
            dark_mode_mobile=self.image_dark_mode_mobile,
        )

    def get_related_articles(self):
        """Up to MAX_RELATED_ARTICLES published, publicly-visible articles
        shown below the article:

        - `related_articles` in their chosen order,
        - then siblings sharing this article's topic and one of its tags,
        - then its topic,
        - then one of its tags.

        Each automatic group is ordered by publication date, descending. No
        article is shown twice, and an article never shows itself."""
        related = []
        related_ids = {self.pk}
        for block in self.related_articles:
            article = block.value.get_article()
            if article is None or not article.live or article.pk in related_ids:
                continue
            related.append(article)
            related_ids.add(article.pk)
        if related:
            # Apply potential page view restrictions
            public_article_ids = set(BlogArticlePage.objects.public().filter(pk__in=[article.pk for article in related]).values_list("pk", flat=True))
            related = [article for article in related if article.pk in public_article_ids]
        if len(related) == MAX_RELATED_ARTICLES:
            return related

        tag_ids = [tag.pk for tag in self.tags.all()]
        shares_topic = Q(topic_id=self.topic_id) if self.topic_id else Q(topic_id__in=[])
        shares_tag = Q(carries_a_matching_tag=True)
        matching_siblings = (
            BlogArticlePage.objects.sibling_of(self)
            .live()
            .public()
            .exclude(pk__in=related_ids)
            .annotate(carries_a_matching_tag=Exists(BlogArticlePage.objects.filter(pk=OuterRef("pk"), tags__in=tag_ids)))
            .filter(shares_topic | shares_tag)
            .annotate(
                related_rank=Case(
                    When(shares_topic & shares_tag, then=Value(0)),
                    When(shares_topic, then=Value(1)),
                    default=Value(2),  # `shares_tag`
                )
            )
            .prefetch_related("tags")
            .order_by("related_rank", "-first_published_at")
        )
        related.extend(matching_siblings[: MAX_RELATED_ARTICLES - len(related)])
        return related


class BlogArticleAuthor(Orderable):
    page = ParentalKey("blog.BlogArticlePage", on_delete=models.CASCADE, related_name="article_authors")
    author = models.ForeignKey("blog.BlogAuthor", on_delete=models.PROTECT, related_name="+")

    class Meta(Orderable.Meta):
        verbose_name = "Blog Article Author"
        verbose_name_plural = "Blog Article Authors"

    panels = [
        FieldPanel("author"),
    ]

    def __str__(self):
        return f"{self.page.title} -> {self.author.name}"
