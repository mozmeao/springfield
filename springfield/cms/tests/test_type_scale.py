# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.models.pages import ArticleDetailPage, FreeFormPage2026, RoadmapPage, WhatsNewPage2026
from springfield.cms.tests.factories import (
    ArticleDetailPageFactory,
    ArticleIndexPageFactory,
    FreeFormPage2026Factory,
    RoadmapPageFactory,
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
)

pytestmark = [pytest.mark.django_db]

COMPACT_SCALE = "fl-scale-compact"


def body_classes(content):
    body = BeautifulSoup(content, "html.parser").find("body")
    assert body
    return body.get("class", [])


def make_whats_new(parent):
    index = WhatsNewIndexPageFactory(parent=parent)
    return WhatsNewPage2026Factory(parent=index)


@pytest.mark.parametrize(
    "make_page, uses_compact",
    [
        (lambda root: FreeFormPage2026Factory(parent=root), False),
        (lambda root: FreeFormPage2026Factory(parent=root, theme="enterprise", show_pre_footer=False), True),
        (lambda root: ArticleIndexPageFactory(parent=root, other_articles_heading="More"), True),
        (lambda root: ArticleDetailPageFactory(parent=root), True),
        (lambda root: RoadmapPageFactory(parent=root), True),
        (make_whats_new, False),
    ],
    ids=["freeform", "freeform-enterprise", "article-index", "article-detail", "roadmap", "whats-new"],
)
def test_cms_page_type_scale(make_page, uses_compact, rf):
    page = make_page(Site.objects.get(is_default_site=True).root_page)

    response = page.serve(rf.get(page.get_full_url()))

    assert response.status_code == 200
    assert (COMPACT_SCALE in body_classes(response.content)) is uses_compact


@pytest.mark.parametrize(
    "url, uses_compact",
    [
        ("/en-US/landing/get/", False),
        ("/en-US/channel/desktop/", True),
        ("/en-US/landing/set-as-default/", True),
        ("/en-US/privacy/websites/cookie-settings/", True),
        ("/en-US/newsletter/", True),
    ],
)
def test_django_page_type_scale(url, uses_compact, client):
    response = client.get(url, follow=True)

    assert response.status_code == 200
    assert (COMPACT_SCALE in body_classes(response.content)) is uses_compact


@pytest.mark.parametrize(
    "theme, type_scale, uses_compact",
    [
        ("", "regular", False),
        ("", "compact", True),
        ("enterprise", "regular", True),
        ("enterprise", "compact", True),
    ],
)
def test_freeform_type_scale_setting(theme, type_scale, uses_compact, rf):
    page = FreeFormPage2026Factory(
        parent=Site.objects.get(is_default_site=True).root_page,
        theme=theme,
        type_scale=type_scale,
        show_pre_footer=not theme,
    )

    response = page.serve(rf.get(page.get_full_url()))

    assert response.status_code == 200
    assert (COMPACT_SCALE in body_classes(response.content)) is uses_compact


def test_freeform_type_scale_defaults_to_regular():
    assert FreeFormPage2026().type_scale == "regular"


def test_freeform_type_scale_is_synchronised_across_locales():
    fields = [field.field_name for field in FreeFormPage2026.override_translatable_fields]
    assert "type_scale" in fields


@pytest.mark.parametrize("model", [FreeFormPage2026, WhatsNewPage2026, ArticleDetailPage, RoadmapPage])
def test_only_freeform_has_type_scale_in_editor(model):
    form_fields = model.get_edit_handler().get_form_class().base_fields
    assert ("type_scale" in form_fields) is (model is FreeFormPage2026)
