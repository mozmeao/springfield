# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration realigning every translated What's New page's version with its
# en-US source. The field was declared synchronized but left overridable, so the
# translation editor offered it as an input.

import os
import sys

from django.db import migrations

from springfield.base.config_manager import config

SOURCE_LANGUAGE = "en-US"


def sync_versions_from_source(apps, schema_editor):
    # Skip in test environments and CI — test fixtures create the data they need.
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    WhatsNewPage2026 = apps.get_model("cms", "WhatsNewPage2026")

    source_versions = dict(WhatsNewPage2026.objects.filter(locale__language_code=SOURCE_LANGUAGE).values_list("translation_key", "version"))

    for page in WhatsNewPage2026.objects.exclude(locale__language_code=SOURCE_LANGUAGE).iterator():
        source_version = source_versions.get(page.translation_key)
        if source_version is None or page.version == source_version:
            continue

        page.version = source_version
        page.save(update_fields=["version"])

        # The draft an editor next publishes carries its own copy of the field, so
        # leaving it stale would put the translated version straight back.
        revision = page.latest_revision
        if revision and revision.content.get("version") != source_version:
            revision.content["version"] = source_version
            revision.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0151_merge_20260904_2119"),
    ]

    operations = [
        migrations.RunPython(sync_versions_from_source, migrations.RunPython.noop),
    ]
