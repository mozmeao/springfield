# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import itertools

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import translation

import pytest
import wagtail_factories
from wagtail.models import Locale, Site

from springfield.blog.models import BlogArticlePage
from springfield.blog.models.pages import BlogIndexPage, HeroStyle
from springfield.blog.models.snippets import BlogTopic
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

User = get_user_model()


@pytest.fixture
def admin_client(client, db):
    """Force-login a superuser using the ModelBackend rather than the project's
    default SSO backend. Without the override, mozilla_django_oidc's
    SessionRefresh middleware sees an OIDC-authenticated user with no OIDC
    token in the session and redirects every admin GET to the auth0 login URL.
    """
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass",
        )
        client.force_login(admin, backend="django.contrib.auth.backends.ModelBackend")
        yield client


@pytest.fixture(autouse=True)
def clear_waffle_cache():
    """Clear waffle's cache before each test so that switch overrides created by
    @override_switch are not shadowed by stale cache entries."""
    cache.clear()
    yield


@pytest.fixture(autouse=True)
def reset_translation():
    """Reset Django's active language after each test.

    Requests to locale-prefixed URLs (e.g. /pt-PT/...) call
    translation.activate() inside the URL resolver. If not cleaned up, the
    activated language leaks into subsequent tests and causes them to render
    with the wrong locale."""
    yield
    translation.deactivate()


@pytest.fixture
def minimal_site(client):
    # Bootstraps a minimal site with a root page at / and one child page at /test-page/
    top_level_page = SimpleRichTextPageFactory(
        slug="root_page",  # this doesn't get shown
        live=True,
    )

    try:
        site = Site.objects.get(is_default_site=True)
        site.root_page = top_level_page
        site.hostname = client._base_environ()["SERVER_NAME"]
        site.save()
    except Site.DoesNotExist:
        site = wagtail_factories.SiteFactory(
            root_page=top_level_page,
            is_default_site=True,
            hostname=client._base_environ()["SERVER_NAME"],
        )

    LocaleFactory(language_code="fr")

    SimpleRichTextPageFactory(
        slug="test-page",
        parent=top_level_page,
        title="Test Page",
    )

    return site


@pytest.fixture
def blog_index(minimal_site):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = BlogIndexPage(
        title="Blog",
        slug="test-unit-blog",
        locale=Locale.objects.get(language_code="en-US"),
    )
    root_page.add_child(instance=index_page)
    return index_page


@pytest.fixture
def blog_topic(blog_index):
    return BlogTopic.objects.create(name="Privacy", slug="test-unit-privacy", locale=blog_index.locale)


@pytest.fixture
def make_article(blog_index, blog_topic):
    slug_numbers = itertools.count(1)

    def make_article(**fields):
        fields.setdefault("topic", blog_topic)
        if fields.get("image"):
            fields.setdefault("image_alt", "Test image alt text")
        else:
            fields.setdefault("hero_style", HeroStyle.TEXT_ONLY)
        if fields.get("listing_image"):
            fields.setdefault("listing_image_alt", "Test listing image alt text")
        article = BlogArticlePage(
            title=fields.pop("title", "Test article"),
            slug=f"test-unit-article-{next(slug_numbers)}",
            locale=blog_index.locale,
            **fields,
        )
        blog_index.add_child(instance=article)
        return article

    return make_article


@pytest.fixture
def real_images(db):
    """Two image rows with real files, for tests that render an `<img>`."""
    image, dark_image, _, _ = get_placeholder_images()
    return image, dark_image


@pytest.fixture
def blog_article(make_article, real_images):
    """An article with a non-decorative featured image and its alt text set."""
    image, _ = real_images
    return make_article(image=image, image_alt="A laptop showing the Firefox home page")
