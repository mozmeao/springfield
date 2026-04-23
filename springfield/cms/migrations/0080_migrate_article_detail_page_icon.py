# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def migrate_article_icon_values(apps, schema_editor):
    from springfield.cms.icon_utils import ICON_VALUE_MAP
    from springfield.cms.models.pages import ArticleDetailPage

    to_update = []
    for page in ArticleDetailPage.objects.exclude(icon=""):
        new_val = ICON_VALUE_MAP.get(page.icon, page.icon)
        if new_val != page.icon:
            page.icon = new_val
            to_update.append(page)
    if to_update:
        ArticleDetailPage.objects.bulk_update(to_update, ["icon"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0079_update_article_detail_page_icon"),
    ]

    operations = [
        migrations.RunPython(migrate_article_icon_values, migrations.RunPython.noop),
    ]
