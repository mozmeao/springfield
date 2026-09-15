# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import override_settings
from django.urls import reverse

import pytest
from wagtail import hooks
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import GroupPagePermission, Locale, Page
from wagtail_localize.operations import translate_object

from springfield.cms.forms import ConfirmUpdateSlugForm, UpdateSlugForm
from springfield.cms.slug_updates import (
    automatic_redirect_creation_disabled,
    find_sibling_with_slug,
    page_with_translations,
    rename_page_and_translations,
    retire_page_and_translations,
    update_page_slug,
)
from springfield.cms.tests.factories import SimpleRichTextPageFactory

User = get_user_model()


@pytest.fixture(autouse=True)
def default_locale(db):
    """Recreate the default Locale for every test in this module.

    Wagtail's default Locale row is created by a data migration. The transactional
    tests here flush the database when they finish, and a flush does not restore
    migration-created rows, so without this the test after the first transactional
    one cannot build a page.
    """
    Locale.objects.get_or_create(language_code=settings.LANGUAGE_CODE)


@pytest.fixture
def publisher_user(db):
    return User.objects.create_superuser(username="publisher", email="publisher@example.com", password="pass")


@pytest.fixture
def editor_user(parent_page):
    """A user who may change pages but not publish them."""
    user = User.objects.create_user(username="editor", email="editor@example.com", password="pass", is_staff=True)
    group = Group.objects.create(name="Editors without publish rights")
    group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
    GroupPagePermission.objects.create(
        group=group,
        page=parent_page,
        permission=Permission.objects.get(content_type__app_label="wagtailcore", codename="change_page"),
    )
    user.groups.add(group)
    return user


@pytest.fixture
def editor_client(client, editor_user):
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        client.force_login(editor_user, backend="django.contrib.auth.backends.ModelBackend")
        yield client


@pytest.fixture
def french_locale(minimal_site):
    return Locale.objects.get(language_code="fr")


@pytest.fixture
def parent_page(minimal_site):
    return SimpleRichTextPageFactory(
        slug="features",
        title="Features",
        parent=minimal_site.root_page,
        live=True,
    )


@pytest.fixture
def outgoing_page(parent_page):
    """The published page currently holding the target slug."""
    return SimpleRichTextPageFactory(
        slug="thing",
        title="Thing",
        parent=parent_page,
        live=True,
    )


@pytest.fixture
def replacement_page(parent_page):
    """The page built to take over the target slug: a draft that has never
    been published, so its slug lives in a revision as well as in its row."""
    page = SimpleRichTextPageFactory(
        slug="new-thing",
        title="New Thing",
        parent=parent_page,
        live=False,
    )
    page.save_revision()
    return page


# Suppress redirect creation


@pytest.mark.django_db(transaction=True)
def test_wagtail_creates_a_redirect_when_a_live_page_slug_changes(outgoing_page):
    """The behavior the update-slug action has to suppress. Wagtail's redirects
    app answers the page_slug_changed signal by pointing the old URL at the
    renamed page, which is exactly wrong when the old URL is about to be taken
    over by a different page."""
    outgoing_page.slug = "thing-old"
    outgoing_page.save()

    redirect = Redirect.objects.get(automatically_created=True)
    assert redirect.old_path == "/en-US/features/thing"
    assert redirect.redirect_page_id == outgoing_page.pk


@pytest.mark.django_db(transaction=True)
def test_no_redirect_is_created_while_automatic_creation_is_disabled(outgoing_page):
    """The context manager has to wrap the transaction, not sit inside it: Wagtail
    sends page_slug_changed from an on_commit callback, so the signal fires as the
    atomic block exits."""
    with automatic_redirect_creation_disabled():
        with transaction.atomic():
            outgoing_page.slug = "thing-old"
            outgoing_page.save()

    assert not Redirect.objects.exists()


# Page and slug querying


@pytest.mark.django_db
def test_find_sibling_with_slug_returns_the_page_holding_the_slug(replacement_page, outgoing_page):
    assert find_sibling_with_slug(replacement_page, "thing").pk == outgoing_page.pk


@pytest.mark.django_db
def test_find_sibling_with_slug_returns_none_when_no_sibling_holds_it(replacement_page, outgoing_page):
    assert find_sibling_with_slug(replacement_page, "unclaimed") is None


