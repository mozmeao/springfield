# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from dataclasses import replace
from io import StringIO
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError

import pytest
import wagtail_factories
from wagtail.models import Locale, Page, Site

from springfield.cms.blocks import NumberedListBlock
from springfield.cms.management.commands._page_scaffold import (
    FTL_TARGET_LOCALE_CODES,
    BlockDataError,
    clean_page_blocks,
    find_discarded_names,
    get_page_specs,
    validate_block_data,
)
from springfield.cms.management.commands.create_mobile_focus_page import Command as MobileFocusCommand
from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
from springfield.cms.models import FreeFormPage2026, PretranslatedPhrase
from springfield.cms.tests.factories import (
    ArticleThemePageFactory,
    FreeFormPage2026Factory,
    SimpleRichTextPageFactory,
    StructuralPageFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def pretranslated_phrases():
    """Create all pre-translated phrases from PHRASES."""
    return {
        key: PretranslatedPhrase.objects.update_or_create(
            translation_key=info["translation_key"],
            locale=Locale.get_default(),
            defaults={"label": info["label"], "live": True},
        )[0]
        for key, info in PHRASES.items()
    }


@pytest.fixture
def scaffold_parents(client, pretranslated_phrases):
    """Build the slice of the page tree the scaffolded pages hang off.

    The test database has no page tree of its own: `minimal_site` creates a root page and one
    /test-page/. resolve_parent_page() walks slugs down from Site.root_page, so /mobile/,
    /landing/ and /features/ have to exist before any of these tests can run at all.
    """
    en_us_locale = Locale.objects.get(language_code="en-US")
    default_seed_page = Page.objects.get(depth=2, slug="home")
    root_page = SimpleRichTextPageFactory(
        title="Firefox Home",
        slug="firefox-home",
        parent=default_seed_page,
        live=True,
        locale=en_us_locale,
    )

    try:
        site = Site.objects.get(is_default_site=True)
        site.root_page = root_page
        site.hostname = client._base_environ()["SERVER_NAME"]
        site.save()
    except Site.DoesNotExist:
        wagtail_factories.SiteFactory(
            root_page=root_page,
            is_default_site=True,
            hostname=client._base_environ()["SERVER_NAME"],
        )

    parents = SimpleNamespace(
        root_page=root_page,
        mobile=FreeFormPage2026Factory(slug="mobile", title="Mobile", parent=root_page, locale=en_us_locale, live=True),
        landing=StructuralPageFactory(slug="landing", title="Landing", parent=root_page, locale=en_us_locale, live=True),
        features=ArticleThemePageFactory(slug="features", title="Features", parent=root_page, locale=en_us_locale, live=True),
    )

    for language_code in FTL_TARGET_LOCALE_CODES:
        target_locale, _ = Locale.objects.get_or_create(language_code=language_code)
        for page_to_translate in (default_seed_page, root_page, parents.mobile, parents.landing):
            page_to_translate.copy_for_translation(target_locale)

    # The French PDF pages are authored in `fr` and live under the French /features/, which sits in
    # the French tree root rather than the default site's. One locale, so translate it on its own.
    parents.features.copy_for_translation(Locale.objects.get(language_code="fr"))

    return parents


def test_rejects_an_unknown_block_type():
    with pytest.raises(BlockDataError, match="unknown block type 'not_a_real_block'"):
        validate_block_data(FreeFormPage2026, "content", [{"type": "not_a_real_block", "id": "x", "value": {}}])


def test_rejects_an_unknown_struct_field():
    """HeadingBlock has no `level` field — Wagtail would drop it without a word."""
    with pytest.raises(BlockDataError, match="unknown field 'level'"):
        validate_block_data(
            FreeFormPage2026,
            "content",
            [{"type": "intro", "id": "x", "value": {"heading": {"level": "h1", "heading_text": "<p>Hi</p>"}}}],
        )


def test_rejects_an_unknown_field_nested_in_a_button():
    with pytest.raises(BlockDataError, match="unknown field 'action'"):
        validate_block_data(
            FreeFormPage2026,
            "content",
            [
                {
                    "type": "intro",
                    "id": "x",
                    "value": {
                        "content": [
                            {
                                "type": "buttons",
                                "id": "y",
                                "value": [{"type": "uitour_button", "id": "z", "value": {"action": "open_protections_report"}}],
                            }
                        ]
                    },
                }
            ],
        )


# NumberedListBlock (springfield/cms/blocks.py) is a StructBlock whose `list_items` is a
# ListBlock of the StructBlock NumberedListItemBlock, which has only `heading` and `text`.
def test_reports_an_unknown_field_inside_a_list_block_item():
    raw_value = {"list_items": [{"type": "item", "id": "x", "value": {"heading": "<p>Hi</p>", "level": "h1"}}]}

    problems = find_discarded_names(NumberedListBlock(), raw_value, "numbered_list")

    assert len(problems) == 1
    assert "numbered_list.list_items[0]" in problems[0]
    assert "unknown field 'level'" in problems[0]


def test_reports_an_unknown_field_in_a_bare_struct_list_item_that_has_a_type_field():
    """A legacy bare-struct item is not a typed entry just because it has a `type` key."""
    raw_value = {"list_items": [{"type": "whatever", "heading": "<p>Hi</p>"}]}

    problems = find_discarded_names(NumberedListBlock(), raw_value, "numbered_list")

    assert len(problems) == 1
    assert "unknown field 'type'" in problems[0]


def test_accepts_valid_data():
    validate_block_data(
        FreeFormPage2026,
        "content",
        [{"type": "intro", "id": "x", "value": {"heading": {"heading_text": '<p data-block-key="a">Hi</p>'}}}],
    )


UNLABELLED_BUTTON_CONTENT = [
    {
        "type": "intro",
        "id": "x",
        "value": {
            "heading": {"heading_text": '<p data-block-key="a">Hi</p>'},
            "content": [{"type": "buttons", "id": "y", "value": [{"type": "download_button", "id": "z", "value": {"settings": {}}}]}],
        },
    }
]


def get_leaf_messages(error) -> list[str]:
    """Collect the messages from the fields that actually failed.

    Every level of a nested StreamBlock/StructBlock error reports only "Validation error in
    StreamBlock", so asserting on str(error) says nothing about what was wrong with the page.
    """
    block_errors = getattr(error, "block_errors", None)
    if not block_errors:
        return error.messages

    messages = []
    for child_error in block_errors.values():
        for nested_error in child_error if isinstance(child_error, list) else [child_error]:
            messages += get_leaf_messages(nested_error)
    return messages


def test_clean_catches_a_button_with_no_label():
    """LabelSourceMixin.clean() requires a label. full_clean() never reaches it, so an
    unlabelled button saves fine and then blocks the first editor who presses Save."""
    page = FreeFormPage2026(title="probe", slug="probe", content=UNLABELLED_BUTTON_CONTENT)

    with pytest.raises(ValidationError) as raised:
        clean_page_blocks(page, ["upper_content", "content"])

    assert get_leaf_messages(raised.value) == ["Either a pre-translated text or custom text is required."]


def test_clean_passes_a_page_whose_buttons_are_labelled():
    """The positive control for the test above: `clean_page_blocks` must not raise on everything."""
    labelled_button_content = [
        {
            "type": "intro",
            "id": "x",
            "value": {
                "heading": {"heading_text": '<p data-block-key="a">Hi</p>'},
                "content": [
                    {
                        "type": "buttons",
                        "id": "y",
                        "value": [{"type": "download_button", "id": "z", "value": {"custom_label": "Download", "settings": {}}}],
                    }
                ],
            },
        }
    ]
    page = FreeFormPage2026(title="probe", slug="probe", content=labelled_button_content)

    clean_page_blocks(page, ["upper_content", "content"])


def test_scaffold_parents_builds_the_tree(scaffold_parents):
    assert scaffold_parents.mobile.slug == "mobile"
    assert scaffold_parents.landing.slug == "landing"
    assert scaffold_parents.features.slug == "features"
    assert scaffold_parents.mobile.get_parent().pk == scaffold_parents.root_page.pk


def test_scaffold_parents_has_productions_tree_shape(scaffold_parents):
    """Site.root_page sits below a non-routable seed page, as production's does. A shallower tree
    sends wagtail-localize down its root-sibling branch, which production never takes."""
    assert scaffold_parents.root_page.get_parent().is_root() is False
    assert scaffold_parents.mobile.url_path == "/home/firefox-home/mobile/"


def test_scaffold_parents_translates_the_parent_chain(scaffold_parents):
    """Production's /mobile/ already exists in every locale the scaffold pages target."""
    german = Locale.objects.get(language_code="de")

    assert scaffold_parents.mobile.has_translation(german)


# One management command per page, so a migration can call each by name. Tests still name pages by
# slug and this maps them; a slug these tests invent for a monkeypatched spec falls back to the
# focus command, which is the class whose `spec` attribute those tests patch.
COMMAND_FOR_SLUG = {
    "focus": "create_mobile_focus_page",
    "get": "create_landing_get_page",
    "complete-pdf": "create_complete_pdf_page",
    "free-pdf-editor": "create_free_pdf_editor_page",
}


def run_command(pages=None, **options):
    """Tests that are not about translation pass locales=["de"]: the default is all 13 target
    locales, and copying the page into each of them costs seconds per call for no extra coverage."""
    output = StringIO()
    for slug in pages if pages is not None else list(COMMAND_FOR_SLUG):
        call_command(COMMAND_FOR_SLUG.get(slug, "create_mobile_focus_page"), stdout=output, **options)
    return output.getvalue()


def get_focus_page():
    return FreeFormPage2026.objects.get(slug="focus", locale__language_code="en-US")


def test_creates_the_focus_page_under_mobile(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])

    page = get_focus_page()
    assert page.get_parent().pk == scaffold_parents.mobile.pk


