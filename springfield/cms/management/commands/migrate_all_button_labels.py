# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command to migrate the **non-download** button blocks from the
old plain-string ``label`` format to the new ``pretranslated_label`` / ``custom_label``
structure introduced by ``LabelSourceMixin``.

Unlike ``migrate_download_button_labels`` (which owns ``download_button`` and does a
PretranslatedPhrase lookup), this command:

- converts every non-download label-bearing button type (``BUTTON_TYPES_WITH_LABEL``);
- does **no** snippet lookup — every old ``label`` becomes ``custom_label`` (no
  non-download button text matches the two seeded download phrases, so the lookup
  would always miss). It is therefore locale-agnostic;
- discovers target models by walking the **live** model registry for StreamFields
  (pages *and* snippets), instead of a hardcoded page list, so snippet StreamFields
  (e.g. ``BannerSnippet.buttons``) and any future page are covered;
- runs as a single atomic transaction (like every other data migration here).

The same conversion is applied to each model's revisions.
"""

import json
import logging
from collections.abc import MutableSequence

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.fields import StreamField as WagtailStreamField
from wagtail.models import Revision, RevisionMixin
from wagtail_localize.models import StringTranslation, TranslationContext, TranslationSource

logger = logging.getLogger(__name__)


BUTTON_TYPES_WITH_LABEL = {
    "button",
    "uitour_button",
    "fxa_button",
    "set_as_default_button",
    "focus_button",
    # NOTE: "download_button" is intentionally absent — download buttons are owned by
    # the migrate_download_button_labels command, which DOES do the snippet
    # lookup this command omits.
}


def convert_button_label(data):
    """
    Recursively convert ``label`` → ``custom_label`` in all non-download button blocks.

    Unlike ``convert_download_button_label``, this does NO PretranslatedPhrase lookup:
    no non-download button text matches the two seeded download phrases, so every row
    takes the ``custom_label`` branch. Locale-agnostic by design.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") in BUTTON_TYPES_WITH_LABEL and isinstance(data.get("value"), dict):
            value = data["value"]
            old_label = value.get("label")
            if isinstance(old_label, str):
                value["pretranslated_label"] = None
                value["custom_label"] = old_label
                del value["label"]
                changed = True
        for v in list(data.values()):
            if convert_button_label(v):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_button_label(item):
                changed = True
    return changed


def _models_with_streamfields():
    """
    Yield ``(Model, [stream_field_names], [(inherited_field, parent_class_name)])``
    for every concrete ``cms`` model in the LIVE model registry that declares one or
    more StreamFields. Includes both pages and snippets, and picks up StreamFields
    inherited from abstract base classes.

    Walks the live model state — NOT historical migration state — so it must not be
    called from a RunPython op against a historical apps registry.
    """
    # wagtail.fields.StreamField is the base class; the project's
    # springfield.cms.fields.StreamField alias is a subclass, so the base catches both.
    for model in apps.get_models():
        if model._meta.app_label != "cms":
            continue
        names = []
        inherited = []
        for field in model._meta.get_fields():
            if isinstance(field, WagtailStreamField):
                names.append(field.name)
                if field.model is not model:
                    inherited.append((field.name, field.model.__name__))
        if names:
            yield model, names, inherited