@pytest.mark.django_db
def test_find_sibling_with_slug_never_returns_the_page_itself(replacement_page):
    """A page finding itself would make the action try to retire the very page it
    is renaming."""
    assert find_sibling_with_slug(replacement_page, "new-thing") is None


@pytest.mark.django_db
def test_find_sibling_with_slug_returns_a_draft_sibling(replacement_page, parent_page):
    """A draft sibling holds the slug as firmly as a live one and blocks the
    rename identically."""
    draft_sibling = SimpleRichTextPageFactory(slug="draft-thing", title="Draft Thing", parent=parent_page, live=False)

    assert find_sibling_with_slug(replacement_page, "draft-thing").pk == draft_sibling.pk


@pytest.mark.django_db
def test_find_sibling_with_slug_ignores_a_page_under_a_different_parent(replacement_page, minimal_site):
    """A page with the same slug elsewhere in the tree is a different URL and does
    not block the rename."""
    other_parent = SimpleRichTextPageFactory(slug="other-section", title="Other Section", parent=minimal_site.root_page, live=True)
    SimpleRichTextPageFactory(slug="elsewhere", title="Elsewhere", parent=other_parent, live=True)

    assert find_sibling_with_slug(replacement_page, "elsewhere") is None


@pytest.mark.django_db
def test_page_with_translations_lists_the_page_before_its_translations(replacement_page, french_locale):
    """Order matters: callers that log or report on the operation should name the
    source page rather than an arbitrary translation."""
    translate_object(replacement_page, [french_locale])

    collected = page_with_translations(replacement_page)

    assert [page.pk for page in collected] == [replacement_page.pk, replacement_page.get_translation(french_locale).pk]


@pytest.mark.django_db
def test_page_with_translations_returns_only_the_page_when_it_has_no_translations(replacement_page):
    assert [page.pk for page in page_with_translations(replacement_page)] == [replacement_page.pk]


@pytest.mark.django_db
def test_page_with_translations_excludes_alias_translations(replacement_page, french_locale):
    """An alias exists to mirror its source, so writing a slug onto one directly
    would desynchronise it from the page it tracks."""
    alias = replacement_page.copy_for_translation(french_locale, copy_parents=True, alias=True)
    assert alias.alias_of_id == replacement_page.pk

    assert [page.pk for page in page_with_translations(replacement_page)] == [replacement_page.pk]


# Slug update operation


@pytest.mark.django_db
def test_rename_page_and_translations_sets_the_new_slug_on_the_page(replacement_page):
    rename_page_and_translations(replacement_page, "thing")

    assert Page.objects.get(pk=replacement_page.pk).slug == "thing"


@pytest.mark.django_db
def test_rename_page_and_translations_sets_the_new_slug_on_each_translation(replacement_page, french_locale):
    translate_object(replacement_page, [french_locale])
    translation = replacement_page.get_translation(french_locale)

    rename_page_and_translations(replacement_page, "thing")

    assert Page.objects.get(pk=translation.pk).slug == "thing"


@pytest.mark.django_db
def test_rename_page_and_translations_keeps_a_draft_revision_in_step(replacement_page):
    """A page with unpublished changes stores its own copy of the slug in its latest
    revision. Left alone, the editor's next publish would revert the rename."""
    rename_page_and_translations(replacement_page, "thing")

    Page.objects.get(pk=replacement_page.pk).get_latest_revision().publish()

    assert Page.objects.get(pk=replacement_page.pk).slug == "thing"


@pytest.mark.django_db
def test_rename_page_and_translations_keeps_an_already_published_revision_in_step(outgoing_page):
    """The same hazard on a live page carrying no draft: publishing it as part of the
    rename must not restore the slug held by the revision published before it."""
    outgoing_page.save_revision().publish()
    # Re-fetch: publishing updates the database, not the instance held here, and a
    # stale instance would misreport whether the page carries a draft.
    published_page = Page.objects.get(pk=outgoing_page.pk)

    rename_page_and_translations(published_page, "renamed-thing", publish=True)

    assert Page.objects.get(pk=outgoing_page.pk).slug == "renamed-thing"


@pytest.mark.django_db
def test_rename_page_and_translations_publishes_the_page_and_its_translations_when_asked(replacement_page, french_locale):
    translate_object(replacement_page, [french_locale])
    translation = replacement_page.get_translation(french_locale)

    rename_page_and_translations(replacement_page, "thing", publish=True)

    assert Page.objects.get(pk=replacement_page.pk).live
    assert Page.objects.get(pk=translation.pk).live


