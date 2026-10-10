# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, ReferenceIndex

from springfield.blog.models import BlogAuthor
from springfield.cms.images.views import SpringfieldImageIndexView
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


def test_list_layout_renders_editable_rows_and_usage(admin_client, make_image, root_page):
    image = make_image()
    image.tags.add("brand")
    french = LocaleFactory(language_code="fr")
    english_page = SimpleRichTextPageFactory(parent=root_page, slug="firefox-home", title="Firefox Home", og_image=image)
    french_page = SimpleRichTextPageFactory(
        parent=root_page,
        slug="accueil-firefox",
        title="Accueil Firefox",
        locale=french,
        translation_key=english_page.translation_key,
        og_image=image,
    )
    author = BlogAuthor.objects.create(name="Ada", slug="ada", image=image, locale=Locale.get_default())
    for source in (english_page, french_page, author):
        ReferenceIndex.create_or_update_for_object(source)

    response = admin_client.get(reverse("wagtailimages:index"), {"layout": "list"})

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    row = soup.select_one(f"form#image-inline-{image.pk}").find_parent("tr")
    assert [cell["data-inline-cell"] for cell in row.select("td[data-inline-cell]")] == [
        "title",
        "description",
        "is_decorative",
        "tags",
        "usage",
        "save",
    ]
    cells = row.find_all("td", recursive=False)
    assert cells[-3]["data-inline-cell"] == "save"
    assert cells[-2].get_text(strip=True) == "Root"
    assert row.select_one(f"input[name='image-{image.pk}-title']")["value"] == "Firefox logo"
    assert row.select_one(f"input[name='image-{image.pk}-tags']")["value"] == "brand"
    assert row.select_one("td[data-inline-cell='title'] a")["href"] == reverse("wagtailimages:edit", args=[image.pk])
    assert row.select_one(f"textarea[name='image-{image.pk}-description']").get_text(strip=True) == "The Firefox logo"
    usage_items = row.select("td[data-inline-cell='usage'] li")
    assert usage_items[0].get_text(" ", strip=True) == "Firefox Home · 2 locales"
    assert usage_items[0].a["href"] == reverse("wagtailadmin_pages:edit", args=[english_page.pk])
    assert usage_items[1].get_text(" ", strip=True) == f"{author} Snippet"


def test_list_layout_links_to_full_usage_beyond_five_groups(admin_client, make_image, root_page):
    image = make_image()
    for page_number in range(6):
        page = SimpleRichTextPageFactory(parent=root_page, slug=f"page-{page_number}", title=f"Page {page_number}", og_image=image)
        ReferenceIndex.create_or_update_for_object(page)
    unused_image = make_image(title="Unused logo")

    response = admin_client.get(reverse("wagtailimages:index"), {"layout": "list"})

    soup = BeautifulSoup(response.content, "html.parser")
    usage_cell = soup.select_one(f"form#image-inline-{image.pk}").find_parent("tr").select_one("td[data-inline-cell='usage']")
    assert len(usage_cell.select("li")) == 5
    assert usage_cell.select("a")[-1].get_text(strip=True) == "+1 more"
    assert usage_cell.select("a")[-1]["href"] == reverse("wagtailimages:image_usage", args=[image.pk])
    unused_usage_cell = soup.select_one(f"form#image-inline-{unused_image.pk}").find_parent("tr").select_one("td[data-inline-cell='usage']")
    assert unused_usage_cell.get_text(strip=True) == "Not used"


def test_grid_layout_renders_the_image_grid(admin_client, make_image):
    image = make_image()

    response = admin_client.get(reverse("wagtailimages:index"))

    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.select_one("ul.listing.horiz.images") is not None
    assert image.title in soup.select_one("ul.listing.horiz.images figcaption").get_text()
    assert soup.select("[data-inline-image-form]") == []


def test_search_results_in_list_layout_are_served_by_our_view(admin_client, make_image):
    image = make_image()
    results_url = reverse("wagtailimages:index_results")

    response = admin_client.get(results_url, {"layout": "list", "q": "logo"})

    assert resolve(results_url).func.view_class is SpringfieldImageIndexView
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    row = soup.select_one(f"form#image-inline-{image.pk}").find_parent("tr")
    assert row.select_one("td[data-inline-cell='usage']") is not None


def test_list_layout_query_count_does_not_grow_with_images(admin_client, make_image, root_page):
    default_locale = Locale.get_default()
    index_url = reverse("wagtailimages:index")
    image_numbers_per_round = [range(0, 2), range(2, 4)]
    query_counts = []
    for image_numbers in image_numbers_per_round:
        for image_number in image_numbers:
            image = make_image(title=f"Firefox logo {image_number}")
            image.get_rendition("max-165x165")
            page = SimpleRichTextPageFactory(parent=root_page, slug=f"page-{image_number}", title=f"Page {image_number}", og_image=image)
            author = BlogAuthor.objects.create(name=f"Author {image_number}", slug=f"author-{image_number}", image=image, locale=default_locale)
            ReferenceIndex.create_or_update_for_object(page)
            ReferenceIndex.create_or_update_for_object(author)
        admin_client.get(index_url, {"layout": "list"})  # warms per-process caches
        with CaptureQueriesContext(connection) as listing_queries:
            admin_client.get(index_url, {"layout": "list"})
        query_counts.append(len(listing_queries))

    two_images_query_count, four_images_query_count = query_counts
    assert four_images_query_count == two_images_query_count
