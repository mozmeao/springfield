# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Add the User Routing framework: RoutingRule + RoutingCondition (AND-
# semantics inline) attachable to WhatsNewPage2026 canonicals, plus the
# routing_paused kill switch. Consumed by ``springfield.cms.routing``
# (dispatcher, evaluator, resolver page) and the ``wnp_dispatch`` wrapper
# in ``springfield.firefox.views``.

import django.db.models.deletion
from django.db import migrations, models

import modelcluster.fields

import springfield.cms.models.routing


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0121_contactpage_body_class_contactpage_extra_js_and_more"),
        ("wagtailcore", "0097_baselogentry_uuid_action_timestamp_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="whatsnewpage2026",
            name="routing_paused",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Emergency kill switch — when on, the dispatcher short-circuits and canonical serves regardless of rule state. "
                    "Use to stop all routing behavior without unpublishing or archiving individual rules. Flip back off to resume."
                ),
                verbose_name="Pause routing",
            ),
        ),
        migrations.CreateModel(
            name="RoutingRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                (
                    "name",
                    models.CharField(
                        help_text="Human-readable name shown in the admin (e.g. 'Lapsed users → welcomeback').",
                        max_length=255,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("live", "Live"), ("archived", "Archived")],
                        default="draft",
                        help_text="Only 'Live' rules are evaluated by the resolver.",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent_page",
                    modelcluster.fields.ParentalKey(
                        help_text="The canonical page this rule attaches to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="routing_rules",
                        to="cms.whatsnewpage2026",
                    ),
                ),
                (
                    "target_page",
                    models.ForeignKey(
                        help_text="The variant page to route matching users to.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="routing_rules_as_target",
                        to="wagtailcore.page",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Routing rule",
                "verbose_name_plural": "User Routing rules",
                "ordering": ["parent_page", "sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="RoutingCondition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                (
                    "signal_name",
                    models.CharField(
                        blank=True,
                        choices=springfield.cms.models.routing._signal_choices,
                        help_text="Which browser or server signal this condition checks.",
                        max_length=64,
                    ),
                ),
                (
                    "operator",
                    models.CharField(
                        choices=[("is", "is"), ("is_not", "is not")],
                        default="is",
                        help_text="`is` matches when the signal is one of the values below; `is not` matches when it isn't.",
                        max_length=16,
                    ),
                ),
                (
                    "expected_values",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text=(
                            "One or more values, one per line (commas also accepted). "
                            "For enum-valued signals, values must match the exact allowed set "
                            "(check the signal's help entry). Booleans: 'true' or 'false'. "
                            "Integers: a number."
                        ),
                    ),
                ),
                (
                    "rule",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conditions",
                        to="cms.routingrule",
                    ),
                ),
            ],
            options={
                "verbose_name": "condition",
                "verbose_name_plural": "conditions",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="routingrule",
            index=models.Index(
                fields=["parent_page", "status", "sort_order"],
                name="cms_routing_parent__6ddacd_idx",
            ),
        ),
    ]
