# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Page
from wagtail.users.models import UserProfile

from springfield.cms.tests.factories import LocaleFactory

pytestmark = [pytest.mark.django_db]

User = get_user_model()


@override_settings(
    # The project is SSO-only by default; enable conventional auth so the test
    # client can log in (mirrors springfield/cms/tests/test_auth.py).
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
    USE_SSO_AUTH=False,
    WAGTAIL_ENABLE_ADMIN=True,
    FALLBACK_LOCALES={"pt-PT": "pt-BR"},
)
def test_published_badge_for_pt_br_page_points_to_pt_br_for_pt_pt_editor(client, tiny_localized_site):
    """
    If a user with a preferred pt-pt locale edits a pt-BR page, page's "PUBLISHED" badge should be the pt-BR URL.
    """
    LocaleFactory(language_code="pt-PT")
    pt_br_page = Page.objects.get(locale__language_code="pt-BR", slug="child-page")

    editor = User.objects.create_superuser(username="editor", email="editor@example.com", password="admin12345")
    profile = UserProfile.get_for_user(editor)
    profile.preferred_language = "pt-pt"  # Wagtail's Portuguese (Portugal) admin language
    profile.save()
    client.force_login(editor)

    response = client.get(f"/{settings.WAGTAIL_ADMIN_URL_PREFIX}/pages/{pt_br_page.id}/edit/")

    assert response.status_code == 200

    # Scope the assertion to the PUBLISHED badge anchor itself (rendered by
    # page_status_tag_new.html with class "page-status-tag"), so an unrelated
    # widget elsewhere on the edit page can't make this pass or fail spuriously.
    soup = BeautifulSoup(response.content, "html.parser")
    badge_hrefs = {a.get("href") for a in soup.select("a.page-status-tag")}
    assert badge_hrefs, "expected the PUBLISHED badge anchor in the edit header"
    # The badge links to the page's own canonical pt-BR URL, never the
    # editor-UI-language pt-PT URL (the bug).
    assert badge_hrefs == {"/pt-BR/test-page/child-page/"}
