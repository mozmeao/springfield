# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import transaction

import pytest
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale

from springfield.cms.slug_updates import automatic_redirect_creation_disabled
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
