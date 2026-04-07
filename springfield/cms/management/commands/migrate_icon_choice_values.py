# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from wagtail.fields import StreamField
from wagtail.models import Revision

from springfield.cms.icon_utils import ICON_VALUE_MAP
from springfield.cms.models.pages import (
    ArticleDetailPage,
    ArticleThemePage,
    DownloadPage,
    FreeFormPage,
    FreeFormPage2026,
    HomePage,
    WhatsNewPage,
    WhatsNewPage2026,
)

MODELS = [
    FreeFormPage,
    FreeFormPage2026,
    WhatsNewPage,
    WhatsNewPage2026,
    HomePage,
    ArticleDetailPage,
    ArticleThemePage,
    DownloadPage,
]


def _walk(value, value_map):
    """Recursively replace icon values in-place in the parsed stream JSON."""
    if isinstance(value, list):
        for item in value:
            _walk(item, value_map)
    elif isinstance(value, dict):
        for key, v in list(value.items()):
            if key == "icon" and isinstance(v, str) and v in value_map:
                value[key] = value_map[v]
            else:
                _walk(v, value_map)


class Command(BaseCommand):
    help = "Migrate IconChoiceBlock stored values from old stems to new directory paths."

    def handle(self, *args, **options):
        value_map = ICON_VALUE_MAP  # default is "" for any icons not in the directory

        streamfield_names = {model: [f.name for f in model._meta.get_fields() if isinstance(f, StreamField)] for model in MODELS}

        # --- Update live model instances ---
        for model in MODELS:
            for fname in streamfield_names[model]:
                field = model._meta.get_field(fname)
                for instance in model.objects.all():
                    stream_value = getattr(instance, fname)
                    # get_prep_value converts StreamValue → plain Python list.
                    # Wagtail 5+ StreamField inherits from Django JSONField, so passing
                    # a Python list back via queryset.update() is handled natively.
                    stream_json = field.get_prep_value(stream_value)
                    _walk(stream_json, value_map)
                    # Use queryset.update to avoid triggering post_save signals.
                    model.objects.filter(pk=instance.pk).update(**{fname: stream_json})

        # --- Update Revision rows ---
        # Revision.content is a JSONField; StreamField values are double-serialised
        # (stored as a JSON string inside the JSON object) — must json.loads/dumps.
        for model in MODELS:
            ct = ContentType.objects.get_for_model(model, for_concrete_model=False)
            revisions_to_update = []
            for revision in Revision.objects.filter(content_type=ct):
                changed = False
                for fname in streamfield_names[model]:
                    raw = revision.content.get(fname)
                    if raw is None:
                        continue
                    stream_json = json.loads(raw)
                    before = json.dumps(stream_json)
                    _walk(stream_json, value_map)
                    if json.dumps(stream_json) != before:
                        revision.content[fname] = json.dumps(stream_json)
                        changed = True
                if changed:
                    revisions_to_update.append(revision)
            if revisions_to_update:
                Revision.objects.bulk_update(revisions_to_update, ["content"])

        self.stdout.write("Icon value migration complete.\n")
