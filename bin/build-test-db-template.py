#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Migrate a SQLite file the way pytest-django builds the test database, for TEST_DB_TEMPLATE.

The root conftest.py copies this file into each test process's in-memory database, so the suite
skips migrating from scratch. It runs under the test settings, as a test run does: importing pytest
first switches on the test-only block in springfield/settings/__init__.py.
"""

import os
import sys
from pathlib import Path

import pytest  # noqa: F401  (switches on the test settings; see the docstring)

# Run as `python bin/...`, so the repo root isn't on the import path the way it is for manage.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(path):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "springfield.settings.test")
    tmp_path = f"{path}.tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    import django

    django.setup()

    from django.core.management import call_command
    from django.db import connections

    # The same steps Django's create_test_db() runs, against a file instead of memory.
    connection = connections["default"]
    connection.close()
    connection.settings_dict["NAME"] = tmp_path
    call_command("migrate", verbosity=0, interactive=False, run_syncdb=True)
    call_command("createcachetable", verbosity=0)
    connection.close()

    # Only a complete template replaces the old one, so a failed build never leaves a partial file.
    os.replace(tmp_path, path)


if __name__ == "__main__":
    main(sys.argv[1])
