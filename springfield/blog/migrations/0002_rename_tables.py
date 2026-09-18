# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Renames the blog model tables from cms_* to blog_*.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(name="blogarticleauthor", table=None),
        migrations.AlterModelTable(name="blogarticlepage", table=None),
        migrations.AlterModelTable(name="blogauthor", table=None),
        migrations.AlterModelTable(name="blogindexpage", table=None),
        migrations.AlterModelTable(name="blogtag", table=None),
        migrations.AlterModelTable(name="blogtopic", table=None),
        migrations.AlterModelTable(name="blogtopicpage", table=None),
        migrations.AlterModelTable(name="taggedblogarticle", table=None),
    ]
