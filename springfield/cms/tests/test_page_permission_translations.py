# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A group's page permissions must reach the page in every locale, not just the one
locale whose tree holds the page the permission refers to."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

import pytest
from wagtail.models import GroupPagePermission, Locale, Page
from wagtail.permissions import page_permission_policy
from wagtail_localize.operations import translate_object

from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]

User = get_user_model()


@pytest.fixture
def english_page():
    english_locale, _ = Locale.objects.get_or_create(language_code=settings.LANGUAGE_CODE)
    homepage = Page.objects.get(depth=2, locale=english_locale)
    return SimpleRichTextPageFactory(parent=homepage, slug="permissions-demo")


@pytest.fixture
def french_page(english_page):
    french_locale, _ = Locale.objects.get_or_create(language_code="fr")
    translate_object(english_page, [french_locale])
    return english_page.get_translation(french_locale)


@pytest.fixture
def editor(english_page):
    """A user whose group has "change" permission for the English page only."""
    user = User.objects.create_user(username="editor", email="editor@example.com", password="pass", is_staff=True)
    group = Group.objects.create(name="Translation permission editors")
    GroupPagePermission.objects.create(
        group=group,
        page=english_page,
        permission=Permission.objects.get(content_type__app_label="wagtailcore", codename="change_page"),
    )
    user.groups.add(group)
    return user


def test_permission_extends_to_translations(editor, english_page, french_page):
    assert page_permission_policy.user_has_permission_for_instance(editor, "change", english_page)
    assert page_permission_policy.user_has_permission_for_instance(editor, "change", french_page)

    editable = page_permission_policy.instances_user_has_permission_for(editor, "change")
    assert set(editable.values_list("pk", flat=True)) == {english_page.pk, french_page.pk}

    assert french_page.permissions_for_user(editor).can_edit()


def test_translation_is_reachable_in_the_explorer(editor, french_page):
    """Editing a page in the admin means first navigating to it, so the explorer has to
    show the translation and the ancestors leading down to it."""
    explorable = page_permission_policy.explorable_instances(editor)

    assert french_page.pk in set(explorable.values_list("pk", flat=True))
    assert set(french_page.get_ancestors().values_list("pk", flat=True)) <= set(explorable.values_list("pk", flat=True))


def test_permission_does_not_leak_to_unrelated_pages(editor, english_page, french_page):
    """Extending to translations must not widen a permission to the rest of a locale."""
    sibling = SimpleRichTextPageFactory(parent=english_page.get_parent(), slug="unrelated")

    assert not page_permission_policy.user_has_permission_for_instance(editor, "change", sibling)
    assert not page_permission_policy.user_has_permission_for_instance(editor, "publish", french_page)


def test_permission_does_not_leak_to_unrelated_users(french_page):
    outsider = User.objects.create_user(username="outsider", email="outsider@example.com", password="pass", is_staff=True)

    assert not page_permission_policy.user_has_permission_for_instance(outsider, "change", french_page)
    assert not page_permission_policy.instances_user_has_permission_for(outsider, "change").exists()
