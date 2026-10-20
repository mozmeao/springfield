# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

import polib
from wagtail import blocks
from wagtail.fields import StreamField
from wagtail.models import Locale, Page, Site
from wagtail_localize.models import StringSegment, Translation, TranslationSource

from springfield.cms.ftl_parser import (
    build_po_from_ftl,
    build_text_to_msgid_mapping,
    get_english_ftl_strings_at_subpath,
    get_english_ui_strings,
    get_ftl_translations_at_subpath,
    get_ui_translations,
    normalize_text_for_matching,
)
from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
from springfield.cms.models import PretranslatedPhrase, SpringfieldImage

# ---------------------------------------------------------------------------------------------
# The page spec
# ---------------------------------------------------------------------------------------------

FTL_TARGET_LOCALE_CODES = (
    "de",
    "fr",
    "es-ES",
    "es-MX",
    "zh-CN",
    "pt-BR",
    "ru",
    "pl",
    "it",
    "ja",
    "id",
    "nl",
    "tr",
)

# Commands for the pages created in this work.
PAGE_COMMAND_NAMES = (
    "create_mobile_focus_page",
    "create_landing_get_page",
    "create_complete_pdf_page",
    "create_free_pdf_editor_page",
)


@dataclass(frozen=True)
class PageSpec:
    """Everything the command needs to build one scaffold page."""

    slug: str
    page_model: type[models.Model]
    parent_slugs: tuple[str, ...]
    title: str
    ftl_relative_paths: tuple[str, ...]
    target_locale_codes: tuple[str, ...]
    build_fields: Callable[[], dict]
    string_pairs: dict[str, str] | None = None
    # The locale the page is authored in. Defaults to settings.LANGUAGE_CODE. The French PDF pages
    # set "fr": their content only ever existed in French, so there is no English to translate from
    # and no en-US page worth creating. Wagtail is happy with a page that exists in one locale only
    # — 15 such pages are already live in this CMS.
    source_locale_code: str | None = None
    # What the scaffold could not carry across from the old template, printed at the end of a run
    # for whoever finishes the page in the admin.
    editor_notes: tuple[str, ...] = ()


def get_page_specs() -> tuple[PageSpec, ...]:
    """One PageSpec per static page being moved into the CMS.

    The specs live beside the content they describe, one per command module, so this reads them
    back off the commands. The import is deferred because each of those modules imports this one.
    """
    from importlib import import_module

    return tuple(import_module(f"{__package__}.{command_name}").Command.spec for command_name in PAGE_COMMAND_NAMES)


# ---------------------------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------------------------


def build_rich_text(block_key: str, text: str) -> str:
    """Rich text is stored as HTML with a stable block key (fixtures/freeformpage.py:41-43)."""
    return f'<p data-block-key="{block_key}">{text}</p>'


def build_text_block(block_id: str, html: str) -> dict:
    """A `text` block in a page's content StreamField."""
    return {"type": "text", "id": block_id, "value": html}


def import_static_image(*, static_path: str, title: str, description: str = "", is_decorative: bool = False) -> SpringfieldImage:
    """Create a SpringfieldImage from a file in media/, or return the one already imported under `title`.

    `static_path` is relative to the media directory, exactly as the old Django template wrote it:
    "img/firefox/browsers/mobile/focus/tracking-protection.svg".
    """
    existing = SpringfieldImage.objects.filter(title=title).first()
    if existing is not None:
        return existing

    source_file = settings.ROOT_PATH / "media" / static_path
    if not source_file.exists():
        raise FileNotFoundError(f"Cannot import image: {source_file} does not exist")

    return SpringfieldImage.objects.create(
        title=title,
        description=description,
        is_decorative=is_decorative,
        file=ContentFile(source_file.read_bytes(), source_file.name),
    )


