# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Operations behind the "Update slug" admin action."""

from contextlib import contextmanager

from django.db import transaction

from wagtail.contrib.redirects.signal_handlers import autocreate_redirects_on_slug_change
from wagtail.signals import page_slug_changed


@contextmanager
def automatic_redirect_creation_disabled():
    """Stop Wagtail's redirects app from answering slug changes made in this block.

    Wrap the transaction in this rather than opening it inside one: Wagtail sends
    ``page_slug_changed`` from a ``transaction.on_commit`` callback, so the signal
    only fires once the outermost atomic block exits. A context manager nested
    inside the transaction has already reconnected the receiver by then.
    """
    page_slug_changed.disconnect(autocreate_redirects_on_slug_change)
    try:
        yield
    finally:
        page_slug_changed.connect(autocreate_redirects_on_slug_change)


def find_sibling_with_slug(page, slug):
    """Return the sibling of ``page`` holding ``slug``, or ``None``"""
    return page.get_siblings(inclusive=False).filter(slug=slug, locale=page.locale).first()


def page_with_translations(page):
    """Return ``page`` followed by its translations, excluding aliases.

    Aliases are left out because an alias exists to mirror its source; writing a
    slug onto one directly would desynchronise it from the page it tracks.
    """
    translations = page.get_translations().filter(alias_of__isnull=True)
    return [page, *translations]


def set_page_slug(page, new_slug):
    """Write ``new_slug`` to the page row and to its latest revision.

    The revision matters as much as the row. A revision stores its own copy of the
    slug, so a row updated on its own would be silently reverted the next time
    anyone published — whether that is a pending draft an editor publishes later, or
    the already-published revision this action republishes itself. Updating the
    revision in place rather than saving a new one leaves the page's draft state and
    revision history as they were.
    """
    page.slug = new_slug
    page.save()

    revision = page.get_latest_revision()
    if revision is not None:
        revision.content["slug"] = new_slug
        revision.save(update_fields=["content"])


def publish_page(page, user=None):
    """Publish the page's latest revision, creating one if it has none."""
    revision = page.get_latest_revision() or page.specific.save_revision(user=user)
    revision.publish(user=user)


def rename_page_and_translations(page, new_slug, publish=False, user=None):
    """Move ``page`` and each of its non-alias translations onto ``new_slug``."""
    for translatable_page in page_with_translations(page):
        set_page_slug(translatable_page, new_slug)
        if publish:
            publish_page(translatable_page, user=user)


def retire_page_and_translations(page, new_slug, user=None):
    """Move ``page`` and its non-alias translations onto ``new_slug`` and unpublish them.

    Renaming is what frees the original slug for the page taking it over; unpublishing
    is what takes the retired content off the live site. Both are needed — a renamed
    page left published would carry on serving its content at the new URL.
    """
    for translatable_page in page_with_translations(page):
        set_page_slug(translatable_page, new_slug)
        if translatable_page.live:
            translatable_page.unpublish(user=user)


def update_page_slug(page, new_slug, conflicting_page=None, conflicting_page_slug=None, publish=False, user=None):
    """Move ``page`` and its translations onto ``new_slug``, retiring whichever page
    already holds it.

    The conflicting page is retired first: Wagtail rejects a save that would duplicate
    a sibling's slug, so the slug has to be freed before the target can take it. The
    redirect suppression wraps the transaction rather than sitting inside it, because
    the signal it suppresses is sent on commit — that is, as the atomic block exits.
    """
    with automatic_redirect_creation_disabled():
        with transaction.atomic():
            if conflicting_page is not None:
                retire_page_and_translations(conflicting_page, conflicting_page_slug, user=user)
            rename_page_and_translations(page, new_slug, publish=publish, user=user)
