# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail_localize.fields import SynchronizedField

from springfield.cms.models import SimpleRichTextPage
from springfield.cms.models.pages import FreeFormPage2026, StructuralPage, WhatsNewPage2026


@pytest.mark.django_db
def test_get_admin_display_title_uses_internal_title_when_set(minimal_site):
    root_page = minimal_site.root_page
    page = SimpleRichTextPage(slug="internal-set", title="Public Title", internal_title="Internal Label")
    root_page.add_child(instance=page)

    assert page.get_admin_display_title() == "Internal Label"


@pytest.mark.django_db
def test_get_admin_display_title_falls_back_to_title_when_blank(minimal_site):
    root_page = minimal_site.root_page
    page = SimpleRichTextPage(slug="internal-blank", title="Public Title")
    root_page.add_child(instance=page)

    assert page.internal_title == ""
    assert page.get_admin_display_title() == "Public Title"


@pytest.mark.django_db
def test_admin_display_reflects_current_title_when_unlabeled(minimal_site):
    root_page = minimal_site.root_page
    page = SimpleRichTextPage(slug="fresh", title="Original Title")
    root_page.add_child(instance=page)

    # An unlabeled page tracks its live public title, so renames show immediately.
    page.title = "Renamed Title"
    rev = page.save_revision()
    rev.publish()
    page.refresh_from_db()

    assert page.internal_title == ""
    assert page.get_admin_display_title() == "Renamed Title"


@pytest.mark.django_db
def test_internal_title_does_not_leak_to_the_public(minimal_site, rf):
    root_page = minimal_site.root_page
    page = SimpleRichTextPage(
        slug="no-leak",
        title="Public Rendering Title",
        internal_title="SECRET-INTERNAL-LABEL-XYZ",
    )
    root_page.add_child(instance=page)

    response = page.serve(rf.get(page.get_full_url()))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    # The internal label is never rendered to visitors...
    assert "SECRET-INTERNAL-LABEL-XYZ" not in content
    # ...while the public title still drives the visible page.
    assert "Public Rendering Title" in content


@pytest.mark.parametrize(
    "page_class",
    [SimpleRichTextPage, FreeFormPage2026, WhatsNewPage2026, StructuralPage],
)
def test_internal_title_is_a_synchronized_translatable_field(page_class):
    """internal_title is copied across locales (synchronized), not sent for translation."""
    by_name = {f.field_name: f for f in page_class.override_translatable_fields}
    assert "internal_title" in by_name
    assert isinstance(by_name["internal_title"], SynchronizedField)