def build_screenshot_block(block_id: str, static_path: str, title: str) -> dict:
    """An image embedded in a rich-text block, imported as decorative.

    The templates these pages come from give their screenshots an empty alt, so is_decorative=True
    matches today's behaviour. A how-to screenshot usually deserves a real description, which is
    why every page using this carries an editor note about it.
    """
    image = import_static_image(static_path=static_path, title=title, is_decorative=True)
    return build_text_block(block_id, f'<embed embedtype="image" id="{image.pk}" alt="" format="fullwidth"/>')


def get_pretranslated_label(phrase_key: str) -> int:
    """Return the pk of the English snippet for a pretranslated_label field.

    Button labels come from PretranslatedPhrase snippets, which carry their own translations.
    LabelSourceMixin.clean() (blocks.py:319-325) requires either a pretranslated_label or a
    custom_label on every button block. A pretranslated label is preferable to free text for a
    standard CTA: the translations already exist, so the string never reaches Smartling twice.

    A translation key matches one snippet per locale, so the lookup has to name the source
    locale: an unrestricted .first() hands the English page a German snippet as its label.
    """
    if phrase_key not in PHRASES:
        raise CommandError(f"Unknown pretranslated phrase {phrase_key!r}; known keys: {', '.join(sorted(PHRASES))}")

    snippet = PretranslatedPhrase.objects.filter(
        translation_key=PHRASES[phrase_key]["translation_key"],
        locale__language_code=settings.LANGUAGE_CODE,
    ).first()
    if snippet is None:
        raise CommandError(f"PretranslatedPhrase {phrase_key!r} does not exist yet. Run `manage.py create_pretranslated_phrases` first.")
    return snippet.pk


# ---------------------------------------------------------------------------------------------
# Block validation
#
# The two checks Wagtail does not perform on programmatically built StreamField data.
#
# StreamBlock.to_python keeps only entries whose "type" it recognises, and StructBlock.to_python
# fills missing fields with defaults while ignoring extra ones. Neither raises. Page.full_clean()
# does not reach block validation either: StreamField.clean() calls to_python, validate and
# run_validators, never stream_block.clean(). So a scaffold with a misspelled field name saves,
# renders and passes assertions about block counts, while quietly missing its content.
# ---------------------------------------------------------------------------------------------


class BlockDataError(Exception):
    """Raised when scaffold data names a block type or field Wagtail would silently discard."""


def find_discarded_names(block, value, path):
    """Walk raw StreamField data against the block definitions, collecting names Wagtail would drop."""
    problems = []

    if isinstance(block, blocks.StreamBlock) and isinstance(value, list):
        for index, entry in enumerate(value):
            if not isinstance(entry, dict):
                continue
            block_type = entry.get("type")
            entry_path = f"{path}[{index}]"
            child_block = block.child_blocks.get(block_type)
            if child_block is None:
                problems.append(f"{entry_path}: unknown block type {block_type!r} — Wagtail discards it without an error")
                continue
            problems += find_discarded_names(child_block, entry.get("value"), f"{entry_path}.{block_type}")

    elif isinstance(block, blocks.StructBlock) and isinstance(value, dict):
        for field_name, field_value in value.items():
            child_block = block.child_blocks.get(field_name)
            if child_block is None:
                problems.append(f"{path}: unknown field {field_name!r} — Wagtail replaces it with the block default")
                continue
            problems += find_discarded_names(child_block, field_value, f"{path}.{field_name}")

    elif isinstance(block, blocks.ListBlock) and isinstance(value, list):
        for index, item in enumerate(value):
            item_value = item["value"] if isinstance(item, dict) and item.get("type") == "item" else item
            problems += find_discarded_names(block.child_block, item_value, f"{path}[{index}]")

    return problems


def validate_block_data(page_model, field_name, raw_value) -> None:
    """Raise if any part of `raw_value` names a block or field that does not exist."""
    stream_block = page_model._meta.get_field(field_name).stream_block
    problems = find_discarded_names(stream_block, raw_value, field_name)
    if problems:
        raise BlockDataError(f"{page_model.__name__}.{field_name} has data Wagtail would discard:\n  " + "\n  ".join(problems))


