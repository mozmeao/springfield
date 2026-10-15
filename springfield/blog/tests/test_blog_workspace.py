# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import itertools
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import Http404
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

import pytest
from wagtail.models import GroupPagePermission, Locale, Site

from springfield.blog.models import BlogArticlePage, BlogIndexPage
from springfield.blog.models.pages import HeroStyle
from springfield.blog.models.snippets import BlogTopic
from springfield.cms.admin_views import WorkspaceView
from springfield.cms.workspaces import get_workspace, workspaces_menu

pytestmark = [pytest.mark.django_db]

User = get_user_model()


def workspace_url():
    return reverse("cms_workspace", args=["blog"])


@pytest.fixture
def blog_index(minimal_site):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = BlogIndexPage(title="Blog", slug="blog", locale=Locale.objects.get(language_code="en-US"))
    root_page.add_child(instance=index_page)
    return index_page


@pytest.fixture
def make_article(blog_index):
    topic = BlogTopic.objects.create(name="Privacy", slug="test-unit-privacy", locale=blog_index.locale)
    slug_numbers = itertools.count(1)

    def make_article(live=True, **fields):
        fields.setdefault("topic", topic)
        article = BlogArticlePage(
            title=fields.pop("title", "Test article"),
            slug=f"test-unit-article-{next(slug_numbers)}",
            locale=blog_index.locale,
            hero_style=HeroStyle.TEXT_ONLY,
            live=live,
            **fields,
        )
        blog_index.add_child(instance=article)
        revision = article.save_revision()
        if live:
            revision.publish()
        return article

    return make_article


@pytest.fixture
def login(client):
    """Log in as a given user with the ModelBackend (see conftest.admin_client)."""
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):

        def login(user):
            client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
            return client

        yield login


def make_staff_user(username, page=None, permissions=()):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass", is_staff=True)
    group = Group.objects.create(name=f"{username}-group")
    group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
    for codename in permissions:
        GroupPagePermission.objects.create(group=group, page=page, permission=Permission.objects.get(codename=codename))
    user.groups.add(group)
    return user


def sidebar_labels(user):
    request = RequestFactory().get(reverse("wagtailadmin_home"))
    request.user = user
    return [item.label for item in workspaces_menu.menu_items_for_request(request)]


def superuser():
    user, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@example.com", "is_staff": True, "is_superuser": True})
    return user


def test_blog_workspace_is_registered(blog_index):
    workspace = get_workspace("blog")
    assert workspace.label == "Blog"
    assert workspace.get_root_page() == blog_index
    assert workspace.url == workspace_url()


def test_superuser_sees_blog_in_workspaces_menu(blog_index):
    assert sidebar_labels(superuser()) == ["Blog"]


def test_editor_with_blog_permissions_sees_the_workspace(login, blog_index):
    user = make_staff_user("editor", blog_index, ["add_page", "change_page"])
    assert sidebar_labels(user) == ["Blog"]
    client = login(user)
    assert client.get(workspace_url()).status_code == 200


def test_staff_without_blog_permissions_doesnt_see_it(login, blog_index):
    user = make_staff_user("other")
    assert sidebar_labels(user) == []
    # Wagtail turns PermissionDenied in the admin into a redirect to the dashboard.
    response = login(user).get(workspace_url())
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")


def call_view(slug):
    request = RequestFactory().get("/")
    request.user = superuser()
    return WorkspaceView.as_view()(request, slug=slug)


def test_workspace_hidden_when_there_is_no_blog_index(minimal_site):
    assert sidebar_labels(superuser()) == []
    with pytest.raises(Http404):
        call_view("blog")


def test_unknown_workspace_is_404(blog_index):
    with pytest.raises(Http404):
        call_view("nope")


