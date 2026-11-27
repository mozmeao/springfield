# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wagtail_factories
from wagtail.models import Site

from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory


def create_minimal_site(hostname):
    """A default site with a root page at / and one child page at /test-page/, plus a French locale."""
    top_level_page = SimpleRichTextPageFactory(
        slug="root_page",  # this doesn't get shown
        live=True,
    )

    try:
        site = Site.objects.get(is_default_site=True)
        site.root_page = top_level_page
        site.hostname = hostname
        site.save()
    except Site.DoesNotExist:
        site = wagtail_factories.SiteFactory(
            root_page=top_level_page,
            is_default_site=True,
            hostname=hostname,
        )

    LocaleFactory(language_code="fr")

    SimpleRichTextPageFactory(
        slug="test-page",
        parent=top_level_page,
        title="Test Page",
    )

    return site