def clean_page_blocks(page, field_names) -> None:
    """Run the block-level clean() methods that Page.full_clean() does not reach.

    This is what the Wagtail admin runs when an editor presses Save, so running it here means
    the editor does not meet our validation errors on a page they have not touched yet.
    """
    for field_name in field_names:
        stream_value = getattr(page, field_name)
        if stream_value:
            stream_value.stream_block.clean(stream_value)


def get_stream_field_names(page_model) -> list[str]:
    return [field.name for field in page_model._meta.get_fields() if isinstance(field, StreamField)]


# ---------------------------------------------------------------------------------------------
# Page creation
# ---------------------------------------------------------------------------------------------


class ScaffoldOutcome(Enum):
    """What `create_scaffold_page` did. Only a newly created page is translated."""

    CREATED = "created"
    REWRITTEN = "rewritten"
    SKIPPED = "skipped"


def get_display_url(page: Page) -> str:
    """The path an operator can paste into a browser.

    `page.url_path` is the internal tree path — `/home/firefox-home/mobile/focus/` on a
    production-shaped tree — and routes to nothing. `get_url_parts()` returns None for a page
    outside any site root, so fall back rather than let a report line raise.
    """
    url_parts = page.get_url_parts()
    return url_parts[2] if url_parts else page.url_path


def get_source_locale(spec: PageSpec) -> Locale:
    return Locale.objects.get(language_code=spec.source_locale_code or settings.LANGUAGE_CODE)


def resolve_parent_page(spec: PageSpec) -> Page:
    """Walk the slug chain down from the site root page for the spec's own locale.

    Slug-only lookups are ambiguous across the tree — `developer` matches both
    `/channel/desktop/developer/` and `/whatsnew/developer/` — so the whole chain is walked.

    Each locale has its own tree root: the default site's root is the en-US one, and French lives
    under a separate root that is its translation. Walking the default root with a French locale
    filter would find nothing, because the French pages are not its children.
    """
    source_locale = get_source_locale(spec)
    page = Site.objects.get(is_default_site=True).root_page
    if page.locale_id != source_locale.pk:
        page = Page.objects.filter(translation_key=page.translation_key, locale=source_locale).first()
        if page is None:
            raise CommandError(
                f"{spec.slug}: the site root has no {source_locale.language_code} translation, so there is no "
                f"{source_locale.language_code} tree to create the page in."
            )
    for slug in spec.parent_slugs:
        page = page.get_children().get(slug=slug, locale=source_locale)
    return page.specific


def check_fields_before_saving(spec: PageSpec, field_values: dict) -> None:
    stream_field_names = set(get_stream_field_names(spec.page_model))
    for field_name, value in field_values.items():
        if field_name in stream_field_names:
            validate_block_data(spec.page_model, field_name, value)


# add_child() writes the page before clean_page_blocks() gets to reject its data. The command runs
# this inside its own transaction, but a Task 4-6 script or a shell calling it directly would be
# left with a half-written page.
@transaction.atomic
def create_scaffold_page(spec: PageSpec, *, force: bool) -> tuple[Page, ScaffoldOutcome]:
    """Create the draft page, or return the existing one untouched.

    A live page is never touched: this command only writes drafts. Without `force` an existing
    page, live or not, is skipped; with `force` a live page stops the run.
    """
    field_values = spec.build_fields()
    check_fields_before_saving(spec, field_values)

    parent = resolve_parent_page(spec)
    existing = parent.get_children().filter(slug=spec.slug).first()

    if existing is not None:
        if not force:
            return existing.specific, ScaffoldOutcome.SKIPPED
        if existing.live:
            raise CommandError(
                f"{get_display_url(existing)} is live in the CMS. This command only ever writes drafts; refusing to "
                f"overwrite published content. Unpublish it first if that is really what you want."
            )

        # Update in place so the page keeps its pk, translation_key, TranslationSource and translations.
        page = existing.specific
        page.title = spec.title
        for field_name, value in field_values.items():
            setattr(page, field_name, value)
        outcome = ScaffoldOutcome.REWRITTEN
    else:
        page = spec.page_model(
            slug=spec.slug,
            title=spec.title,
            locale=get_source_locale(spec),
            live=False,
            **field_values,
        )
        parent.add_child(instance=page)
        outcome = ScaffoldOutcome.CREATED

    clean_page_blocks(page, get_stream_field_names(spec.page_model))
    page.live = False
    page.save()
    page.save_revision()
    return page, outcome


