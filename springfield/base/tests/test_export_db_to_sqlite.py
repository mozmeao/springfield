# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from wagtail.models import get_page_models


def test_every_page_model_is_included_in_the_db_export():
    export_script = (settings.ROOT_PATH / "bin" / "export-db-to-sqlite.sh").read_text()
    script_lines = {line.strip().removesuffix("\\").strip() for line in export_script.splitlines()}

    missing_page_models = [model._meta.label for model in get_page_models() if model._meta.label not in script_lines]

    assert missing_page_models == []
