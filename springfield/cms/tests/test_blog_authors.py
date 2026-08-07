# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import IntegrityError
from django.db.models import ProtectedError

import pytest
from wagtail.models import Locale, Site
from wagtail_localize.fields import TranslatableField, get_translatable_fields

from springfield.cms.models import BlogArticleAuthor, BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTopic

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def article(minimal_site):
    """One blog article carrying nothing beyond what the page tree and validation
    require — these tests exercise the author relation, not article content."""
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = root_page.add_child(instance=BlogIndexPage(title="Blog", slug="blog"))
    topic = BlogTopic.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())
    return index_page.add_child(instance=BlogArticlePage(title="Article", slug="article", topic=topic))


def make_author(name, slug, **kwargs):
    return BlogAuthor.objects.create(name=name, slug=slug, locale=Locale.get_default(), **kwargs)


def test_same_author_slug_allowed_in_two_locales():
    """Slug is the author's identity within a locale, so the same person can exist
    once per language without the slugs colliding."""
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")

    en_author = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=Locale.get_default())
    fr_author = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=fr_locale)

    assert en_author.pk != fr_author.pk


def test_duplicate_author_slug_in_one_locale_is_rejected():
    BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=Locale.get_default())

    with pytest.raises(IntegrityError):
        BlogAuthor.objects.create(name="Ada Lovelace Again", slug="ada-lovelace", locale=Locale.get_default())


def test_two_authors_in_one_locale_can_share_a_name():
    """Two people can genuinely share a name; the slug is what distinguishes them."""
    first = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=Locale.get_default())
    second = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace-2", locale=Locale.get_default())

    assert first.pk != second.pk


def test_only_name_is_required():
    author = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=Locale.get_default())

    assert author.job_title == ""
    assert author.bio == ""
    assert author.email == ""
    assert author.image is None


def test_author_prose_is_translated_and_the_rest_synchronized():
    """Name and prose get translated; slug, email and image are the same person's
    details in every locale, so translators should never be handed a URL key or an
    image reference."""
    translatable_names = {field.field_name for field in get_translatable_fields(BlogAuthor) if isinstance(field, TranslatableField)}

    assert translatable_names == {"name", "job_title", "bio"}


def test_get_authors_returns_authors_in_editor_order(article):
    ada = make_author("Ada Lovelace", "ada-lovelace")
    grace = make_author("Grace Hopper", "grace-hopper")

    article.article_authors.set([BlogArticleAuthor(author=grace), BlogArticleAuthor(author=ada)])
    article.save()

    assert [author.name for author in article.get_authors()] == ["Grace Hopper", "Ada Lovelace"]


def test_get_authors_is_empty_without_authors(article):
    assert article.get_authors() == []


def test_get_authors_caches_its_result(article, django_assert_num_queries):
    article.article_authors.set([BlogArticleAuthor(author=make_author("Ada Lovelace", "ada-lovelace"))])
    article.save()

    article.get_authors()
    with django_assert_num_queries(0):
        article.get_authors()


def test_deleting_a_credited_author_is_blocked(article):
    """PROTECT is what stops an editor deleting a person who is still credited on a
    published article, which would otherwise silently drop the byline."""
    ada = make_author("Ada Lovelace", "ada-lovelace")
    article.article_authors.set([BlogArticleAuthor(author=ada)])
    article.save()

    with pytest.raises(ProtectedError):
        ada.delete()


def test_deleting_an_uncredited_author_succeeds():
    ada = make_author("Ada Lovelace", "ada-lovelace")

    ada.delete()

    assert not BlogAuthor.objects.filter(slug="ada-lovelace").exists()
