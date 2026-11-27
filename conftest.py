# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Lets a test run start from an already-migrated database. Migrating an empty test database takes
# over a minute, and under pytest-xdist every worker does it. When TEST_DB_TEMPLATE names a SQLite
# file built by bin/build-test-db-template.py, each process copies it into the in-memory test
# database before pytest-django sets that database up, so Django's `migrate` finds nothing to
# apply. Without TEST_DB_TEMPLATE, nothing changes.

import os
import sqlite3

import pytest

# The in-memory test database Django creates for the "default" alias. With shared cache, every
# connection in the process that opens this name sees the same database.
IN_MEMORY_TEST_DB = "file:memorydb_default?mode=memory&cache=shared"

# The in-memory database exists only while a connection to it is open, so hold one for the session.
_template_connection = None


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings_parallel_suffix):
    global _template_connection

    template = os.environ.get("TEST_DB_TEMPLATE")
    if not template or not os.path.exists(template):
        return

    from django.conf import settings

    database = settings.DATABASES["default"]
    if database["ENGINE"] != "django.db.backends.sqlite3" or database.get("TEST", {}).get("NAME"):
        return

    source = sqlite3.connect(template)
    _template_connection = sqlite3.connect(IN_MEMORY_TEST_DB, uri=True)
    source.backup(_template_connection)
    source.close()
