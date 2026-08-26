# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse

import pytest
from pytest_django.asserts import assertInHTML
from wagtail.models import Locale
from wagtail_localize.models import SegmentOverride, StringSegment, StringTranslation, Translation, TranslationSource

pytestmark = pytest.mark.django_db


@pytest.fixture
def get_edit_page_html(admin_client):

    def _get_edit_page_html(page):
        url = reverse("wagtailadmin_pages:edit", args=[page.id])

        response = admin_client.get(url)

        assert response.status_code == 200
        return response.content.decode()

    return _get_edit_page_html


@pytest.fixture
def assert_button_in_page(get_edit_page_html):

    def _assert_button_in_page(page, translation):
        create_share_url = reverse("cms_translation_draftsharing_create", args=[translation.pk])
        expected_button_html = f"""
        <template id="translation-draftsharing-button">
            <button type="button"
                    class="button"
                    data-translation-draftsharing
                    data-url="{create_share_url}">
                <svg class="icon icon-view icon" aria-hidden="true">
                    <use href="#icon-view"></use>
                </svg>
                Create draft sharing link
            </button>
        </template>
        """

        page_html = get_edit_page_html(page)

        assertInHTML(expected_button_html, page_html)

    return _assert_button_in_page


@pytest.fixture
def assert_button_not_in_page(get_edit_page_html):

    def _assert_button_not_in_page(page):
        page_html = get_edit_page_html(page)

        assert "translation-draftsharing-button" not in page_html

    return _assert_button_not_in_page


def test_shown_when_a_translation_edit_is_unpublished(assert_button_in_page, translated_page_with_pending_edit):
    assert_button_in_page(translated_page_with_pending_edit.page, translated_page_with_pending_edit.translation)


def test_shown_when_the_page_is_not_live(assert_button_in_page, translated_page):
    translated_page.page.live = False
    translated_page.page.save(update_fields=["live"])

    assert_button_in_page(translated_page.page, translated_page.translation)


def test_shown_when_live_but_never_published(assert_button_in_page, translated_page):
    """Imported content can be live with no last_published_at; treat it as shareable."""
    translated_page.page.last_published_at = None
    translated_page.page.save(update_fields=["last_published_at"])

    assert_button_in_page(translated_page.page, translated_page.translation)


def test_shown_when_a_segment_override_is_pending(assert_button_in_page, translated_page):
    segment = StringSegment.objects.filter(source=translated_page.translation.source).first()
    SegmentOverride.objects.create(
        locale=translated_page.locale,
        context=segment.context,
        data_json='"overridden"',
        has_error=False,
    )

    assert_button_in_page(translated_page.page, translated_page.translation)


def test_shown_when_source_page_has_changed(assert_button_in_page, translated_page):
    source_page = translated_page.source_page
    source_page.title += "!"
    source_page.save()
    TranslationSource.update_or_create_from_instance(source_page)

    assert_button_in_page(translated_page.page, translated_page.translation)


def test_hidden_when_nothing_has_changed_since_publication(assert_button_not_in_page, translated_page):
    assert_button_not_in_page(translated_page.page)


def test_hidden_when_the_only_pending_edit_has_an_error(assert_button_not_in_page, translated_page_with_pending_edit):
    StringTranslation.objects.filter(locale=translated_page_with_pending_edit.locale).update(has_error=True)

    assert_button_not_in_page(translated_page_with_pending_edit.page)


def test_button_not_rendered_in_translated_snippet_editor(admin_client, pretranslated_phrase_snippet):
    """edit_translation.html is shared with snippets, which have no page to share."""
    # Create a translatable snippet with an enabled Translation for the snippet editor path
    locale = Locale.objects.create(language_code="fr")
    # Use copy_for_translation rather than save_target which depends on on_commit behaviour
    translated_snippet = pretranslated_phrase_snippet.copy_for_translation(locale)
    translated_snippet.save()
    source, __ = TranslationSource.get_or_create_from_instance(pretranslated_phrase_snippet)
    Translation.objects.create(source=source, target_locale=locale, enabled=True)

    url = reverse("wagtailsnippets_cms_pretranslatedphrase:edit", args=[translated_snippet.pk])

    response = admin_client.get(url)

    assert response.status_code == 200
    page_html = response.content.decode()
    assert "translation-draftsharing-button" not in page_html
