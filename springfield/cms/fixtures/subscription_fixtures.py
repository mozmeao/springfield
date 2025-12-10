# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_test_index_page
from springfield.cms.models import FreeFormPage


def get_subscription_variants() -> list[dict]:
    return [
        {
            "type": "subscription",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="3yuor">Subscribe to newsletter</p>',
                    "heading_text": '<p data-block-key="9my2x">Subscription block</p>',
                    "subheading_text": '<p data-block-key="qsml9">The Subscription block only needs a heading. '
                    "The form will be rendered automatically.</p>",
                }
            },
            "id": "f24b5d7d-5cba-4202-9c30-9a2ee8e9dada",
        }
    ]


def get_subscription_test_page():
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-subscription-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-subscription-page",
            title="Test Subscription Page",
        )
        index_page.add_child(instance=page)

    page.content = get_subscription_variants()
    page.save_revision().publish()
    return page
