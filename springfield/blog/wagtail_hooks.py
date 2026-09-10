# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from wagtail import hooks
from wagtail.models import Locale as WagtailLocale
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.chooser import ChooseResultsView, ChooseView, SnippetChooserViewSet

from springfield.blog.admin_views import blog_tag_autocomplete
from springfield.blog.models import BlogAuthor, BlogTag, BlogTopic
from springfield.cms.wagtail_hooks import LocaleDefaultingSnippetViewSet


@hooks.register("register_admin_urls")
def register_blog_admin_urls():
    return [
        path("blog-tag-autocomplete/", blog_tag_autocomplete, name="blog_tag_autocomplete"),
    ]


class BlogTagViewSet(LocaleDefaultingSnippetViewSet):
    model = BlogTag
    list_display = ["name", "locale", "live"]


class BlogTopicViewSet(LocaleDefaultingSnippetViewSet):
    model = BlogTopic
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
    list_display = ["name", "job_title", "locale", "live"]
    search_fields = ["name"]
    chooser_viewset_class = BlogAuthorChooserViewSet


for _viewset in (
    BlogTagViewSet,
    BlogTopicViewSet,
    BlogAuthorViewSet,
):
    register_snippet(_viewset)
