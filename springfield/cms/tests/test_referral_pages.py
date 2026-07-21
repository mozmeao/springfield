# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.models import Site

from springfield.cms.tests.factories import ReferralHubPageFactory

pytestmark = [pytest.mark.django_db]


def test_hub_page_get_context_includes_invite_url(rf):
    site = Site.objects.get(is_default_site=True)
    hub_page = ReferralHubPageFactory(parent=site.root_page)

    context = hub_page.get_context(rf.get("/"))

    assert "invite_url" in context
    assert context["invite_url"] == "https://example.com/invite-link-still-to-come"