class Command(BaseCommand):
    help = "Migrate non-download button labels from plain strings to pretranslated_label/custom_label."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made.\n"))

        models = list(_models_with_streamfields())
        self._print_scan_summary(models)

        for model, field_names, _inherited in models:
            self._convert_objects(model, field_names, dry_run)
            # Revisions only exist for RevisionMixin models (snippets via
            # BaseDraftTranslatableSnippetMixin; pages via Page). field_names is each
            # model's OWN list, so BannerSnippet.buttons revisions get walked too.
            if issubclass(model, RevisionMixin):
                self._convert_revisions(model, field_names, dry_run)

        self._update_translation_sources([m for m, _, _ in models], dry_run)
        self._relink_button_translations(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration complete.\n"))

    def _print_scan_summary(self, models):
        """Print which StreamField models were found, with row counts, so the registry
        walk is observable rather than a silent dependency (§6.4)."""
        self.stdout.write("Scanning live model registry for StreamFields:\n")
        total_rows = 0
        empty_models = 0
        for model, field_names, inherited in models:
            row_count = model.objects.count()
            total_rows += row_count
            inherited_by_field = dict(inherited)
            field_display = ", ".join(
                f"{name} (inherits {name} from {inherited_by_field[name]})" if name in inherited_by_field else name for name in field_names
            )
            if row_count == 0:
                empty_models += 1
                status = "empty"
            else:
                status = "scanned"
            self.stdout.write(f"  {model.__name__}  fields=[{field_display}]  rows={row_count}  {status}\n")
        self.stdout.write(f"Total: {len(models)} models with StreamFields, {total_rows} rows scanned, {empty_models} empty\n")

    def _convert_objects(self, model, field_names, dry_run):
        """Convert the live rows of one model. Saves with ``update_fields`` so we only
        touch the changed StreamFields (and don't create new revisions)."""
        total = 0
        for obj in model.objects.all():
            changed_fields = []
            for field_name in field_names:
                stream_value = getattr(obj, field_name)
                if stream_value and convert_button_label(stream_value.raw_data):
                    changed_fields.append(field_name)
            if changed_fields:
                if not dry_run:
                    obj.save(update_fields=changed_fields)
                total += 1
                self.stdout.write(f"  {model.__name__} pk={obj.pk}: updated {', '.join(changed_fields)}\n")
        if total:
            self.stdout.write(f"  {model.__name__}: {total} rows updated.\n")

    def _convert_revisions(self, model, field_names, dry_run):
        """Convert this model's revisions in place, walking ITS OWN field_names (not the
        hardcoded page-field list the download command uses — that would skip
        BannerSnippet.buttons and any other non-page StreamField)."""
        content_type = ContentType.objects.get_for_model(model)
        total_revised = 0
        for revision in Revision.objects.filter(content_type=content_type).iterator():
            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                if convert_button_label(field_data):
                    revision.content[field_name] = json.dumps(field_data)
                    modified = True
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total_revised += 1
        if total_revised:
            self.stdout.write(f"  {model.__name__}: {total_revised} revisions updated.\n")

    def _update_translation_sources(self, models, dry_run):
        """Re-sync wagtail-localize TranslationSource snapshots so they reflect the new
        block structure.

        Only updates the source's serialized content (``update_from_db``) — does NOT
        call ``create_or_update_translation()``, which would re-materialize translated
        objects and can silently drop blocks whose segments don't match the updated
        schema. The migration converts each translated row directly (so live translated
        pages/snippets keep rendering), and the re-pathed segments re-sync through the
        normal Smartling workflow on next publish. The mixin has no legacy-``label``
        fallback, so any old-format row that survives the migration renders a blank
        label — there is no silent old-format rendering path.
        """
        self.stdout.write("Updating TranslationSource records...\n")

        if dry_run:
            self.stdout.write("  Skipping TranslationSource sync in dry-run mode.\n")
            return

        content_type_ids = [ContentType.objects.get_for_model(m).pk for m in models]
        sources_updated = 0
        for source in TranslationSource.objects.filter(specific_content_type_id__in=content_type_ids):
            try:
                source.update_from_db()
                sources_updated += 1
            except Exception:
                ct = ContentType.objects.get_for_id(source.specific_content_type_id)
                try:
                    obj = source.get_source_instance()
                except Exception:
                    obj = None
                logger.warning(
                    "Failed to update TranslationSource pk=%s (%s.%s, object_id=%s, object=%s).",
                    source.pk,
                    ct.app_label,
                    ct.model,
                    source.object_id,
                    obj,
                    exc_info=True,
                )

        self.stdout.write(f"  {sources_updated} TranslationSources updated.\n")

    def _relink_button_translations(self, dry_run):
        """Re-link orphaned StringTranslations after the ``label`` → ``custom_label`` rename.

        wagtail-localize keys a translation by its segment's content path. Renaming a
        button's ``label`` child to ``custom_label`` moves the source segment to a new
        path (``…<block_id>.custom_label``), leaving the existing StringTranslations
        stranded at the old ``…<block_id>.label`` path. The live row already holds the
        translated text (so public pages are unaffected), but the translation editor and
        preview no longer see those translations.

        For every old ``.label`` context whose sibling ``.custom_label`` context exists
        (created by ``_update_translation_sources`` above), copy each translation across.
        The source text is unchanged, so both contexts reference the same ``String`` and
        the copied translation matches the new segment. Idempotent via ``get_or_create``.
        """
        self.stdout.write("Re-linking button translations (label -> custom_label)...\n")

        if dry_run:
            self.stdout.write("  Skipping translation re-link in dry-run mode.\n")
            return

        # (object_id, path) of every custom_label context, to find an old .label context's sibling.
        custom_label_keys = set(TranslationContext.objects.filter(path__endswith=".custom_label").values_list("object_id", "path"))

        relinked = 0
        for old_ctx in TranslationContext.objects.filter(path__endswith=".label").iterator():
            new_path = old_ctx.path[: -len(".label")] + ".custom_label"
            if (old_ctx.object_id, new_path) not in custom_label_keys:
                continue  # not a renamed button field (e.g. a link block's own .label)
            new_ctx = TranslationContext.objects.get(object_id=old_ctx.object_id, path=new_path)
            for st in StringTranslation.objects.filter(context=old_ctx):
                _, created = StringTranslation.objects.get_or_create(
                    translation_of=st.translation_of,
                    locale=st.locale,
                    context=new_ctx,
                    defaults={
                        "data": st.data,
                        "translation_type": st.translation_type,
                        "tool_name": st.tool_name,
                        "last_translated_by": st.last_translated_by,
                    },
                )
                if created:
                    relinked += 1

        self.stdout.write(f"  {relinked} button translations re-linked.\n")
