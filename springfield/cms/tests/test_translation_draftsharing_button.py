# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse

import pytest
from pytest_django.asserts import assertInHTML
from wagtail.models import Locale
from wagtail_localize.models import Translation, TranslationSource

pytestmark = pytest.mark.django_db


def test_shown_in_translation_edit_view(admin_client, translated_page):
    create_share_url = reverse("cms_translation_draftsharing_create", args=[translated_page.translation.pk])
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
    edit_url = reverse("wagtailadmin_pages:edit", args=[translated_page.page.id])

    response = admin_client.get(edit_url)

    assert response.status_code == 200
    page_html = response.content.decode()
    assertInHTML(expected_button_html, page_html)


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
