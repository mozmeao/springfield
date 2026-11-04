# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils import timezone

import factory
import wagtail_factories
from wagtail import models as wagtail_models
from wagtail_localize.models import TranslationSource
from wagtail_localize_smartling import models as smartling_models

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


class RoadmapPageFactory(wagtail_factories.PageFactory):
    title = "Firefox Roadmap"
    live = True
    slug = "whatsnext"

    class Meta:
        model = models.RoadmapPage


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
    image_alt = "A placeholder image used for testing purposes."
    featured_image_alt = "A placeholder image used for testing purposes."

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
    featured_image_alt = "A placeholder image used for testing purposes."

    class Meta:
        model = models.DownloadPage


class FreeFormPage2026Factory(wagtail_factories.PageFactory):
    title = "Test FreeFormPage2026"
    live = True
    slug = "freeform-2026-page"

    class Meta:
        model = models.FreeFormPage2026


class FlareDocsIndexPageFactory(wagtail_factories.PageFactory):
    title = "Flare Docs - Test"
    live = True
    slug = "flare-docs-test"

    class Meta:
        model = models.FlareDocsIndexPage


class ReferralHubPageFactory(wagtail_factories.PageFactory):
    title = "Test Referral Hub Page"
    live = True
    slug = "invite"

    class Meta:
        model = models.ReferralHubPage


class ReferralGetFirefoxPageFactory(wagtail_factories.PageFactory):
    title = "Test Referral Get Firefox Page"
    live = True
    slug = "get-firefox"

    class Meta:
        model = models.ReferralGetFirefoxPage


class ShareFirefoxPageFactory(wagtail_factories.PageFactory):
    title = "Test Share Firefox Page"
    live = True
    slug = "share"

    class Meta:
        model = models.ShareFirefoxPage


def create_smartling_job(pages, user=None):
    """
    A Smartling job carrying one file per page, as submitting an order of those
    pages produces. It has not been sent, so it holds no Smartling identifiers.
    """
    user = user or WagtailUserFactory()
    project, _ = smartling_models.Project.objects.get_or_create(
        environment="staging",
        account_uid="test-account-uid",
        project_id="test-project-id",
        defaults={
            "archived": False,
            "name": "Test Smartling project",
            "type_code": "APPLICATION_RESOURCES",
            "source_locale_description": "English (United States) [en-US]",
            "source_locale_id": "en-US",
        },
    )
    order = smartling_models.Order.objects.create(
        name="Test order",
        created_by=user,
        submitted_at=timezone.now(),
    )
    job = smartling_models.Job.objects.create(
        project=project,
        order=order,
        user=user,
        name="Test job",
        description="Test order",
        reference_number=order.reference_number,
    )
    for page in pages:
        translation_source, _ = TranslationSource.get_or_create_from_instance(page)
        smartling_models.JobFile.objects.create(job=job, translation_source=translation_source)

    return job