# ---------------------------------------------------------------------------------------------
# Translation import
#
# Import the FTL translations a static page already had into its CMS scaffold. The pipeline
# mirrors create_pretranslated_phrases.py: English FTL strings become a {normalized text: message
# id} mapping, each locale's FTL file supplies the translated text, and the two are matched
# against the page's wagtail-localize segments to build a PO file to import.
# ---------------------------------------------------------------------------------------------


def get_english_strings_for_paths(ftl_relative_paths: tuple[str, ...]) -> dict[str, str]:
    """Union the English strings from every FTL file a page uses, plus the shared ui strings.

    Each path is checked on its own rather than only the union: one file of several moving or
    being renamed would otherwise leave a quietly reduced string set and an import that reports
    success while translating less than it should.
    """
    strings: dict[str, str] = {}
    for ftl_relative_path in ftl_relative_paths:
        strings_at_path = get_english_ftl_strings_at_subpath(ftl_relative_path)
        if not strings_at_path:
            raise CommandError(f"Found no English strings in {ftl_relative_path} — has the FTL file moved?")
        strings.update(strings_at_path)

    strings.update(get_english_ui_strings())
    return strings


def get_translations_for_paths(locale_code: str, ftl_relative_paths: tuple[str, ...]) -> dict[str, str]:
    translations: dict[str, str] = {}
    for ftl_relative_path in ftl_relative_paths:
        translations.update(get_ftl_translations_at_subpath(locale_code, ftl_relative_path))
    translations.update(get_ui_translations(locale_code))
    return translations


def get_latest_schema_version() -> str:
    """Mirrors create_pretranslated_phrases.py:77-80."""
    # springfield/cms/management/commands/ -> springfield/cms/migrations/
    migrations_directory = Path(__file__).parent.parent.parent / "migrations"
    migration_names = sorted(migration_file.stem for migration_file in migrations_directory.glob("0*.py"))
    return migration_names[-1] if migration_names else ""


def get_translation_source(page) -> TranslationSource:
    source, created = TranslationSource.get_or_create_from_instance(page)
    if not created:
        # update_from_db() first, or refresh_segments() re-extracts the stale stored source
        # and a re-run translates content that is no longer on the page.
        source.update_from_db()
        source.refresh_segments()
    source.schema_version = get_latest_schema_version()
    source.save(update_fields=["schema_version"])
    return source


@dataclass(frozen=True)
class TranslationReport:
    """What `translate_page` managed to do, for the command to report to the operator."""

    strings_imported: int
    locales_translated: tuple[str, ...]
    locales_missing_a_translated_parent: tuple[str, ...]


