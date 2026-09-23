# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A group's "Translated pages" permissions extend its page permissions to the same page
in every other locale, at the levels those permissions grant."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

import pytest
from wagtail.models import GroupPagePermission, Locale, Page
from wagtail.permissions import page_permission_policy
from wagtail.users.forms import GroupForm
from wagtail_localize.operations import translate_object

from springfield.blog.models.pages import BlogIndexPage
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
def editor_group(english_page):
    """A group with "change" and "publish" permission for the English page only."""
    group = Group.objects.create(name="Translation permission editors")
    for codename in ("change_page", "publish_page"):
        GroupPagePermission.objects.create(
            group=group,
            page=english_page,
            permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename),
        )
    return group


@pytest.fixture
def editor(editor_group):
    user = User.objects.create_user(username="editor", email="editor@example.com", password="pass", is_staff=True)
    user.groups.add(editor_group)
    return user


@pytest.fixture
def translation_editor(editor, editor_group):
    """The editor, with "Edit" but not "Publish" in the group's "Translated pages" permissions."""
    editor_group.permissions.add(Permission.objects.get(content_type__app_label="base", codename="change_translated_page"))
    return editor


def test_translated_pages_permissions_are_offered_on_the_group_form():
    offered_codenames = set(GroupForm().fields["permissions"].queryset.values_list("codename", flat=True))

    assert {
        "add_translated_page",
        "bulk_delete_translated_page",
        "change_translated_page",
        "lock_translated_page",
        "publish_translated_page",
        "unlock_translated_page",
    } <= offered_codenames


def test_page_permission_stays_in_its_locale_without_translated_pages_permission(editor, english_page, french_page):
    assert page_permission_policy.user_has_permission_for_instance(editor, "publish", english_page)
    assert not page_permission_policy.user_has_permission_for_instance(editor, "change", french_page)
    assert french_page.pk not in set(page_permission_policy.explorable_instances(editor).values_list("pk", flat=True))


def test_translations_get_the_translated_pages_levels(translation_editor, english_page, french_page):
    assert page_permission_policy.user_has_permission_for_instance(translation_editor, "change", french_page)
    assert not page_permission_policy.user_has_permission_for_instance(translation_editor, "publish", french_page)
    assert page_permission_policy.user_has_permission_for_instance(translation_editor, "publish", english_page)

    editable = page_permission_policy.instances_user_has_permission_for(translation_editor, "change")
    assert set(editable.values_list("pk", flat=True)) == {english_page.pk, french_page.pk}

    french_permissions = french_page.permissions_for_user(translation_editor)
    assert french_permissions.can_edit()
    assert not french_permissions.can_publish()


def test_translated_pages_levels_do_not_widen_the_stored_page(editor, editor_group, english_page, french_page):
    editor_group.permissions.add(Permission.objects.get(content_type__app_label="base", codename="lock_translated_page"))

    assert page_permission_policy.user_has_permission_for_instance(editor, "lock", french_page)
    assert not page_permission_policy.user_has_permission_for_instance(editor, "lock", english_page)


def test_translation_is_reachable_in_the_explorer(translation_editor, french_page):
    """Editing a page in the admin means first navigating to it, so the explorer has to
    show the translation and the ancestors leading down to it."""
    explorable = set(page_permission_policy.explorable_instances(translation_editor).values_list("pk", flat=True))

    assert french_page.pk in explorable
    assert set(french_page.get_ancestors().values_list("pk", flat=True)) <= explorable


def test_permission_does_not_leak_to_unrelated_pages(translation_editor, english_page):
    """Extending to translations must not widen a permission to the rest of a locale."""
    sibling = SimpleRichTextPageFactory(parent=english_page.get_parent(), slug="unrelated")

    assert not page_permission_policy.user_has_permission_for_instance(translation_editor, "change", sibling)


def test_permission_does_not_leak_to_unrelated_users(translation_editor, french_page):
    outsider = User.objects.create_user(username="outsider", email="outsider@example.com", password="pass", is_staff=True)

    assert not page_permission_policy.user_has_permission_for_instance(outsider, "change", french_page)
    assert not page_permission_policy.instances_user_has_permission_for(outsider, "change").exists()


def test_blog_page_translations_are_extended(translation_editor, editor_group, english_page):
    blog_index = english_page.get_parent().add_child(instance=BlogIndexPage(title="Blog", slug="permissions-blog", locale=english_page.locale))
    GroupPagePermission.objects.create(
        group=editor_group,
        page=blog_index,
        permission=Permission.objects.get(content_type__app_label="wagtailcore", codename="change_page"),
    )
    french_locale, _ = Locale.objects.get_or_create(language_code="fr")
    translate_object(blog_index, [french_locale])

    assert page_permission_policy.user_has_permission_for_instance(translation_editor, "change", blog_index.get_translation(french_locale))
