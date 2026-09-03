# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import transaction

import pytest
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale, Page
from wagtail_localize.operations import translate_object

from springfield.cms.slug_updates import (
    automatic_redirect_creation_disabled,
    find_sibling_with_slug,
    page_with_translations,
    rename_page_and_translations,
)
from springfield.cms.tests.factories import SimpleRichTextPageFactory


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
