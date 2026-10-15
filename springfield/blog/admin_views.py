# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import F
from django.forms import CheckboxSelectMultiple
from django.http import JsonResponse
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.functional import cached_property

from django_filters.filters import ModelMultipleChoiceFilter
from wagtail.admin.ui.tables.pages import PageTitleColumn
from wagtail.admin.views.pages.listing import IndexView, PageFilterSet
from wagtail.admin.views.tags import TAGS_AUTOCOMPLETE_LIMIT
from wagtail.admin.widgets.button import HeaderButton
from wagtail.models import Locale, Page

from springfield.blog.models import BlogArticlePage, BlogTag, BlogTopic


def blog_tag_autocomplete(request):
    """Tag autocomplete scoped to published default-locale BlogTags."""
    term = request.GET.get("term", None)
    if not term:
        return JsonResponse([], safe=False)

    names = (
        BlogTag.objects.filter(name__istartswith=term, locale=Locale.get_default())
        .live()
        .order_by("name")
        .values_list("name", flat=True)[:TAGS_AUTOCOMPLETE_LIMIT]
    )
    return JsonResponse(list(names), safe=False)


class BlogPostFilterSet(PageFilterSet):
    topic = ModelMultipleChoiceFilter(
        label="Topic",
        queryset=lambda request: BlogTopic.objects.filter(locale=Locale.get_default()).order_by("name"),
        widget=CheckboxSelectMultiple,
    )

    class Meta:
        model = BlogArticlePage
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "locale" in self.filters:
            self.filters["locale"].label = "Language"


class BlogPostIndexView(IndexView):
    default_ordering = "-first_published_at"
    page_title = "All posts"
    add_item_label = "New post"

    @cached_property
    def workspace_url(self):
        return reverse("cms_workspace", args=["blog"])

    def get_breadcrumbs_items(self):
        return [*self.breadcrumbs_items, {"url": self.workspace_url, "label": "Blog"}, {"url": "", "label": self.get_page_title()}]

    @cached_property
    def header_buttons(self):
        return [HeaderButton("Back to Blog workspace", url=self.workspace_url, icon_name="arrow-left"), *super().header_buttons]

    def get_base_queryset(self):
        return super().get_base_queryset().select_related("topic", "locale")

    def get_filterset_kwargs(self):
        kwargs = super().get_filterset_kwargs()
        if "locale" not in kwargs["data"]:
            kwargs["data"] = kwargs["data"].copy()
            kwargs["data"]["locale"] = Locale.get_default().language_code
        return kwargs

    def get_table(self, object_list):
        annotate_other_languages(object_list)
        return super().get_table(object_list)

    def order_queryset(self, queryset):
        if self.ordering in ("first_published_at", "-first_published_at") and not self.is_searching:
            field = F("first_published_at")
            return queryset.order_by(field.desc(nulls_last=True) if self.ordering.startswith("-") else field.asc(nulls_last=True))
        return super().order_queryset(queryset)


class PostTitleColumn(PageTitleColumn):
    cell_template_name = "wagtailadmin/workspaces/_post_title_cell.html"


def annotate_other_languages(pages):
    pages = list(pages)
    by_key = {}
    for translation in Page.objects.filter(translation_key__in={page.translation_key for page in pages}).select_related("locale"):
        by_key.setdefault(translation.translation_key, []).append(translation.locale)
    for page in pages:
        page.other_languages = sorted(
            (locale for locale in by_key.get(page.translation_key, []) if locale.pk != page.locale_id), key=lambda locale: locale.language_code
        )


def translations_display(page):
    return ", ".join(locale.get_display_name() for locale in getattr(page, "other_languages", []))


def post_date_display(page):
    return date_format(page.first_published_at) if page.first_published_at else "Not published"