def test_workspace_page_shows_actions_counts_and_recent_edits(admin_client, blog_index, make_article):
    make_article(title="Live post")
    make_article(title="Draft post", live=False)
    scheduled = make_article(title="Scheduled post", live=False)
    revision = scheduled.save_revision()
    revision.approved_go_live_at = timezone.now() + timedelta(days=1)
    revision.save()

    response = admin_client.get(workspace_url())

    assert response.status_code == 200
    counts = {count["status"]: count["value"] for count in response.context["counts"]}
    assert counts == {"live": 1, "changes": 0, "draft": 2, "scheduled": 1}
    assert [row["page"].title for row in response.context["recent"]] == ["Scheduled post", "Draft post", "Live post"]
    assert response.context["add_url"] == reverse("wagtailadmin_pages:add", args=["blog", "blogarticlepage", blog_index.pk])
    assert [(link.label, link.icon) for link in response.context["manage_links"]] == [
        ("Blog Topics", "folder-open-inverse"),
        ("Blog Tags", "tag"),
        ("Blog Authors", "user"),
        ("Topic pages", "doc-empty-inverse"),
    ]
    assert response.context["browse_url"] == reverse("blog_posts:index")
    assert [item["label"] for item in response.context["breadcrumbs_items"]] == ["Home", "Blog"]
    content = response.content.decode()
    assert "New post" in content
    assert "Recently edited" in content


def test_counts_only_include_blog_articles(admin_client, blog_index, make_article):
    make_article()
    assert {count["status"]: count["value"] for count in admin_client.get(workspace_url()).context["counts"]}["live"] == 1
    assert BlogArticlePage.objects.count() == 1


def test_all_posts_listing_lives_under_the_workspace():
    assert reverse("blog_posts:index") == "/cms-admin/workspaces/blog/posts/"


def test_all_posts_listing_links_back_to_the_workspace(admin_client, blog_index):
    response = admin_client.get(reverse("blog_posts:index"))
    assert [item["label"] for item in response.context["breadcrumbs_items"]] == ["Home", "Blog", "All posts"]
    content = response.content.decode()
    assert "Back to Blog workspace" in content
    assert f'href="{workspace_url()}"' in content


def test_all_posts_listing_is_newest_post_date_first(admin_client, blog_index, make_article):
    older = make_article(title="Older")
    older.first_published_at = timezone.now() - timedelta(days=30)
    older.save()
    make_article(title="Never published", live=False)
    newer = make_article(title="Newer")
    newer.first_published_at = timezone.now() - timedelta(days=1)
    newer.save()

    response = admin_client.get(reverse("blog_posts:index"))

    assert response.status_code == 200
    assert [page.title for page in response.context["pages"]] == ["Newer", "Older", "Never published"]


def test_all_posts_listing_filters_by_topic(admin_client, blog_index, make_article):
    other_topic = BlogTopic.objects.create(name="AI", slug="test-unit-ai", locale=blog_index.locale)
    make_article(title="Privacy post")
    make_article(title="AI post", topic=other_topic)

    response = admin_client.get(reverse("blog_posts:index"), {"topic": other_topic.pk})

    assert [page.title for page in response.context["pages"]] == ["AI post"]


@pytest.fixture
def translated_post(blog_index, make_article):
    english = make_article(title="Profile management")
    german = english.copy_for_translation(Locale.objects.get_or_create(language_code="de")[0], copy_parents=True)
    german.title = "Profilverwaltung"
    german.save_revision().publish()
    return english, german


def test_all_posts_defaults_to_english_with_a_translations_column(admin_client, translated_post):
    response = admin_client.get(reverse("blog_posts:index"))

    assert [page.title for page in response.context["pages"]] == ["Profile management"]
    assert response.context["pages"][0].other_languages[0].language_code == "de"
    assert "Translations" in response.content.decode()


def test_all_posts_language_filter_shows_other_languages(admin_client, translated_post):
    german = admin_client.get(reverse("blog_posts:index"), {"locale": "de"})
    assert [page.title for page in german.context["pages"]] == ["Profilverwaltung"]
    assert german.context["pages"][0].other_languages[0].language_code == "en-US"

    everything = admin_client.get(reverse("blog_posts:index"), {"locale": ""})
    assert sorted(page.title for page in everything.context["pages"]) == ["Profile management", "Profilverwaltung"]


def test_page_tree_button_comes_after_edit_blog_homepage(admin_client, blog_index):
    content = admin_client.get(workspace_url()).content.decode()
    assert content.index("All posts") < content.index("Edit blog homepage") < content.index("Page tree")