@pytest.mark.django_db
def test_rename_page_and_translations_leaves_an_unpublished_page_unpublished(replacement_page):
    rename_page_and_translations(replacement_page, "thing")

    assert not Page.objects.get(pk=replacement_page.pk).live


@pytest.mark.django_db
def test_retire_page_and_translations_renames_and_unpublishes_the_page(outgoing_page):
    retire_page_and_translations(outgoing_page, "thing-old")

    retired = Page.objects.get(pk=outgoing_page.pk)
    assert retired.slug == "thing-old"
    assert not retired.live


@pytest.mark.django_db
def test_retire_page_and_translations_renames_and_unpublishes_each_translation(outgoing_page, french_locale):
    translate_object(outgoing_page, [french_locale])
    translation = outgoing_page.get_translation(french_locale)
    translation.save_revision().publish()

    retire_page_and_translations(outgoing_page, "thing-old")

    retired_translation = Page.objects.get(pk=translation.pk)
    assert retired_translation.slug == "thing-old"
    assert not retired_translation.live


@pytest.mark.django_db
def test_retire_page_and_translations_keeps_the_revision_in_step(outgoing_page):
    """An outgoing page carrying a draft would otherwise reclaim the target slug
    the next time anyone published it."""
    outgoing_page.save_revision()

    retire_page_and_translations(outgoing_page, "thing-old")

    Page.objects.get(pk=outgoing_page.pk).get_latest_revision().publish()

    assert Page.objects.get(pk=outgoing_page.pk).slug == "thing-old"


@pytest.mark.django_db
def test_update_page_slug_swaps_the_replacement_onto_the_outgoing_slug(replacement_page, outgoing_page, french_locale):
    translate_object(replacement_page, [french_locale])
    replacement_translation = replacement_page.get_translation(french_locale)

    update_page_slug(replacement_page, "thing", conflicting_page=outgoing_page, conflicting_page_slug="thing-old")

    assert Page.objects.get(pk=replacement_page.pk).slug == "thing"
    assert Page.objects.get(pk=replacement_translation.pk).slug == "thing"
    retired = Page.objects.get(pk=outgoing_page.pk)
    assert retired.slug == "thing-old"
    assert not retired.live


@pytest.mark.django_db
def test_update_page_slug_leaves_other_pages_alone_when_nothing_holds_the_slug(replacement_page, outgoing_page):
    update_page_slug(replacement_page, "unclaimed")

    assert Page.objects.get(pk=replacement_page.pk).slug == "unclaimed"
    assert Page.objects.get(pk=outgoing_page.pk).slug == "thing"


@pytest.mark.django_db
def test_update_page_slug_rolls_back_completely_when_a_translation_cannot_be_renamed(replacement_page, outgoing_page, parent_page, french_locale):
    """The failure lands on the outgoing page's translation, after the outgoing page
    itself has already been renamed and unpublished, so the transaction reverts both
    changes."""
    translate_object(outgoing_page, [french_locale])
    french_parent = parent_page.get_translation(french_locale)
    SimpleRichTextPageFactory(slug="thing-old", title="Blocker", parent=french_parent, locale=french_locale, live=True)

    with pytest.raises(ValidationError):
        update_page_slug(replacement_page, "thing", conflicting_page=outgoing_page, conflicting_page_slug="thing-old")

    untouched = Page.objects.get(pk=outgoing_page.pk)
    assert untouched.slug == "thing"
    assert untouched.live
    assert Page.objects.get(pk=replacement_page.pk).slug == "new-thing"


@pytest.mark.django_db(transaction=True)
def test_update_page_slug_creates_no_redirects(replacement_page, outgoing_page):
    update_page_slug(replacement_page, "thing", conflicting_page=outgoing_page, conflicting_page_slug="thing-old")

    assert not Redirect.objects.exists()


# Admin views and forms


def test_update_slug_form_accepts_a_valid_slug():
    assert UpdateSlugForm(data={"slug": "thing"}).is_valid()


def test_update_slug_form_rejects_a_value_that_is_not_a_slug():
    form = UpdateSlugForm(data={"slug": "not a slug!"})

    assert not form.is_valid()
    assert "slug" in form.errors


@pytest.mark.django_db
def test_confirm_update_slug_form_prefills_the_replacement_slug(outgoing_page):
    form = ConfirmUpdateSlugForm(conflicting_page=outgoing_page, initial={"slug": "thing"})

    assert form["conflicting_page_slug"].value() == "thing-old"


