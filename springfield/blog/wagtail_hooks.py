# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.contenttypes.models import ContentType
from django.urls import path, reverse

from wagtail import hooks
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import BulkActionsColumn, PageStatusColumn
from wagtail.admin.viewsets.pages import PageListingViewSet
from wagtail.models import Locale as WagtailLocale
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.chooser import ChooseResultsView, ChooseView, SnippetChooserViewSet

from springfield.blog.admin_views import (
    BlogPostFilterSet,
    BlogPostIndexView,
    PostTitleColumn,
    blog_tag_autocomplete,
    post_date_display,
    translations_display,
)
from springfield.blog.models import BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTag, BlogTopic, BlogTopicPage
from springfield.cms.wagtail_hooks import LocaleDefaultingSnippetViewSet
from springfield.cms.workspaces import Workspace, WorkspaceLink


@hooks.register("register_admin_urls")
def register_blog_admin_urls():
    return [
        path("blog-tag-autocomplete/", blog_tag_autocomplete, name="blog_tag_autocomplete"),
    ]


class BlogTagViewSet(LocaleDefaultingSnippetViewSet):
    model = BlogTag
    icon = "tag"
    list_display = ["name", "locale", "live"]


class BlogTopicViewSet(LocaleDefaultingSnippetViewSet):
    model = BlogTopic
    icon = "folder-open-inverse"
    list_display = ["name", "locale", "live"]


class DefaultLocaleBlogAuthorMixin:
    """Restricts an author chooser to the rows an article is allowed to store."""

    def get_object_list(self):
        return BlogAuthor.objects.filter(locale=WagtailLocale.get_default(), live=True)


class BlogAuthorChooseView(DefaultLocaleBlogAuthorMixin, ChooseView):
    pass


class BlogAuthorChooseResultsView(DefaultLocaleBlogAuthorMixin, ChooseResultsView):
    pass


class BlogAuthorChooserViewSet(SnippetChooserViewSet):
    # Both views need the restriction: ChooseView renders the initial modal and
    # ChooseResultsView serves search and pagination within it.
    choose_view_class = BlogAuthorChooseView
    choose_results_view_class = BlogAuthorChooseResultsView


class BlogAuthorViewSet(LocaleDefaultingSnippetViewSet):
    model = BlogAuthor
    icon = "user"
    list_display = ["name", "job_title", "locale", "live"]
    search_fields = ["name"]
    chooser_viewset_class = BlogAuthorChooserViewSet


for _viewset in (
    BlogTagViewSet,
    BlogTopicViewSet,
    BlogAuthorViewSet,
):
    register_snippet(_viewset)


class BlogPostListingViewSet(PageListingViewSet):
    model = BlogArticlePage
    icon = "doc-full-inverse"
    index_view_class = BlogPostIndexView
    filterset_class = BlogPostFilterSet
    columns = [
        BulkActionsColumn("bulk_actions"),
        PostTitleColumn("title", label="Title", sort_key="title", classname="title"),
        Column("topic", label="Topic", accessor="topic.name", width="14%"),
        Column("locale", label="Language", accessor="locale.get_display_name", width="11%"),
        Column("translations", label="Translations", accessor=translations_display, width="12%"),
        Column("first_published_at", label="Post date", accessor=post_date_display, sort_key="first_published_at", width="11%"),
        DateColumn("latest_revision_created_at", label="Updated", sort_key="latest_revision_created_at", width="10%"),
        PageStatusColumn("status", label="Status", sort_key="live", width="10%"),
    ]


@hooks.register("register_admin_viewset")
def register_blog_post_listing():
    return BlogPostListingViewSet("blog_posts", url_prefix="workspaces/blog/posts")


def blog_workspace_links(root, user):
    topic_pages = ContentType.objects.get_for_model(BlogTopicPage)
    return [
        WorkspaceLink(
            label="Topic pages",
            url=f"{reverse('wagtailadmin_explore', args=[root.pk])}?content_type={topic_pages.pk}",
            icon="doc-empty-inverse",
        ),
    ]


def get_blog_root_page():
    indexes = BlogIndexPage.objects.filter(locale=WagtailLocale.get_default()).order_by("path")
    return indexes.filter(slug="blog").first() or indexes.first()


@hooks.register("register_workspace")
def register_blog_workspace():
    return Workspace(
        slug="blog",
        label="Blog",
        icon="doc-full-inverse",
        get_root_page=get_blog_root_page,
        add_page_model=BlogArticlePage,
        add_label="New post",
        snippet_models=(BlogTopic, BlogTag, BlogAuthor),
        listing_url_name="blog_posts:index",
        listing_label="All posts",
        root_edit_label="Edit blog homepage",
        get_extra_links=blog_workspace_links,
    )
