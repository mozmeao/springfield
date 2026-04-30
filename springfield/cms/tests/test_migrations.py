# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import apps as django_apps
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.models import CreateModel

import pytest


@pytest.mark.django_db
def test_no_abstract_class_refs_in_migration_bases():
    """
    Ensure no CreateModel migration uses a live Python class reference to an
    abstract model in its bases= tuple.

    When an abstract mixin is referenced directly (e.g.
    bases=(some.module.SomeMixin, "wagtailcore.page")), Django resolves the
    live class at migration replay time. Any fields added to the mixin after
    the migration was written are silently included in the CREATE TABLE SQL,
    causing DuplicateColumn errors when a later AddField migration tries to
    add those same columns on a fresh database.

    The safe pattern is to use string references for concrete parents
    (e.g. "wagtailcore.page") and rely on explicit AddField operations to
    track abstract mixin field additions.
    """
    # Only check our own apps (identified by module path), not third-party ones.
    our_app_labels = {config.label for config in django_apps.get_app_configs() if config.module.__name__.startswith("springfield")}

    loader = MigrationLoader(None, ignore_no_migrations=True)
    violations = []

    for (app_label, migration_name), migration in loader.disk_migrations.items():
        if app_label not in our_app_labels:
            continue
        for operation in migration.operations:
            if not isinstance(operation, CreateModel):
                continue
            for base in operation.bases:
                if isinstance(base, str):
                    continue  # safe: string refs resolve against migration state
                if getattr(getattr(base, "_meta", None), "abstract", False):
                    violations.append(
                        f"{app_label}.{migration_name}: "
                        f"CreateModel '{operation.name}' has abstract class "
                        f"{base.__module__}.{base.__qualname__} in bases="
                    )

    assert not violations, (
        "The following migrations reference live abstract Python classes in "
        "bases=. Replace them with string references or remove them — "
        "abstract mixin fields should be tracked via explicit AddField "
        "operations instead:\n\n" + "\n".join(violations)
    )
