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


class WhatsNewPage2026Factory(wagtail_factories.PageFactory):
    title = "What's New in Firefox 145"
    live = True
    slug = "145"
    version = "145"

    class Meta:
        model = models.WhatsNewPage2026


class GeneralWhatsNewPage2026Factory(wagtail_factories.PageFactory):
    title = "What's New in Firefox — General"
    live = True
    slug = "general"
    version = "general"

    class Meta:
        model = models.WhatsNewPage2026


class NightlyWhatsNewPage2026Factory(wagtail_factories.PageFactory):
    title = "What's New in Firefox Nightly"
    live = True
    slug = "nightly"
    version = "nightly"

    class Meta:
        model = models.WhatsNewPage2026


class DeveloperWhatsNewPage2026Factory(wagtail_factories.PageFactory):
    title = "What's New in Firefox Developer Edition"
    live = True
    slug = "developer"
    version = "developer"

    class Meta:
        model = models.WhatsNewPage2026


class BetaWhatsNewPage2026Factory(wagtail_factories.PageFactory):
    title = "What's New in Firefox Beta"
    live = True
    slug = "beta"
    version = "beta"

    class Meta:
        model = models.WhatsNewPage2026


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
    icon = "globe"

    class Meta:
        model = models.ArticleDetailPage


class ArticleThemePageFactory(wagtail_factories.PageFactory):
    title = "Test Article Theme Page"
    live = True
    slug = "article-theme"

    class Meta:
        model = models.ArticleThemePage


class DownloadIndexPageFactory(wagtail_factories.PageFactory):
    title = "Test Download Index Page"
    live = True
    slug = "download-index"

    class Meta:
        model = models.DownloadIndexPage


class DownloadPageFactory(wagtail_factories.PageFactory):
    title = "Test Download Page"
    live = True
    slug = "download"
    platform = "windows"
    subheading = "<p>Test subheading</p>"

    class Meta:
        model = models.DownloadPage


class FreeFormPage2026Factory(wagtail_factories.PageFactory):
    title = "Test FreeFormPage2026"
    live = True
    slug = "freeform-2026-page"

    class Meta:
        model = models.FreeFormPage2026
