# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Operations behind the "Update slug" admin action."""

from contextlib import contextmanager

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