def translate_page(page, spec, locale_codes: tuple[str, ...]) -> TranslationReport:
    """Register the TranslationSource and import FTL translations for each locale."""
    english_strings = get_english_strings_for_paths(spec.ftl_relative_paths)
    english_text_to_msgid = build_text_to_msgid_mapping(english_strings)
    source = get_translation_source(page)
    parent_page = page.get_parent()

    strings_imported = 0
    locales_translated = []
    locales_missing_a_translated_parent = []

    for locale_code in locale_codes:
        # save_target() passes copy_parent_pages=True, and an untranslated ancestor is copied in
        # as an alias, which inherits live=True from its source. This command only ever writes
        # drafts, so a locale whose parent is not translated yet waits for it instead.
        target_locale = Locale.objects.filter(language_code=locale_code).first()
        if target_locale is None or not parent_page.has_translation(target_locale):
            locales_missing_a_translated_parent.append(locale_code)
            continue

        translated_strings = get_translations_for_paths(locale_code, spec.ftl_relative_paths)
        if not translated_strings:
            continue

        translation, _ = Translation.objects.get_or_create(source=source, target_locale=target_locale)
        po = build_po_from_ftl(translation, english_text_to_msgid, translated_strings)
        # build_po_from_ftl always returns a POFile; an empty one is falsy because POFile
        # subclasses list. Check truthiness, not None-ness.
        if not po:
            continue

        translation.import_po(po, delete=False, translation_type="manual", tool_name="ftl_import")
        translation.save_target(publish=False)
        strings_imported += len(po)
        locales_translated.append(locale_code)

    return TranslationReport(
        strings_imported=strings_imported,
        locales_translated=tuple(locales_translated),
        locales_missing_a_translated_parent=tuple(locales_missing_a_translated_parent),
    )


def build_po_from_text_pairs(translation, source_to_target: dict[str, str]) -> polib.POFile:
    """Build a PO by matching Wagtail segments against a plain {source text: target text} mapping.

    build_po_from_ftl goes through FTL message ids and rewrites FTL link syntax. The PDF pages have
    no FTL message ids and no FTL link syntax — their French is the source of record — so they match
    on normalized text directly.
    """
    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=utf-8",
        "X-WagtailLocalize-TranslationID": str(translation.uuid),
    }

    normalized_pairs = {normalize_text_for_matching(source): target for source, target in source_to_target.items()}

    for segment in StringSegment.objects.filter(source=translation.source).select_related("string", "context"):
        target_text = normalized_pairs.get(normalize_text_for_matching(segment.string.data))
        if target_text:
            po.append(polib.POEntry(msgid=segment.string.data, msgctxt=segment.context.path, msgstr=target_text))

    return po


# ---------------------------------------------------------------------------------------------
# The shared command
# ---------------------------------------------------------------------------------------------

PUBLISHING_WARNING = (
    "\nThis page is a draft. Its route already carries prefer_cms, so publishing one serves it to "
    "the public immediately — there is no second switch to throw."
)


