# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import factory
import wagtail_factories
from wagtail import models as wagtail_models

from springfield.cms import models


class WagtailUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "auth.User"  # Equivalent to ``model = myapp.models.User``
        django_get_or_create = ("username",)

    email = "testuser@example.com"
    password = factory.PostGenerationMethodCall("set_password", "te5tus3r")
    username = "testuser"

    is_superuser = False
    is_staff = True
    is_active = True


class SimpleRichTextPageFactory(wagtail_factories.PageFactory):
    title = "Test SimpleRichTextPage"
    live = True
    slug = "homepage"

    class Meta:
        model = models.SimpleRichTextPage


class LocaleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = wagtail_models.Locale


class StructuralPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.StructuralPage


class WhatsNewIndexPageFactory(wagtail_factories.PageFactory):
    slug = "whatsnew"

    class Meta:
        model = models.WhatsNewIndexPage


class WhatsNewPageFactory(wagtail_factories.PageFactory):
    title = "What's New in Firefox 123"
    live = True
    slug = "123"
    version = "123"

    class Meta:
        model = models.WhatsNewPage


class FreeFormPageFactory(wagtail_factories.PageFactory):
    title = "Test FreeFormPage"
    live = True
    slug = "freeform-page"

    class Meta:
        model = models.FreeFormPage


class ArticleIndexPageFactory(wagtail_factories.PageFactory):
    title = "Test Article Index Page"
    live = True
    slug = "articles"

    class Meta:
        model = models.ArticleIndexPage


class ArticleDetailPageFactory(wagtail_factories.PageFactory):
    title = "Test Article Detail Page"
    live = True
    slug = "article-detail-page"
    description = "Test Article Description for Index Page"

    class Meta:
        model = models.ArticleDetailPage
