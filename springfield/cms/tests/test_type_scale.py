# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.blog.models.pages import BlogArticlePage, BlogIndexPage, BlogTopicPage
from springfield.cms.models import (
    ArticleDetailPage,
    ArticleIndexPage,
    ArticleThemePage,
    ContactPage,
    DownloadPage,
    FlareDocsIndexPage,
    FreeFormPage2026,
    HomePage,
    RoadmapPage,
    SmartWindowExplainerPage,
    WhatsNewPage2026,
)
from springfield.cms.models.base import TypeScale
from springfield.cms.models.pages import ENTERPRISE_THEME
from springfield.cms.tests.factories import FreeFormPage2026Factory

pytestmark = [pytest.mark.django_db]

COMPACT_SCALE = "fl-scale-compact"


def body_classes(content):
    body = BeautifulSoup(content, "html.parser").find("body")
    assert body
    return body.get("class", [])


@pytest.mark.parametrize(
    "page_model, fields, expected_class",
    [
        pytest.param(HomePage, {}, "", id="home"),
        pytest.param(DownloadPage, {}, "", id="download"),
        pytest.param(ArticleThemePage, {}, "", id="article-theme"),
        pytest.param(FreeFormPage2026, {}, "", id="freeform"),
        pytest.param(FreeFormPage2026, {"type_scale": TypeScale.COMPACT}, COMPACT_SCALE, id="freeform-compact"),
        pytest.param(FreeFormPage2026, {"theme": ENTERPRISE_THEME}, COMPACT_SCALE, id="freeform-enterprise"),
        pytest.param(WhatsNewPage2026, {}, "", id="whats-new"),
        pytest.param(WhatsNewPage2026, {"theme": ENTERPRISE_THEME}, COMPACT_SCALE, id="whats-new-enterprise"),
        pytest.param(ContactPage, {}, COMPACT_SCALE, id="contact"),
        pytest.param(ArticleIndexPage, {}, COMPACT_SCALE, id="article-index"),
        pytest.param(ArticleDetailPage, {}, COMPACT_SCALE, id="article-detail"),
        pytest.param(RoadmapPage, {}, COMPACT_SCALE, id="roadmap"),
        pytest.param(SmartWindowExplainerPage, {}, COMPACT_SCALE, id="smart-window-explainer"),
        pytest.param(FlareDocsIndexPage, {}, COMPACT_SCALE, id="flare-docs-index"),
        pytest.param(BlogIndexPage, {}, COMPACT_SCALE, id="blog-index"),
        pytest.param(BlogTopicPage, {}, COMPACT_SCALE, id="blog-topic"),
        pytest.param(BlogArticlePage, {}, COMPACT_SCALE, id="blog-article"),
    ],
)
def test_page_type_scale_class(page_model, fields, expected_class):
    assert page_model(**fields).type_scale_class == expected_class


def test_freeform_type_scale_sets_body_class(rf):
    page = FreeFormPage2026Factory(parent=Site.objects.get(is_default_site=True).root_page, type_scale=TypeScale.COMPACT)

    response = page.serve(rf.get(page.get_full_url()))

    assert response.status_code == 200
    assert COMPACT_SCALE in body_classes(response.content)


@pytest.mark.parametrize(
    "page_model, has_field",
    [
        pytest.param(FreeFormPage2026, True, id="freeform"),
        pytest.param(WhatsNewPage2026, False, id="whats-new"),
        pytest.param(ArticleDetailPage, False, id="article-detail"),
        pytest.param(RoadmapPage, False, id="roadmap"),
    ],
)
def test_type_scale_field_in_editor(page_model, has_field):
    form_fields = page_model.get_edit_handler().get_form_class().base_fields

    assert ("type_scale" in form_fields) is has_field


@pytest.mark.parametrize(
    "url, uses_compact",
    [
        ("/en-US/landing/get/", False),
        ("/en-US/channel/desktop/", True),
        ("/en-US/download/all/", True),
        ("/en-US/landing/set-as-default/", True),
        ("/en-US/privacy/websites/cookie-settings/", True),
        ("/en-US/newsletter/", True),
    ],
)
def test_django_page_type_scale(url, uses_compact, client):
    response = client.get(url, follow=True)

    assert response.status_code == 200
    assert (COMPACT_SCALE in body_classes(response.content)) is uses_compact
