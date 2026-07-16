# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.models import FreeFormPage2026


def get_enterprise_download() -> dict:
    return {
        "type": "enterprise_download",
        "value": None,
        "id": "ed000001-0000-0000-0000-000000000001",
    }


def get_enterprise_download_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-enterprise-download-page",
        parent=index_page,
        defaults={
            "title": "Enterprise Download",
        },
    )

    page.upper_content = [get_enterprise_download()]
    page.content = [get_enterprise_download()]
    page.save_revision().publish()
    return page