def test_page_is_created_as_a_draft(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])

    assert get_focus_page().live is False


def test_page_content_survives_wagtail(scaffold_parents):
    """The point of Task 0: assert what was saved, not merely that saving worked."""
    from springfield.cms.management.commands import create_mobile_focus_page as mobile_focus

    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()

    expected_fields = mobile_focus.build_fields()
    assert len(page.content) == len(expected_fields["content"])
    assert len(page.upper_content) == len(expected_fields["upper_content"])
    for block in page.content:
        if block.block_type != "intro":
            continue
        assert str(block.value["heading"]["heading_text"]).strip(), f"{block.id} lost its heading"


def test_every_stream_block_entry_has_a_unique_id(scaffold_parents):
    """Duplicate ids collapse wagtail-localize segment paths and break translation."""
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()

    ids = [block.id for stream_field in (page.upper_content, page.content) for block in stream_field]
    assert all(ids)
    assert len(ids) == len(set(ids))


def test_rerunning_does_not_duplicate(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    run_command(pages=["focus"], locales=["de"])

    assert FreeFormPage2026.objects.filter(slug="focus", locale__language_code="en-US").count() == 1


def test_existing_page_is_left_alone_without_force(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()
    page.title = "Edited by a human"
    page.save()

    run_command(pages=["focus"], locales=["de"])

    assert get_focus_page().title == "Edited by a human"


def test_force_rewrites_in_place_and_keeps_the_translation_key(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    original = get_focus_page()
    original.title = "Edited by a human"
    original.save()

    run_command(pages=["focus"], locales=["de"], force=True)
    rewritten = get_focus_page()

    assert rewritten.title != "Edited by a human"
    assert rewritten.pk == original.pk
    assert rewritten.translation_key == original.translation_key


def test_refuses_to_touch_a_live_page(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()
    page.live = True
    page.save()

    with pytest.raises(CommandError, match="is live"):
        run_command(pages=["focus"], locales=["de"], force=True)


def test_dry_run_writes_nothing(scaffold_parents):
    run_command(pages=["focus"], locales=["de"], dry_run=True)

    assert not FreeFormPage2026.objects.filter(slug="focus").exists()


def test_every_registered_command_carries_exactly_one_spec():
    """Each command module holds one page's content and its spec; PAGE_COMMAND_NAMES is the only
    list of them. A page added without being registered there is invisible to every test below."""
    from springfield.cms.management.commands._page_scaffold import PAGE_COMMAND_NAMES

    specs = get_page_specs()

    assert len(specs) == len(PAGE_COMMAND_NAMES)
    assert sorted(spec.slug for spec in specs) == sorted(COMMAND_FOR_SLUG)
    assert all(callable(spec.build_fields) for spec in specs)


def test_reported_paths_are_urls_rather_than_tree_paths(scaffold_parents):
    """url_path is the internal tree path — on a production-shaped tree it starts with
    /home/firefox-home/ and pasting it into a browser gives a 404."""
    created = run_command(pages=["focus"], locales=["de"])
    skipped = run_command(pages=["focus"], locales=["de"])

    for output in (created, skipped):
        assert "/en-US/mobile/focus/" in output
        assert "/home/firefox-home/" not in output


def test_block_data_wagtail_would_discard_stops_the_command(scaffold_parents, monkeypatch):
    """`check_fields_before_saving` is the only thing standing between a typo in a content module
    and a page that saves, renders and counts right while missing its content."""
    spec_with_an_unknown_block = replace(
        get_page_specs()[0],
        slug="focus-broken",
        build_fields=lambda: {"content": [{"type": "not_a_real_block", "id": "x", "value": {}}]},
    )
    monkeypatch.setattr(MobileFocusCommand, "spec", spec_with_an_unknown_block)

    with pytest.raises(CommandError, match="not_a_real_block"):
        run_command(pages=["focus-broken"], locales=["de"])


def test_a_missing_parent_page_names_the_slug_chain(scaffold_parents, monkeypatch):
    spec_with_a_missing_parent = replace(get_page_specs()[0], slug="focus-orphan", parent_slugs=("mobile", "nowhere"))
    monkeypatch.setattr(MobileFocusCommand, "spec", spec_with_a_missing_parent)

    with pytest.raises(CommandError, match="mobile/nowhere"):
        run_command(pages=["focus-orphan"], locales=["de"])


def test_create_scaffold_page_rolls_back_a_page_whose_blocks_fail_to_clean(scaffold_parents):
    """Called outside the command there is no outer transaction, so the function has to be atomic
    on its own: add_child() writes the page before clean_page_blocks() rejects it."""
    from springfield.cms.management.commands._page_scaffold import create_scaffold_page

    spec_with_an_unlabelled_button = replace(
        get_page_specs()[0],
        slug="focus-unlabelled",
        build_fields=lambda: {"content": UNLABELLED_BUTTON_CONTENT},
    )

    with pytest.raises(ValidationError):
        create_scaffold_page(spec_with_an_unlabelled_button, force=False)

    assert not FreeFormPage2026.objects.filter(slug="focus-unlabelled").exists()


def test_live_page_without_force_is_skipped_and_other_pages_still_run(scaffold_parents):
    """A live page is reported and left alone, and that is a clean skip rather than an error.

    Each page is its own command now, so what used to be "the rest of the run continues" is "the
    next command still works" — and a non-zero exit from this one would stop a migration dead.
    """
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()
    page.live = True
    page.save()

    output = run_command(pages=["focus"], locales=["de"])

    assert "Live, skipped" in output
    assert "/mobile/focus/" in output

    run_command(pages=["get"], locales=["de"])
    assert FreeFormPage2026.objects.filter(slug="get", live=False).exists()


def test_closing_block_is_full_width_vertical(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])

    settings = list(get_focus_page().content)[-1].value["settings"]
    assert settings["layout"] == "vertical"
    assert settings["full_width"] is True
    assert settings["slim"] is True


def test_imports_a_static_svg():
    from springfield.cms.management.commands._page_scaffold import import_static_image

    image = import_static_image(
        static_path="img/firefox/browsers/mobile/focus/tracking-protection.svg",
        title="Firefox Focus tracking protection illustration",
        is_decorative=True,
    )

    assert image.pk
    assert image.width > 0
    assert image.height > 0


def test_importing_the_same_image_twice_reuses_it():
    from springfield.cms.management.commands._page_scaffold import import_static_image

    first = import_static_image(
        static_path="img/firefox/browsers/mobile/focus/tracking-protection.svg",
        title="Firefox Focus tracking protection illustration",
        is_decorative=True,
    )
    second = import_static_image(
        static_path="img/firefox/browsers/mobile/focus/tracking-protection.svg",
        title="Firefox Focus tracking protection illustration",
        is_decorative=True,
    )

    assert first.pk == second.pk


def test_missing_static_file_raises():
    from springfield.cms.management.commands._page_scaffold import import_static_image

    with pytest.raises(FileNotFoundError, match="no-such-file.svg"):
        import_static_image(static_path="img/no-such-file.svg", title="Does not exist", is_decorative=True)


def test_focus_page_has_its_illustrations(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()

    with_media = [block for block in page.content if len(block.value["media"])]
    assert len(with_media) == 4


def test_focus_page_renders_with_imported_svgs(rf, scaffold_parents):
    """srcset_image applies width-* operations; an SVG Wagtail cannot measure takes the
    whole page render down, not just the image."""
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()

    # page.serve() directly, the way test_pages.py:57 does it: it renders a draft without
    # going through routing, and it returns an already-rendered HttpResponse from
    # l10n_utils.render() — there is no .render() to call on it.
    response = page.serve(rf.get(page.get_full_url()))

    assert "tracking-protection" in response.content.decode()


def test_focus_hero_and_closing_blocks_have_both_store_buttons(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    page = get_focus_page()

    for intro in (page.upper_content[0], list(page.content)[-1]):
        buttons = [block for block in intro.value["content"] if block.block_type == "buttons"]
        assert len(buttons) == 1
        stores = [(button.block_type, button.value["store"]) for button in buttons[0].value]
        assert stores == [("focus_button", "android"), ("focus_button", "ios")]
        assert all(button.value["custom_label"] == "Get Firefox Focus" for button in buttons[0].value)


def test_get_pretranslated_label_returns_the_snippet_pk(db):
    from springfield.cms.management.commands._page_scaffold import get_pretranslated_label
    from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
    from springfield.cms.models import PretranslatedPhrase

    snippet = PretranslatedPhrase.objects.create(
        translation_key=PHRASES["get_firefox"]["translation_key"],
        label="Get Firefox",
        locale=Locale.objects.get(language_code="en-US"),
    )

    assert get_pretranslated_label("get_firefox") == snippet.pk


def test_get_pretranslated_label_resolves_the_english_snippet(db):
    """A button block stores one snippet pk. Once the phrase is translated the key matches a row
    per locale, and an unrestricted .first() can hand the page a German snippet as its source."""
    from springfield.cms.management.commands._page_scaffold import get_pretranslated_label
    from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
    from springfield.cms.models import PretranslatedPhrase

    translation_key = PHRASES["get_firefox"]["translation_key"]
    PretranslatedPhrase.objects.create(
        translation_key=translation_key,
        label="Firefox holen",
        locale=Locale.objects.get_or_create(language_code="de")[0],
    )
    english_snippet = PretranslatedPhrase.objects.create(
        translation_key=translation_key,
        label="Get Firefox",
        locale=Locale.objects.get(language_code="en-US"),
    )

    assert get_pretranslated_label("get_firefox") == english_snippet.pk


def test_get_pretranslated_label_rejects_an_unknown_key():
    from springfield.cms.management.commands._page_scaffold import get_pretranslated_label

    with pytest.raises(CommandError, match="Unknown pretranslated phrase 'nope'"):
        get_pretranslated_label("nope")


def test_get_pretranslated_label_says_when_the_phrase_is_missing(db):
    from springfield.cms.management.commands._page_scaffold import get_pretranslated_label

    with pytest.raises(CommandError, match="create_pretranslated_phrases"):
        get_pretranslated_label("download_firefox")


def test_translates_the_focus_page_into_the_requested_locales(scaffold_parents):
    from wagtail_localize.models import Translation

    run_command(pages=["focus"], locales=["de", "fr"])
    page = get_focus_page()

    translated_locales = set(
        Translation.objects.filter(source__object_id=page.translation_key).values_list("target_locale__language_code", flat=True)
    )
    assert translated_locales == {"de", "fr"}


def test_translated_page_carries_translated_text(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])
    german_page = FreeFormPage2026.objects.get(slug="focus", locale__language_code="de")

    english_page = get_focus_page()
    german_headings = [str(block.value["heading"]["heading_text"]) for block in german_page.content]
    english_headings = [str(block.value["heading"]["heading_text"]) for block in english_page.content]

    assert german_headings != english_headings


def test_translated_pages_are_drafts(scaffold_parents):
    run_command(pages=["focus"], locales=["de"])

    assert FreeFormPage2026.objects.get(slug="focus", locale__language_code="de").live is False


def get_live_page_pks() -> set[int]:
    return set(Page.objects.filter(live=True).values_list("pk", flat=True))


def test_a_full_run_publishes_nothing_anywhere_in_the_tree(scaffold_parents):
    """The headline contract: everything this command writes is a draft, in every locale.

    The tests above each watch one page. The one time this contract broke it broke on pages no
    test was watching — wagtail-localize copied untranslated German ancestors in as aliases, and
    an alias inherits live=True. So this one watches the whole tree, across every spec and every
    locale each spec targets.

    One locale's parent is removed first, deliberately. With every parent in place the run never
    reaches the code that creates aliases, and the assertion would hold no matter what that code
    did. A stage database restored from a partial snapshot has exactly this gap, so the run has to
    translate the other twelve locales and still publish nothing.
    """
    turkish = Locale.objects.get(language_code="tr")
    scaffold_parents.mobile.get_translation(turkish).delete()
    live_page_pks_before = get_live_page_pks()

    output = run_command()

    assert get_live_page_pks() == live_page_pks_before
    # ...and it got there by translating twelve locales, not by skipping all thirteen.
    assert output.count("skipped ") == 1
    assert "skipped tr:" in output
    translated_focus_pages = FreeFormPage2026.objects.filter(slug="focus").exclude(locale__language_code="en-US")
    assert translated_focus_pages.count() == len(FTL_TARGET_LOCALE_CODES) - 1


def test_a_page_going_live_stops_the_run_and_rolls_it_back(scaffold_parents, monkeypatch):
    """The command's own backstop for the contract above. It is deliberately not written against a
    known way of publishing a page: the point is to catch the next one nobody predicted."""
    from springfield.cms.management.commands import _page_scaffold as translations

    def publish_an_ancestor_while_translating(page, spec, locale_codes):
        german_parent = page.get_parent().get_translation(Locale.objects.get(language_code="de"))
        german_parent.live = True
        german_parent.save()
        return translations.TranslationReport(strings_imported=0, locales_translated=(), locales_missing_a_translated_parent=())

    monkeypatch.setattr("springfield.cms.management.commands._page_scaffold.translate_page", publish_an_ancestor_while_translating)
    live_page_pks_before = get_live_page_pks()

    with pytest.raises(CommandError, match="only ever writes drafts, but this run published"):
        run_command(pages=["focus"], locales=["de"])

    assert get_live_page_pks() == live_page_pks_before
    assert not FreeFormPage2026.objects.filter(slug="focus").exists()


def test_skipped_pages_are_not_retranslated(scaffold_parents):
    """A second run must not re-import FTL strings over translations an editor has edited."""
    from wagtail_localize.models import StringTranslation

    run_command(pages=["focus"], locales=["de"])
    translation = StringTranslation.objects.filter(locale__language_code="de").first()
    translation.data = "Von Hand bearbeitet"
    translation.save()

    run_command(pages=["focus"], locales=["de"])

    translation.refresh_from_db()
    assert translation.data == "Von Hand bearbeitet"


def test_force_leaves_hand_corrected_translations_alone(scaffold_parents):
    """--force rewrites the English scaffold. The translations stay attached through the page's
    unchanged translation_key, and re-importing the FTL strings over them would undo an editor's
    corrections — which is the data loss --force exists to avoid, not to cause."""
    from wagtail_localize.models import StringTranslation

    run_command(pages=["focus"], locales=["de"])
    translation = StringTranslation.objects.filter(locale__language_code="de").first()
    translation.data = "Von Hand bearbeitet"
    translation.save()

    run_command(pages=["focus"], locales=["de"], force=True)

    translation.refresh_from_db()
    assert translation.data == "Von Hand bearbeitet"


def test_a_locale_whose_parent_is_untranslated_is_skipped_rather_than_aliased(scaffold_parents):
    """save_target(publish=False) still copies untranslated ancestors in as aliases, and an alias
    inherits live=True from its source. A command that only writes drafts must not publish those."""
    german = Locale.objects.get(language_code="de")
    scaffold_parents.mobile.get_translation(german).delete()

    output = run_command(pages=["focus"], locales=["de"])

    assert not Page.objects.filter(locale=german, alias_of__isnull=False).exists()
    assert not FreeFormPage2026.objects.filter(slug="focus", locale=german).exists()
    assert "skipped de" in output
    assert "/en-US/mobile/" in output


def test_missing_ftl_source_raises_rather_than_importing_nothing():
    from springfield.cms.management.commands._page_scaffold import get_english_strings_for_paths

    with pytest.raises(CommandError, match="no English strings"):
        get_english_strings_for_paths(("firefox/nope/does-not-exist.ftl",))


def test_a_moved_ftl_file_is_reported_even_when_another_path_still_resolves():
    """Checking only the union means one file of several can vanish and the run still reports
    success, with a quietly reduced string set — the silent failure this check exists to prevent."""
    from springfield.cms.management.commands._page_scaffold import get_english_strings_for_paths

    with pytest.raises(CommandError, match="firefox/nope/does-not-exist.ftl"):
        get_english_strings_for_paths(("firefox/browsers/mobile/focus.ftl", "firefox/nope/does-not-exist.ftl"))


def test_unknown_locale_is_rejected(scaffold_parents):
    with pytest.raises(CommandError, match="Not CMS locales"):
        run_command(pages=["focus"], locales=["xx-YY"])


def test_build_po_from_text_pairs_matches_segments_on_their_text(scaffold_parents):
    """The PDF pages in a later task have no FTL message ids, so they match on text alone."""
    from springfield.cms.management.commands._page_scaffold import build_po_from_text_pairs, get_translation_source

    run_command(pages=["focus"], locales=["de"])
    source = get_translation_source(get_focus_page())
    translation = source.translations.create(target_locale=Locale.objects.get_or_create(language_code="fr")[0])

    po = build_po_from_text_pairs(translation, {"Delete your history": "Supprimez votre historique"})

    assert [(entry.msgid, entry.msgstr) for entry in po] == [("Delete your history", "Supprimez votre historique")]
    assert all(entry.msgctxt for entry in po)


def test_without_locales_the_page_spec_decides_which_locales_to_translate(scaffold_parents):
    """Every other test pins --locales, so this is the only cover for the default — and the only
    run that puts the registry's real locale set through the FTL files it names."""
    from wagtail_localize.models import Translation

    focus_spec = next(spec for spec in get_page_specs() if spec.slug == "focus")

    run_command(pages=["focus"])

    translated_locales = set(
        Translation.objects.filter(source__object_id=get_focus_page().translation_key).values_list("target_locale__language_code", flat=True)
    )
    assert translated_locales == set(focus_spec.target_locale_codes)


def test_creates_the_landing_get_page_under_landing(scaffold_parents):
    run_command(pages=["get"], locales=["de"])
    page = FreeFormPage2026.objects.get(slug="get", locale__language_code="en-US")

    assert page.get_parent().pk == scaffold_parents.landing.pk
    assert page.live is False


def test_landing_get_is_noindex_and_marketing_attributed(scaffold_parents):
    run_command(pages=["get"], locales=["de"])
    page = FreeFormPage2026.objects.get(slug="get", locale__language_code="en-US")

    assert page.enable_marketing_attribution is True
    assert page.noindex is True


def test_landing_get_sets_no_page_specific_css_or_js(scaffold_parents):
    run_command(pages=["get"], locales=["de"])
    page = FreeFormPage2026.objects.get(slug="get", locale__language_code="en-US")

    assert page.body_class == ""
    assert page.extra_js == ""


def test_landing_get_keeps_its_protections_report_button(scaffold_parents):
    """The field is button_type, not action. Get it wrong and Wagtail silently
    substitutes the default, which is a 'new tab' button."""
    run_command(pages=["get"], locales=["de"])
    page = FreeFormPage2026.objects.get(slug="get", locale__language_code="en-US")

    button_types = [
        button.value["button_type"]
        for section in page.content
        if section.block_type == "section"
        for panel in section.value["content"]
        if panel.block_type == "media_content"
        for row in panel.value["content"]
        if row.block_type == "buttons"
        for button in row.value
        if button.block_type == "uitour_button"
    ]
    assert "open_protections_report" in button_types


def test_landing_get_download_buttons_use_the_pretranslated_label(scaffold_parents):
    """A custom label would send "Download Firefox" to Smartling again; the snippet is already translated."""
    run_command(pages=["get"], locales=["de"])
    page = FreeFormPage2026.objects.get(slug="get", locale__language_code="en-US")

    hero_buttons = [button for block in page.upper_content[0].value["content"] if block.block_type == "buttons" for button in block.value]
    section_ctas = [button for section in page.content if section.block_type == "section" for button in section.value["cta"]]
    download_buttons = [button for button in hero_buttons + section_ctas if button.block_type == "download_button"]

    assert len(download_buttons) == 3
    assert all(button.value["pretranslated_label"].label == "Download Firefox" for button in download_buttons)


def test_landing_get_carries_its_german_translations(scaffold_parents):
    """The page's whole point is that its FTL translations come with it."""
    run_command(pages=["get"], locales=["de"])
    german_page = FreeFormPage2026.objects.get(slug="get", locale__language_code="de")

    german_headings = [str(block.value["heading"]["heading_text"]) for block in german_page.content if block.block_type == "section"]
    assert german_headings
    assert not any("Make <strong>Firefox</strong> your own" in heading for heading in german_headings)


def test_every_landing_get_string_comes_from_an_ftl_file(scaffold_parents):
    """Translation matches on normalized English text, so any string on the page that is not an FTL
    value — off by a curly apostrophe, a paraphrase, a word invented to fill a required field — is a
    string that goes untranslated in every locale, and nothing else reports it."""
    from wagtail_localize.models import StringSegment

    from springfield.cms.ftl_parser import build_text_to_msgid_mapping, normalize_text_for_matching
    from springfield.cms.management.commands._page_scaffold import get_english_strings_for_paths, get_translation_source

    run_command(pages=["get"], locales=["de"])
    page = FreeFormPage2026.objects.get(slug="get", locale__language_code="en-US")
    spec = next(page_spec for page_spec in get_page_specs() if page_spec.slug == "get")

    ftl_text = build_text_to_msgid_mapping(get_english_strings_for_paths(spec.ftl_relative_paths))
    segments = StringSegment.objects.filter(source=get_translation_source(page)).select_related("string", "context")
    # The page title and the URLs inside link blocks are translatable fields too, and neither is an
    # FTL string: the title is the page's name in the CMS, and a URL is a destination.
    prose = [segment for segment in segments if not segment.context.path.endswith(("title", "link.custom_url", "link.relative_url"))]
    unmatched = [segment.string.data for segment in prose if normalize_text_for_matching(segment.string.data) not in ftl_text]

    assert unmatched == []


def test_every_page_opens_in_the_wagtail_admin_editor(pretranslated_phrases):
    """The admin's rich-text widget is stricter than anything else that touches this data.

    Wagtail's HTML->ContentState parser treats <br> as a paired tag, so a bare one raises
    AssertionError when the edit form renders — the editor gets a 500 on a page that saves, renders
    and passes every other test here. clean_page_blocks() does not catch it: that is the form
    *submit* path, and this is the form *render* path. A draft nobody can open is the one failure
    that costs this command its whole purpose, so walk every authored rich-text value through the
    real widget.
    """
    from wagtail.admin.rich_text import get_rich_text_editor_widget

    widget = get_rich_text_editor_widget("default")

    def rich_text_values(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from rich_text_values(item)
        elif isinstance(value, list):
            for item in value:
                yield from rich_text_values(item)
        elif isinstance(value, str) and "<p" in value:
            yield value

    checked = 0
    for spec in get_page_specs():
        for text in rich_text_values(spec.build_fields()):
            widget.format_value(text)
            checked += 1

    # Without this the test passes by finding nothing to check, which is how it first went green
    # against a page that genuinely broke the editor.
    assert checked > 30, f"only walked {checked} rich-text values — the walk is missing the content"


def get_fr_features_page(scaffold_parents):
    return scaffold_parents.features.get_translations().get(locale__language_code="fr")


def test_pdf_pages_are_created_in_french_under_features(scaffold_parents):
    """These two are authored in `fr`, not translated into it.

    Each locale has its own tree root, so the French pages hang off the French /features/, not the
    one the default site's root page leads to.
    """
    from springfield.cms.models import ArticleDetailPage

    run_command(pages=["complete-pdf", "free-pdf-editor"])

    fr_features = get_fr_features_page(scaffold_parents)
    for slug in ("complete-pdf", "free-pdf-editor"):
        page = ArticleDetailPage.objects.get(slug=slug)
        assert page.locale.language_code == "fr"
        assert page.get_parent().pk == fr_features.pk
        assert page.live is False


def test_pdf_pages_have_no_english_version(scaffold_parents):
    """The English page the old design needed was a liability: nothing on it was real copy, and
    publishing it would have turned the /en-US/ -> /fr/ redirect into an indexable English page."""
    from springfield.cms.models import ArticleDetailPage

    run_command(pages=["complete-pdf", "free-pdf-editor"])

    assert not ArticleDetailPage.objects.filter(slug__in=("complete-pdf", "free-pdf-editor"), locale__language_code="en-US").exists()


def test_pdf_pages_are_not_translated_anywhere(scaffold_parents):
    from wagtail_localize.models import Translation

    from springfield.cms.models import ArticleDetailPage

    run_command(pages=["complete-pdf", "free-pdf-editor"])

    for slug in ("complete-pdf", "free-pdf-editor"):
        page = ArticleDetailPage.objects.get(slug=slug)
        assert not Translation.objects.filter(source__object_id=page.translation_key).exists()


def test_pdf_page_text_is_the_template_french_verbatim(scaffold_parents):
    from springfield.cms.models import ArticleDetailPage

    run_command(pages=["complete-pdf", "free-pdf-editor"])

    complete = "".join(str(block.value) for block in ArticleDetailPage.objects.get(slug="complete-pdf").content)
    free = "".join(str(block.value) for block in ArticleDetailPage.objects.get(slug="free-pdf-editor").content)

    assert "Fini les soucis liés à la paperasse" in complete
    assert "DÉCLARATION RECTIFICATIVE, ANNULE ET REMPLACE" in complete
    assert "Cerfa 13750*07" in free
    assert "Ne laissez plus la complexité des formulaires administratifs vous stresser." in free


def test_output_warns_that_publishing_goes_live_immediately(scaffold_parents):
    """All four routes already carry prefer_cms, so there is no second switch between a published
    CMS page and the public seeing it."""
    output = run_command(pages=["focus"], locales=["de"])

    assert "prefer_cms" in output
    assert "publishing one serves it to the public immediately" in output


def test_output_lists_what_an_editor_still_has_to_do(scaffold_parents):
    output = run_command(pages=["complete-pdf"])

    assert "An editor still needs to:" in output
    assert "hide-from-firefox" in output
    assert "alt text" in output


def test_every_spec_with_known_losses_carries_editor_notes():
    """A fidelity loss recorded only in a module docstring reaches nobody who opens the admin."""
    specs = {spec.slug: spec for spec in get_page_specs()}

    for slug in ("get", "complete-pdf", "free-pdf-editor"):
        assert specs[slug].editor_notes, f"{slug} has known losses but no editor notes"
