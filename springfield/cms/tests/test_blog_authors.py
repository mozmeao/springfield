# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import translation

import pytest
from wagtail.models import Locale, Site
from wagtail_localize.fields import TranslatableField, get_translatable_fields

from springfield.cms.management.commands.link_translations_after_export import TRANSLATABLE_SNIPPET_MODELS
from springfield.cms.models import BlogArticleAuthor, BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTopic
from springfield.cms.wagtail_hooks import BlogAuthorChooseView

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def article(minimal_site):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = root_page.add_child(instance=BlogIndexPage(title="Blog", slug="blog"))
    topic = BlogTopic.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())
    return index_page.add_child(instance=BlogArticlePage(title="Article", slug="article", topic=topic))


def make_author(name, slug, **kwargs):
    return BlogAuthor.objects.create(name=name, slug=slug, locale=Locale.get_default(), **kwargs)


def test_same_author_slug_allowed_in_two_locales():
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")

    en_author = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=Locale.get_default())
    fr_author = BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=fr_locale)

    assert en_author.pk != fr_author.pk


def test_duplicate_author_slug_in_one_locale_is_rejected():
    BlogAuthor.objects.create(name="Ada Lovelace", slug="ada-lovelace", locale=Locale.get_default())

    with pytest.raises(IntegrityError):
        BlogAuthor.objects.create(name="Ada Lovelace Again", slug="ada-lovelace", locale=Locale.get_default())


def test_two_authors_in_one_locale_can_share_a_name():
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
    ada = make_author("Ada Lovelace", "ada-lovelace")
    article.article_authors.set([BlogArticleAuthor(author=ada)])
    article.save()

    with pytest.raises(ProtectedError):
        ada.delete()


def test_deleting_an_uncredited_author_succeeds():
    ada = make_author("Ada Lovelace", "ada-lovelace")

    ada.delete()

    assert not BlogAuthor.objects.filter(slug="ada-lovelace").exists()


def test_get_authors_returns_the_translated_author(article):
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    ada = make_author("Ada Lovelace", "ada-lovelace")
    fr_ada = ada.copy_for_translation(fr_locale)
    fr_ada.name = "Ada Lovelace en français"
    fr_ada.live = True
    fr_ada.save()

    article.article_authors.set([BlogArticleAuthor(author=ada)])
    article.save()

    with translation.override("fr"):
        article_fresh = BlogArticlePage.objects.get(pk=article.pk)
        assert [author.name for author in article_fresh.get_authors()] == ["Ada Lovelace en français"]


def test_get_authors_falls_back_to_the_default_locale_author(article):
    Locale.objects.get_or_create(language_code="fr")
    article.article_authors.set([BlogArticleAuthor(author=make_author("Ada Lovelace", "ada-lovelace"))])
    article.save()

    with translation.override("fr"):
        article_fresh = BlogArticlePage.objects.get(pk=article.pk)
        assert [author.name for author in article_fresh.get_authors()] == ["Ada Lovelace"]


def test_get_authors_falls_back_when_the_translation_is_not_live(article):
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    ada = make_author("Ada Lovelace", "ada-lovelace")
    fr_ada = ada.copy_for_translation(fr_locale)
    fr_ada.name = "Ada Lovelace en français"
    fr_ada.live = False
    fr_ada.save()

    article.article_authors.set([BlogArticleAuthor(author=ada)])
    article.save()

    with translation.override("fr"):
        article_fresh = BlogArticlePage.objects.get(pk=article.pk)
        assert [author.name for author in article_fresh.get_authors()] == ["Ada Lovelace"]


def test_get_authors_omits_an_unpublished_author(article):
    article.article_authors.set([BlogArticleAuthor(author=make_author("Ada Lovelace", "ada-lovelace", live=False))])
    article.save()

    assert article.get_authors() == []


def test_author_chooser_offers_only_live_default_locale_authors():
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    ada = make_author("Ada Lovelace", "ada-lovelace")
    BlogAuthor.objects.create(name="Ada en français", slug="ada-fr", locale=fr_locale)
    make_author("Draft Author", "draft-author", live=False)

    view = BlogAuthorChooseView()
    view.model_class = BlogAuthor

    assert list(view.get_object_list()) == [ada]


def test_author_chooser_modal_lists_only_live_default_locale_authors(admin_client):
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    make_author("Ada Lovelace", "ada-lovelace")
    BlogAuthor.objects.create(name="Ada en français", slug="ada-fr", locale=fr_locale)
    make_author("Draft Author", "draft-author", live=False)

    response = admin_client.get(reverse("wagtailsnippetchoosers_cms_blogauthor:choose"))

    assert response.status_code == 200
    rendered = response.json()["html"]
    assert "Ada Lovelace" in rendered
    assert "Ada en français" not in rendered
    assert "Draft Author" not in rendered


def test_blog_authors_are_included_in_the_db_export():
    export_script = (settings.ROOT_PATH / "bin" / "export-db-to-sqlite.sh").read_text()

    assert "cms.BlogAuthor" in export_script
    assert "cms.BlogArticleAuthor" in export_script


def test_blog_authors_are_relinked_after_export():
    assert BlogAuthor in TRANSLATABLE_SNIPPET_MODELS
