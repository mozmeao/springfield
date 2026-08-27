# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Draft sharing for translated pages.
#
# wagtail-localize does not create draft revision for pages as its translations change,
# so `wagtaildraftsharing` cannot natively create sharing links for translated pages.
# These helpers create revisions for the pending translation that exists solely to be
# shared, without altering the page itself.

from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from wagtail.models import Revision
from wagtaildraftsharing.models import WagtaildraftsharingLink
from wagtaildraftsharing.utils import tz_aware_utc_now

# Marker on `Revision.object_str` for revisions created solely for draft sharing
SHARE_REVISION_PREFIX = "[draft-sharing]"


def create_detached_revision(translation, page, user):
    """Create a revision for the pending translation that is not the page's latest.

    The revision exists only so a sharing link has something to point at. Nothing
    about the live page changes.
    """
    pending = translation.source.get_ephemeral_translated_instance(
        translation.target_locale,
        # Untranslated strings will fall back to the original page's text
        fallback=True,
    )
    specific_page = page.specific
    latest_revision_created_at = page.latest_revision.created_at if page.latest_revision else tz_aware_utc_now()
    return Revision.objects.create(
        content_object=specific_page,
        base_content_type=specific_page.get_base_content_type(),
        user=user,
        content=pending.serializable_data(),
        object_str=f"{SHARE_REVISION_PREFIX} {pending}",
        # Ensure this revision is never the official latest revision
        created_at=latest_revision_created_at - timedelta(seconds=1),
    )


def _links_for_page(page):
    """All sharing links for `page`'s revisions."""
    return WagtaildraftsharingLink.objects.filter(revision__in=Revision.objects.for_instance(page))


def _active_links_for_page(page):
    """Active sharing links for `page`."""
    now = tz_aware_utc_now()
    return _links_for_page(page).filter(is_active=True).filter(Q(active_until__isnull=True) | Q(active_until__gt=now))


def delete_dead_sharing_revisions(page):
    """Delete `page`'s revisions used solely by now-inactive sharing links. Returns
    the number of deleted revisions.

    Deleting the revision cascades to its links.
    """
    protected_ids = [pk for pk in (page.latest_revision_id, page.live_revision_id) if pk]
    linked_revision_ids = _links_for_page(page).values_list("revision_id", flat=True)
    active_revision_ids = _active_links_for_page(page).values_list("revision_id", flat=True)

    revisions_to_delete = (
        Revision.objects.for_instance(page)
        .filter(object_str__startswith=SHARE_REVISION_PREFIX)
        .filter(id__in=linked_revision_ids)
        .exclude(id__in=active_revision_ids)
        .exclude(id__in=protected_ids)
    )
    if not revisions_to_delete:
        return 0

    with transaction.atomic():
        for revision in revisions_to_delete:
            # Revision has a custom `delete` method
            revision.delete()
    return len(revisions_to_delete)
