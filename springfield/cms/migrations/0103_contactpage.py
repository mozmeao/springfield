# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import django.db.models.deletion
from django.db import migrations, models

import springfield.cms.fields


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0102_whatsnewpage2026_body_class_and_more"),
        ("wagtailcore", "0096_referenceindex_referenceindex_source_object_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContactPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "og_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Image displayed when this page is shared on social media. Recommended size: 1200×630 pixels (PNG).",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="cms.springfieldimage",
                    ),
                ),
                (
                    "subheading",
                    models.CharField(
                        blank=True,
                        help_text="Optional subheading displayed below the page title.",
                        max_length=255,
                    ),
                ),
                (
                    "form_fields",
                    springfield.cms.fields.StreamField(
                        blank=True,
                        null=True,
                        block_lookup={},
                        help_text="Define the form fields that will appear on the contact page.",
                    ),
                ),
                (
                    "to_email_address",
                    models.EmailField(
                        help_text="Email address where form submissions will be sent.",
                        max_length=254,
                    ),
                ),
                (
                    "redirect_to",
                    models.ForeignKey(
                        help_text="Page to redirect to after a successful form submission (e.g. a thank-you page).",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="wagtailcore.page",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contact Page",
                "verbose_name_plural": "Contact Pages",
            },
            bases=("wagtailcore.page",),
        ),
    ]
