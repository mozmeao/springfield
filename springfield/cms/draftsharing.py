# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Draft sharing for translated pages.
#
# wagtail-localize does not create draft revision for pages as its translations change,
# so `wagtaildraftsharing` cannot natively create sharing links for translated pages.
# These helpers create revisions for the pending translation that exists solely to be
# shared, without altering the page itself.

from django.db.models import Max, Q

from wagtail.models import Revision
from wagtail_localize.models import SegmentOverride, StringSegment, StringTranslation
from wagtaildraftsharing.models import WagtaildraftsharingLink
from wagtaildraftsharing.utils import tz_aware_utc_now


def create_detached_revision(translation, page, user):
    """Create a revision for the pending translation that is not the page's latest.

    The revision exists only so a sharing link has something to point at. Nothing
    about the live page changes.
    """
    pending = translation.source.get_ephemeral_translated_instance(
        translation.target_locale,
        # Untranslated strings will fallback to the original page's text
        fallback=True,
    )
    specific_page = page.specific
    return Revision.objects.create(
        content_object=specific_page,
        base_content_type=specific_page.get_base_content_type(),
        user=user,
        content=pending.serializable_data(),
        object_str=str(pending),
    )


def latest_translation_edit(translation):
    """When this `translation`'s content was last changed, or None.

    Covers both translated strings and segment overrides. Rows flagged with an error
    are excluded: a failed publish updates their timestamp, but they are not rendered.
    """
    context_ids = StringSegment.objects.filter(source_id=translation.source_id).values_list("context_id", flat=True)
    latest_updates = [
        StringTranslation.objects.filter(
            locale_id=translation.target_locale_id,
            context_id__in=context_ids,
            has_error=False,
        ).aggregate(latest=Max("updated_at"))["latest"],
        SegmentOverride.objects.filter(
            locale_id=translation.target_locale_id,
            context_id__in=context_ids,
            has_error=False,
        ).aggregate(latest=Max("updated_at"))["latest"],
    ]
    return max([latest_update for latest_update in latest_updates if latest_update], default=None)


def _links_for_page(page):
    """All sharing links for `page`'s revisions."""
    return WagtaildraftsharingLink.objects.filter(revision__in=Revision.objects.for_instance(page))


def _active_links_for_page(page):
    """Active sharing links for `page`."""
    now = tz_aware_utc_now()
    return _links_for_page(page).filter(is_active=True).filter(Q(active_until__isnull=True) | Q(active_until__gt=now))


def reusable_sharing_link(translation, page):
    """An existing link whose revision already contains the current translation, or None.

    Allows repeated shares to return the same link instead of creating a duplicate revision.
    """
    active_links_for_page = _active_links_for_page(page).order_by("-revision__created_at")

    latest_edit = latest_translation_edit(translation)
    if latest_edit is not None:
        active_links_for_page = active_links_for_page.filter(revision__created_at__gte=latest_edit)

    return active_links_for_page.first()


def delete_dead_sharing_revisions(page):
    """Delete `page`'s revisions used solely by now-inactive sharing links. Returns
    the number of deleted revisions.

    Deleting the revision cascades to its links.
    """
    protected_ids = [pk for pk in (page.latest_revision_id, page.live_revision_id) if pk]
    linked_revision_ids = _links_for_page(page).values_list("revision_id", flat=True)
    active_revision_ids = _active_links_for_page(page).values_list("revision_id", flat=True)

    dead = Revision.objects.for_instance(page).filter(id__in=linked_revision_ids).exclude(id__in=active_revision_ids).exclude(id__in=protected_ids)
    deleted_count, __ = dead.delete()
    return deleted_count
