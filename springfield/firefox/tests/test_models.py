# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.rich_text import RichText

from springfield.cms.tests.conftest import minimal_site  # noqa
from springfield.firefox.tests import factories

pytestmark = [
    pytest.mark.django_db,
]


@pytest.mark.parametrize("serving_method", ("serve", "serve_preview"))
def test_features_index_page(minimal_site, rf, serving_method):  # noqa
    root_page = minimal_site.root_page

    test_index_page = factories.FeaturesIndexPageFactory(
        parent=root_page,
        sub_title="Test Subtitle",
    )

    test_index_page.save()

    test_detail_pages = {}

    for i in range(1, 3):
        test_detail_pages[f"test_detail_page_{i}"] = factories.FeaturesDetailPageFactory(
            parent=test_index_page,
            slug=f"test-detail-{i}",
            desc=f"Test Featured Detail Page {i} Description",
            content=RichText(f"Test Featured Detail Page {i} Content"),
            featured_article=True,
        )
        test_detail_pages[f"test_detail_page_{i}"].save()

    for i in range(3, 13):
        test_detail_pages[f"test_detail_page_{i}"] = factories.FeaturesDetailPageFactory(
            parent=test_index_page,
            slug=f"test-detail-{i}",
            desc=f"Test Detail Page {i} Description",
            content=RichText(f"Test Detail Page {i} Content"),
        )
        test_detail_pages[f"test_detail_page_{i}"].save()

    _relative_url = test_index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/test/"
    request = rf.get(_relative_url)

    resp = getattr(test_index_page, serving_method)(request, mode_name="irrelevant")
    page_content = resp.text
    assert "Test Index Page Title" in page_content
    assert "Test Subtitle" in page_content
    assert "Test Featured Detail Page 1 Description" in page_content
    assert "Test Detail Page 12 Description" in page_content


@pytest.mark.parametrize("serving_method", ("serve", "serve_preview"))
def test_features_detail_page(minimal_site, rf, serving_method):  # noqa
    root_page = minimal_site.root_page

    call_to_action_bottom = factories.FeaturesCallToActionSnippetFactory(
        heading="Test Call To Action Bottom Heading",
        desc="Test Call To Action Bottom Description",
    )
    call_to_action_bottom.save()

    test_index_page = factories.FeaturesIndexPageFactory(
        parent=root_page,
        sub_title="Test Subtitle",
    )

    test_detail_page = factories.FeaturesDetailPageFactory(
        parent=test_index_page,
        slug="test-detail-1",
        desc="Test Detail Page Description",
        content=RichText("Test Detail Page Content"),
        article_media__0__video=factories.FeaturesVideoBlockFactory(
            title="Test Video Title",
            youtube_video_id="123456789",
        ),
        call_to_action_bottom=call_to_action_bottom,
    )

    test_index_page.save()
    test_detail_page.save()

    _relative_url = test_detail_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/test/test-detail-1/"
    request = rf.get(_relative_url)

    resp = getattr(test_detail_page, serving_method)(request, mode_name="irrelevant")
    page_content = resp.text
    assert "Test Detail Page Title" in page_content
    assert "Test Video Title" in page_content
    assert "Test Detail Page Content" in page_content
    assert "Test Call To Action Bottom Heading" in page_content
    assert "Test Call To Action Bottom Description" in page_content
