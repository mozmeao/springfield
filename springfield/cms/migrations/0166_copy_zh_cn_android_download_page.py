# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.db import migrations

from springfield.base.config_manager import config

SLUG = "huohu"


def copy_android_download_page(apps, schema_editor):
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    from springfield.cms.models import DownloadPage
    from springfield.cms.wagtail_hooks import regenerate_analytics_ids_on_copy

    android_page = DownloadPage.objects.filter(platform="android", locale__language_code="zh-CN").first()
    if android_page is None or android_page.get_children().filter(slug=SLUG).exists():
        return

    new_page = android_page.copy(
        to=android_page,
        update_attrs={
            "slug": SLUG,
            "show_all_android_download_options": True,
        },
        keep_live=False,
        copy_revisions=False,
        log_action=None,
    )
    regenerate_analytics_ids_on_copy(None, android_page, new_page)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0165_download_page_heading_and_android_options"),
    ]

    operations = [
        migrations.RunPython(copy_android_download_page, reverse_code=migrations.RunPython.noop),
    ]
