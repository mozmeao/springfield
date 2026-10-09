# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Where images are used, grouped for display in the image listing."""

from collections import defaultdict
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType

from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.models import Locale, Page, ReferenceIndex, TranslatableMixin


@dataclass
class UsageGroup:
    """A page or snippet that uses an image, together with its translations that use it too."""

    title: str
    edit_url: str | None
    locale_count: int
    is_snippet: bool


@dataclass
class ImageUsage:
    groups: list[UsageGroup]
    more_count: int


NO_USAGE = ImageUsage(groups=[], more_count=0)


def get_image_usages(images, limit=5):
    """Map each image's pk to the pages and snippets that use it, translations folded together.

    Runs one reference query plus one query per source model, however many images there are.
    Edit URLs are built without permission checks; the edit views enforce permissions.
    """
    references = ReferenceIndex.get_references_to_in_bulk(list(images)).values_list("to_object_id", "base_content_type_id", "object_id").distinct()
    source_keys_by_image_id = defaultdict(set)
    object_ids_by_content_type_id = defaultdict(set)
    for image_id, content_type_id, object_id in references:
        source_keys_by_image_id[int(image_id)].add((content_type_id, object_id))
        object_ids_by_content_type_id[content_type_id].add(object_id)

    sources_by_key = {}
    for content_type_id, object_ids in object_ids_by_content_type_id.items():
        model = ContentType.objects.get_for_id(content_type_id).model_class()
        if model is None:
            continue
        sources = model._default_manager.filter(pk__in=object_ids)
        if issubclass(model, TranslatableMixin):
            sources = sources.select_related("locale")
        for source in sources:
            sources_by_key[(content_type_id, str(source.pk))] = source

    default_locale_id = Locale.get_default().pk
    url_finder = AdminURLFinder()
    usages = {}
    for image_id, source_keys in source_keys_by_image_id.items():
        sources = [sources_by_key[key] for key in source_keys if key in sources_by_key]
        groups = group_translations(sources, default_locale_id, url_finder)
        if groups:
            usages[image_id] = ImageUsage(groups=groups[:limit], more_count=max(0, len(groups) - limit))
    return usages


def group_translations(sources, default_locale_id, url_finder):
    """One UsageGroup per translation set, shown through its default-locale member when it has one.

    Pages come first, then snippets, each sorted by title.
    """
    members_by_translation = defaultdict(list)
    for source in sources:
        translation_key = getattr(source, "translation_key", None) or source.pk
        members_by_translation[(type(source), translation_key)].append(source)

    groups = []
    for members in members_by_translation.values():
        members.sort(key=lambda member: (getattr(member, "locale_id", None) != default_locale_id, member.pk))
        shown_member = members[0]
        groups.append(
            UsageGroup(
                title=str(shown_member),
                edit_url=url_finder.get_edit_url(shown_member),
                locale_count=len(members),
                is_snippet=not isinstance(shown_member, Page),
            )
        )
    groups.sort(key=lambda group: (group.is_snippet, group.title.lower()))
    return groups
