# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Adds the editor-only `internal_title` field to every concrete page model.
# The field is left blank by default: the admin display falls back to the public
# title when `internal_title` is empty (see AbstractSpringfieldCMSPage), so no data
# backfill is needed. Schema-only and rolling-deploy safe on PostgreSQL — adding a
# column with a constant default is a fast metadata-only operation.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0123_alter_articledetailpage_sticker_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="articledetailpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="articleindexpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="articlethemepage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="blogarticlepage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="blogindexpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="contactpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="downloadindexpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="downloadpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="flaredocsindexpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="freeformpage2026",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="referralgetfirefoxpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="referralhubpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="roadmappage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="simplerichtextpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="smartwindowexplainerpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="smartwindowpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="structuralpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="thankspage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="whatsnewindexpage",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="whatsnewpage2026",
            name="internal_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Editor-only label for organizing pages in the CMS. Not shown to the public; the public title is used when blank.",
                max_length=255,
            ),
        ),
    ]
