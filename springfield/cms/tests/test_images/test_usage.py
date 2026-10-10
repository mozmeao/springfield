# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

import pytest
from wagtail.models import Locale, ReferenceIndex

from springfield.blog.models import BlogAuthor
from springfield.cms.images.usage import UsageGroup, get_image_usages
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


def test_translations_of_a_page_fold_into_one_group(make_image, root_page):
    image = make_image()
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
    ReferenceIndex.create_or_update_for_object(french_page)
    ReferenceIndex.create_or_update_for_object(english_page)

    usage = get_image_usages([image])[image.pk]

    assert usage.groups == [
        UsageGroup(
            title="Firefox Home",
            edit_url=reverse("wagtailadmin_pages:edit", args=[english_page.pk]),
            locale_count=2,
            is_snippet=False,
        )
    ]
    assert usage.more_count == 0


def test_pages_are_listed_before_snippets(make_image, root_page):
    image = make_image()
    author = BlogAuthor.objects.create(name="Ada", slug="ada", image=image, locale=Locale.get_default())
    page = SimpleRichTextPageFactory(parent=root_page, slug="zeta", title="Zeta", og_image=image)
    ReferenceIndex.create_or_update_for_object(author)
    ReferenceIndex.create_or_update_for_object(page)

    usage = get_image_usages([image])[image.pk]

    assert usage.groups == [
        UsageGroup(title="Zeta", edit_url=reverse("wagtailadmin_pages:edit", args=[page.pk]), locale_count=1, is_snippet=False),
        UsageGroup(
            title=str(author),
            edit_url=reverse("wagtailsnippets_blog_blogauthor:edit", args=[author.pk]),
            locale_count=1,
            is_snippet=True,
        ),
    ]


def test_groups_beyond_the_limit_are_counted(make_image, root_page):
    image = make_image()
    for title in ("Charlie", "Alpha", "Bravo"):
        page = SimpleRichTextPageFactory(parent=root_page, slug=title.lower(), title=title, og_image=image)
        ReferenceIndex.create_or_update_for_object(page)

    usage = get_image_usages([image], limit=2)[image.pk]

    assert [group.title for group in usage.groups] == ["Alpha", "Bravo"]
    assert usage.more_count == 1


def test_a_reference_to_a_deleted_source_is_skipped(make_image, root_page):
    image = make_image()
    page = SimpleRichTextPageFactory(parent=root_page, slug="kept", title="Kept", og_image=image)
    stale_page = SimpleRichTextPageFactory(parent=root_page, slug="stale", title="Stale", og_image=image)
    ReferenceIndex.create_or_update_for_object(page)
    ReferenceIndex.create_or_update_for_object(stale_page)
    ReferenceIndex.objects.filter(object_id=str(stale_page.pk)).update(object_id="999999")

    usage = get_image_usages([image])[image.pk]

    assert [group.title for group in usage.groups] == ["Kept"]


def test_unused_images_have_no_entry(make_image):
    image = make_image()

    assert get_image_usages([image]) == {}


def test_query_count_does_not_grow_with_images(make_image, root_page):
    default_locale = Locale.get_default()
    images = [make_image() for image_number in range(4)]
    for image in images:
        page = SimpleRichTextPageFactory(parent=root_page, slug=f"page-{image.pk}", title=f"Page {image.pk}", og_image=image)
        author = BlogAuthor.objects.create(name=f"Author {image.pk}", slug=f"author-{image.pk}", image=image, locale=default_locale)
        ReferenceIndex.create_or_update_for_object(page)
        ReferenceIndex.create_or_update_for_object(author)
    get_image_usages(images[:1])  # warms the ContentType cache

    with CaptureQueriesContext(connection) as one_image_queries:
        get_image_usages(images[:1])
    with CaptureQueriesContext(connection) as four_image_queries:
        get_image_usages(images)

    assert len(four_image_queries) == len(one_image_queries)
