# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Rename the ``retired`` rule status to ``archived`` for consistency with
# the design plan's terminology. Any existing rows with status="retired"
# are data-migrated to status="archived"; behavior is unchanged (both
# statuses meant "attached but not evaluated by the dispatcher").

from django.db import migrations, models


def forwards_rename_retired(apps, schema_editor):
    RoutingRule = apps.get_model("cms", "RoutingRule")
    RoutingRule.objects.filter(status="retired").update(status="archived")


def backwards_rename_archived(apps, schema_editor):
    RoutingRule = apps.get_model("cms", "RoutingRule")
    RoutingRule.objects.filter(status="archived").update(status="retired")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0116_remove_routingrule_expected_value_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="routingrule",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("live", "Live"), ("archived", "Archived")],
                default="draft",
                help_text="Only 'Live' rules are evaluated by the resolver.",
                max_length=16,
            ),
        ),
        migrations.RunPython(forwards_rename_retired, backwards_rename_archived),
    ]