class CreatePageCommand(BaseCommand):
    """Subclasses set `help` and `spec` and nothing else."""

    spec: PageSpec

    def add_arguments(self, parser):
        parser.add_argument(
            "--locales",
            nargs="+",
            metavar="CODE",
            help="Limit translation to these locale codes. Defaults to every locale the page targets.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Rewrite an existing draft in place. Without this, an existing page is left alone. "
                "Translations are never re-imported, with or without this flag."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Roll the transaction back at the end: report what would happen and write no CMS pages. "
                "Images imported along the way stay in media storage."
            ),
        )

    def handle(self, *args, **options):
        spec = self.spec

        with transaction.atomic():
            live_page_pks_before = self.get_live_page_pks()

            try:
                page, outcome = create_scaffold_page(spec, force=options["force"])
            except BlockDataError as error:
                raise CommandError(f"{spec.slug}: {error}") from error
            except Page.DoesNotExist as error:
                parent_path = "/".join(spec.parent_slugs)
                raise CommandError(f"{spec.slug}: no page at /{parent_path}/ below the default site root — create it first.") from error

            self.report_outcome(page, outcome)

            # Only a page this run created is translated. Re-importing the FTL strings over a page
            # that already has translations would overwrite the ones an editor corrected by hand,
            # which is the data loss --force exists to prevent, not to cause. A force-rewrite keeps
            # its translation_key, so the translations stay attached and wagtail-localize marks the
            # segments that changed as needing translation.
            if outcome is ScaffoldOutcome.CREATED:
                self.translate(page, spec, options)

            self.check_nothing_was_published(live_page_pks_before)
            self.report_editor_notes(spec)

            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run: everything above was rolled back."))

    def translate(self, page, spec, options):
        # A page authored in its own locale has nothing to translate from — no FTL files, no source
        # English. Entering the translate phase would only build an unused TranslationSource.
        if not spec.target_locale_codes:
            self.stdout.write("  no translations for this page (authored in its own locale)")
            return

        locale_codes = options["locales"] or spec.target_locale_codes
        # A locale the site is not configured for would otherwise be reported as merely missing a
        # translated parent, which hides the typo that caused it.
        cms_language_codes = {language_code for language_code, _label in settings.WAGTAIL_CONTENT_LANGUAGES}
        unknown_codes = set(locale_codes) - cms_language_codes
        if unknown_codes:
            raise CommandError(f"Not CMS locales: {', '.join(sorted(unknown_codes))}")

        self.report_translations(page, translate_page(page, spec, locale_codes))

    def get_live_page_pks(self) -> set[int]:
        return set(Page.objects.filter(live=True).values_list("pk", flat=True))

    def check_nothing_was_published(self, live_page_pks_before: set[int]) -> None:
        """Stop the run if any page went live, and roll the whole thing back.

        Every page this command writes is a draft for an editor to finish, so nothing here should
        ever publish. wagtail-localize already broke that once without anyone predicting it:
        save_target() passes copy_parent_pages=True, and an untranslated ancestor copied in as an
        alias inherits live=True. Raising inside the transaction turns the next such surprise into
        a rollback and a message rather than live content on the site.
        """
        published_pks = self.get_live_page_pks() - live_page_pks_before
        if not published_pks:
            return

        published_pages = Page.objects.filter(pk__in=published_pks).select_related("locale").order_by("path")
        raise CommandError(
            "This command only ever writes drafts, but this run published "
            f"{len(published_pks)} page(s):\n  "
            + "\n  ".join(f"pk={page.pk} {page.locale.language_code} {page.url_path}" for page in published_pages)
            + "\nThe whole run has been rolled back and nothing was saved. You did not do anything "
            "wrong — this is a bug in the command, and the list above is worth reporting as one."
        )

    def report_outcome(self, page, outcome):
        display_url = get_display_url(page)
        if outcome is ScaffoldOutcome.CREATED:
            self.stdout.write(self.style.SUCCESS(f"Draft written: {display_url}"))
        elif outcome is ScaffoldOutcome.REWRITTEN:
            self.stdout.write(self.style.SUCCESS(f"Draft rewritten: {display_url} (translations left as they were)"))
        elif page.live:
            self.stdout.write(self.style.WARNING(f"Live, skipped: {display_url} (never overwritten)"))
        else:
            self.stdout.write(f"Already exists, left alone: {display_url} (use --force to rewrite)")

    def report_translations(self, page, report):
        self.stdout.write(f"  translated {len(report.locales_translated)} locales, {report.strings_imported} strings")
        if not report.locales_missing_a_translated_parent:
            return

        parent_url = get_display_url(page.get_parent())
        for locale_code in report.locales_missing_a_translated_parent:
            self.stdout.write(
                self.style.WARNING(
                    f"  skipped {locale_code}: {parent_url} has no {locale_code} translation, and translating under it "
                    f"would publish it as a live alias. Translate the parent and re-run."
                )
            )

    def report_editor_notes(self, spec):
        """What the scaffold could not carry across, for whoever finishes the page."""
        if spec.editor_notes:
            self.stdout.write("\nAn editor still needs to:")
            for note in spec.editor_notes:
                self.stdout.write(f"  - {note}")
        self.stdout.write(self.style.WARNING(PUBLISHING_WARNING))
