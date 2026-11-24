# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace

from django.utils import translation

import pytest
from wagtail_localize.models import Translation, TranslationSource

from springfield.cms.fixtures.snippet_fixtures import get_banner_snippet
from springfield.cms.models import SyncedBlockSnippet
from springfield.cms.tests.test_synced_blocks.conftest import get_locale, main_content_html, section_item, synced_block_item

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def builders(freeform_page_factory, synced_block_factory, synced_block_translation_factory):
    return SimpleNamespace(page=freeform_page_factory, synced_block=synced_block_factory, translate=synced_block_translation_factory)


def english_synced_block(builders):
    return builders.synced_block(section_item("English heading"))


def page_for(builders, snippet, language_code):
    """A page in ``language_code`` holding ``snippet``, with the language it is served in."""
    return builders.page(content=[synced_block_item(snippet)], locale=get_locale(language_code)), language_code


def es_ar_alias_page_for(builders, snippet):
    """The es-MX page served in the es-AR alias locale, which falls back to es-MX."""
    get_locale("es-AR")
    page, _ = page_for(builders, snippet, "es-MX")
    return page, "es-AR"


def french_page_with_french_translation(builders):
    french = builders.translate(english_synced_block(builders), get_locale("fr"), section_item("French heading"))
    return page_for(builders, french, "fr")


def es_ar_page_with_es_mx_translation(builders):
    mexican_spanish = builders.translate(english_synced_block(builders), get_locale("es-MX"), section_item("Mexican Spanish heading"))
    return es_ar_alias_page_for(builders, mexican_spanish)


def french_page_with_french_translation_and_unpublished_english(builders):
    english = english_synced_block(builders)
    french = builders.translate(english, get_locale("fr"), section_item("French heading"))
    english.unpublish()
    return page_for(builders, french, "fr")


def es_ar_page_with_unpublished_es_ar_and_published_es_mx_translations(builders):
    english = english_synced_block(builders)
    mexican_spanish = builders.translate(english, get_locale("es-MX"), section_item("Mexican Spanish heading"))
    builders.translate(english, get_locale("es-AR"), section_item("Argentinian Spanish heading"), publish=False)
    return es_ar_alias_page_for(builders, mexican_spanish)


def french_page_referencing_english(builders):
    return page_for(builders, english_synced_block(builders), "fr")


def french_page_with_unpublished_french_translation(builders):
    french = builders.translate(english_synced_block(builders), get_locale("fr"), section_item("French heading"), publish=False)
    return page_for(builders, french, "fr")


def es_ar_page_without_es_mx_translation(builders):
    return es_ar_alias_page_for(builders, english_synced_block(builders))


def es_ar_page_with_unpublished_es_mx_translation(builders):
    mexican_spanish = builders.translate(english_synced_block(builders), get_locale("es-MX"), section_item("Mexican Spanish heading"), publish=False)
    return es_ar_alias_page_for(builders, mexican_spanish)


@pytest.mark.parametrize(
    "build_page, expected_heading",
    [
        pytest.param(french_page_with_french_translation, "French heading", id="page_locale"),
        pytest.param(es_ar_page_with_es_mx_translation, "Mexican Spanish heading", id="fallback_locale"),
        pytest.param(french_page_with_french_translation_and_unpublished_english, "French heading", id="page_locale_published_english_unpublished"),
        pytest.param(
            es_ar_page_with_unpublished_es_ar_and_published_es_mx_translations,
            "Mexican Spanish heading",
            id="fallback_published_page_locale_unpublished",
        ),
        pytest.param(french_page_referencing_english, "English heading", id="english_no_translation"),
        pytest.param(french_page_with_unpublished_french_translation, "English heading", id="english_translation_unpublished"),
        pytest.param(es_ar_page_without_es_mx_translation, "English heading", id="english_fallback_locale_has_no_translation"),
        pytest.param(es_ar_page_with_unpublished_es_mx_translation, "English heading", id="english_fallback_locale_translation_unpublished"),
    ],
)
def test_synced_block_renders_published_translation_or_english(build_page, builders, expected_heading, rf):
    page, language_code = build_page(builders)
    # Translated test pages sit under the English site root, so a client request would not switch locale.
    with translation.override(language_code):
        response = page.serve(rf.get(page.get_full_url()))

    assert response.status_code == 200
    assert expected_heading in main_content_html(response)


def test_banner_snippet_has_no_localized_version_without_translation(index_page):
    banner = get_banner_snippet()
    banner.save_revision().publish()

    with translation.override("fr"):
        assert banner.get_localized() is None


def test_translating_page_keeps_synced_block_on_default_locale_snippet(builders):
    snippet = english_synced_block(builders)
    page = builders.page(content=[synced_block_item(snippet)])
    french = get_locale("fr")
    page.get_parent().specific.copy_for_translation(french, copy_parents=True).save_revision().publish()

    source, _ = TranslationSource.get_or_create_from_instance(page)
    Translation.objects.create(source=source, target_locale=french, enabled=True).save_target(publish=True)

    french_page = page.get_translation(french)
    assert french_page.content[0].value == snippet
    assert not SyncedBlockSnippet.objects.filter(locale=french).exists()