@pytest.mark.django_db
def test_confirm_update_slug_form_omits_the_replacement_slug_field_when_nothing_holds_the_slug(db):
    form = ConfirmUpdateSlugForm(conflicting_page=None, initial={"slug": "unclaimed"})

    assert "conflicting_page_slug" not in form.fields


@pytest.mark.django_db
def test_confirm_update_slug_form_rejects_a_replacement_slug_another_sibling_holds(outgoing_page, parent_page):
    SimpleRichTextPageFactory(slug="thing-old", title="Already Here", parent=parent_page, live=True)

    form = ConfirmUpdateSlugForm(
        conflicting_page=outgoing_page,
        data={"slug": "thing", "conflicting_page_slug": "thing-old"},
    )

    assert not form.is_valid()
    assert "conflicting_page_slug" in form.errors


@pytest.mark.django_db
def test_confirm_update_slug_form_rejects_a_replacement_slug_equal_to_the_new_slug(outgoing_page):
    form = ConfirmUpdateSlugForm(
        conflicting_page=outgoing_page,
        data={"slug": "thing", "conflicting_page_slug": "thing"},
    )

    assert not form.is_valid()
    assert "conflicting_page_slug" in form.errors


@pytest.mark.django_db
def test_slug_entry_view_renders_the_slug_field(admin_client, replacement_page):
    response = admin_client.get(reverse("cms_page_update_slug", args=[replacement_page.id]))

    assert response.status_code == 200
    assert list(response.context["form"].fields) == ["slug"]


@pytest.mark.django_db
def test_slug_entry_view_redirects_to_the_confirmation_carrying_the_slug(admin_client, replacement_page):
    response = admin_client.post(reverse("cms_page_update_slug", args=[replacement_page.id]), {"slug": "thing"})

    assert response.status_code == 302
    assert response.url == f"{reverse('cms_page_update_slug_confirm', args=[replacement_page.id])}?slug=thing"


@pytest.mark.django_db
def test_slug_entry_view_requires_publish_permission(editor_client, replacement_page):
    response = editor_client.get(reverse("cms_page_update_slug", args=[replacement_page.id]))

    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")


@pytest.mark.django_db
def test_slug_entry_view_returns_404_for_a_page_that_does_not_exist(admin_client):
    """Followed, because Django's LocaleMiddleware answers a 404 on an unprefixed URL
    by redirecting to the locale-prefixed one first."""
    response = admin_client.get(reverse("cms_page_update_slug", args=[999999]), follow=True)

    assert response.status_code == 404


@pytest.mark.django_db
def test_confirm_view_context_when_no_page_holds_the_slug(admin_client, replacement_page, french_locale):
    translate_object(replacement_page, [french_locale])

    response = admin_client.get(reverse("cms_page_update_slug_confirm", args=[replacement_page.id]), {"slug": "unclaimed"})

    assert response.status_code == 200
    assert response.context["new_slug"] == "unclaimed"
    assert response.context["translation_count"] == 1
    assert response.context["conflicting_page"] is None
    assert "publish" in response.context["form"].fields
    assert "conflicting_page_slug" not in response.context["form"].fields


@pytest.mark.django_db
def test_confirm_view_links_to_the_page_being_retired_and_prefills_its_new_slug(admin_client, replacement_page, outgoing_page):
    response = admin_client.get(reverse("cms_page_update_slug_confirm", args=[replacement_page.id]), {"slug": "thing"})

    assert response.status_code == 200
    assert response.context["conflicting_page"].pk == outgoing_page.pk
    assert response.context["conflicting_page_translation_count"] == 0
    assert response.context["form"]["conflicting_page_slug"].value() == "thing-old"


@pytest.mark.django_db
def test_confirm_view_redirects_back_when_no_slug_is_given(admin_client, replacement_page):
    response = admin_client.get(reverse("cms_page_update_slug_confirm", args=[replacement_page.id]))

    assert response.status_code == 302
    assert response.url == reverse("cms_page_update_slug", args=[replacement_page.id])


