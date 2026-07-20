# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations

import springfield.cms.fields
import springfield.cms.rich_text


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0120_referralgetfirefoxpage_referralhubpage"),
    ]

    operations = [
        migrations.AddField(
            model_name="referralhubpage",
            name="heading_text",
            field=springfield.cms.rich_text.RichTextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="referralhubpage",
            name="subheading_text",
            field=springfield.cms.rich_text.RichTextField(blank=True),
        ),
        migrations.AddField(
            model_name="referralhubpage",
            name="content",
            field=springfield.cms.fields.StreamField(blank=True, block_lookup={}, null=True),
        ),
    ]
