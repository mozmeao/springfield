# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0077_articleindexpage_show_sibling_detail_pages"),
    ]

    operations = [
        migrations.AddField(
            model_name="articleindexpage",
            name="index_card_type",
            field=models.CharField(
                choices=[
                    ("sticker_card", "Sticker card"),
                    ("outline_card", "Outline card"),
                    ("illustration_card", "Illustration card"),
                ],
                default="sticker_card",
                help_text="Controls the card style used in the article listing.",
                max_length=20,
            ),
        ),
    ]