@pytest.mark.django_db
def test_confirm_view_performs_the_swap_and_reports_it(admin_client, replacement_page, outgoing_page):
    response = admin_client.post(
        reverse("cms_page_update_slug_confirm", args=[replacement_page.id]),
        {"slug": "thing", "conflicting_page_slug": "thing-old"},
    )

    updated_page = Page.objects.get(pk=replacement_page.pk)
    assert updated_page.slug == "thing"
    assert updated_page.live is False
    retired = Page.objects.get(pk=outgoing_page.pk)
    assert retired.slug == "thing-old"
    assert not retired.live
    # Wagtail renders each message through a template, so the stored message is HTML.
    message = str(list(get_messages(response.wsgi_request))[0])
    assert "Page “New Thing” now uses the slug “thing”." in message
    assert reverse("wagtailadmin_pages:edit", args=[replacement_page.id]) in message
    assert "View live" not in message


@pytest.mark.django_db
def test_confirm_view_publishes_the_page_when_the_box_is_ticked(admin_client, replacement_page, outgoing_page):
    response = admin_client.post(
        reverse("cms_page_update_slug_confirm", args=[replacement_page.id]),
        {"slug": "thing", "conflicting_page_slug": "thing-old", "publish": "on"},
    )

    updated_page = Page.objects.get(pk=replacement_page.pk)
    assert updated_page.slug == "thing"
    assert updated_page.live

    message = str(list(get_messages(response.wsgi_request))[0])
    assert "Page “New Thing” now uses the slug “thing”." in message
    assert reverse("wagtailadmin_pages:edit", args=[replacement_page.id]) in message
    assert updated_page.url in message


@pytest.mark.django_db
def test_confirm_view_shows_error_raised_by_update_method(admin_client, replacement_page, outgoing_page, parent_page, french_locale):
    translate_object(outgoing_page, [french_locale])
    french_parent = parent_page.get_translation(french_locale)
    SimpleRichTextPageFactory(slug="thing-old", title="Blocker", parent=french_parent, locale=french_locale, live=True)

    response = admin_client.post(
        reverse("cms_page_update_slug_confirm", args=[replacement_page.id]),
        {"slug": "thing", "conflicting_page_slug": "thing-old"},
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()[0] == "The slug 'thing-old' is already in use within the parent page at '/en-US/features-fr/'."
    assert Page.objects.get(pk=replacement_page.pk).slug == "new-thing"
    assert Page.objects.get(pk=outgoing_page.pk).slug == "thing"


@pytest.mark.django_db
def test_confirm_view_redirects_to_the_parent_explorer(admin_client, replacement_page, outgoing_page, parent_page):
    response = admin_client.post(
        reverse("cms_page_update_slug_confirm", args=[replacement_page.id]),
        {"slug": "thing", "conflicting_page_slug": "thing-old"},
    )

    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_explore", args=[parent_page.id])


@pytest.mark.django_db
def test_update_slug_button_is_displayed_in_page_listing(publisher_user, replacement_page):
    buttons = [
        button
        for hook in hooks.get_hooks("register_page_listing_more_buttons")
        for button in hook(page=replacement_page, user=publisher_user, next_url=None)
        if getattr(button, "url_name", None) == "cms_page_update_slug"
    ]

    assert len(buttons) == 1
    assert buttons[0].is_shown(publisher_user)


@pytest.mark.django_db
def test_update_slug_button_is_displayed_in_page_header(publisher_user, replacement_page):
    buttons = [
        button
        for hook in hooks.get_hooks("register_page_header_buttons")
        for button in hook(page=replacement_page, user=publisher_user, next_url=None, view_name="edit")
        if getattr(button, "url_name", None) == "cms_page_update_slug"
    ]

    assert len(buttons) == 1
    assert buttons[0].is_shown(publisher_user)


@pytest.mark.django_db
def test_update_slug_button_is_hidden_for_user_without_publish_permission(editor_user, replacement_page):
    listing_buttons = [
        button
        for hook in hooks.get_hooks("register_page_listing_more_buttons")
        for button in hook(page=replacement_page, user=editor_user, next_url=None)
        if getattr(button, "url_name", None) == "cms_page_update_slug"
    ]
    header_buttons = [
        button
        for hook in hooks.get_hooks("register_page_header_buttons")
        for button in hook(page=replacement_page, user=editor_user, next_url=None, view_name="edit")
        if getattr(button, "url_name", None) == "cms_page_update_slug"
    ]

    assert len(listing_buttons) == 1
    assert len(header_buttons) == 1
    assert not any(button.is_shown(editor_user) for button in listing_buttons + header_buttons)
