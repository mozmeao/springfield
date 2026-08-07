# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

import pytest
from wagtail.models import Locale
from wagtail_localize.fields import TranslatableField, get_translatable_fields

from springfield.cms.forms import BlogTagField
from springfield.cms.models import BlogTag

pytestmark = [pytest.mark.django_db]


def test_same_tag_name_allowed_in_two_locales():
    """taggit's TagBase makes name and slug globally unique. BlogTag scopes both to the
    locale so one concept can exist once per language — the whole point of keeping tags
    translatable."""
    fr_locale = Locale.objects.get_or_create(language_code="fr")[0]

    en_tag = BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())
    fr_tag = BlogTag.objects.create(name="Privacy", slug="privacy", locale=fr_locale)

    assert en_tag.pk != fr_tag.pk


def test_duplicate_tag_name_in_one_locale_is_rejected():
    """Name uniqueness within a locale is what makes name-based tag resolution
    deterministic, so it must be enforced by the database, not only by the form."""
    BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())

    with pytest.raises(IntegrityError):
        BlogTag.objects.create(name="Privacy", slug="privacy-again", locale=Locale.get_default())


def test_blog_tag_field_resolves_name_to_default_locale_tag():
    """The same tag name can exist in several locales; the field must always bind the
    article to the default-locale row, never another language's."""
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    en_tag = BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())
    BlogTag.objects.create(name="Privacy", slug="privacy", locale=fr_locale)

    field = BlogTagField(tag_model=BlogTag, required=False)

    assert field.clean("Privacy") == [en_tag]


def test_blog_tag_field_rejects_unknown_name():
    field = BlogTagField(tag_model=BlogTag, required=False)

    with pytest.raises(ValidationError, match="Nonexistent"):
        field.clean("Nonexistent")


def test_blog_tag_field_rejects_unpublished_tag():
    BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default(), live=False)
    field = BlogTagField(tag_model=BlogTag, required=False)

    with pytest.raises(ValidationError, match="Privacy"):
        field.clean("Privacy")


def test_blog_tag_field_rejects_tag_from_another_locale():
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    BlogTag.objects.create(name="Confidentialité", slug="confidentialite", locale=fr_locale)
    field = BlogTagField(tag_model=BlogTag, required=False)

    with pytest.raises(ValidationError, match="Confidentialité"):
        field.clean("Confidentialité")


def test_blog_tag_field_accepts_empty_input():
    """tags is optional, so an empty field must clean to no tags rather than raising."""
    field = BlogTagField(tag_model=BlogTag, required=False)

    assert field.clean("") == []


def test_blog_tag_autocomplete_offers_only_published_default_locale_tags(admin_client):
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())
    BlogTag.objects.create(name="Privacy in French", slug="privacy-fr", locale=fr_locale)
    BlogTag.objects.create(name="Privacy draft", slug="privacy-draft", locale=Locale.get_default(), live=False)

    response = admin_client.get(reverse("cms_blog_tag_autocomplete"), {"term": "Privacy"})

    assert response.json() == ["Privacy"]


def test_blog_tag_autocomplete_without_term_returns_nothing(admin_client):
    BlogTag.objects.create(name="Privacy", slug="privacy", locale=Locale.get_default())

    response = admin_client.get(reverse("cms_blog_tag_autocomplete"))

    assert response.json() == []


def test_tag_slug_is_synchronized_rather_than_translated():
    translatable_names = {field.field_name for field in get_translatable_fields(BlogTag) if isinstance(field, TranslatableField)}

    assert translatable_names == {"name"}
