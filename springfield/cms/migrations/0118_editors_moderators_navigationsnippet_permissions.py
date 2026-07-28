# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def add_group_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    try:
        ct = ContentType.objects.get(app_label="cms", model="navigationsnippet")
    except ContentType.DoesNotExist:
        return

    codenames = [
        ("add_navigationsnippet", "Can add Navigation Snippet"),
        ("change_navigationsnippet", "Can change Navigation Snippet"),
        ("delete_navigationsnippet", "Can delete Navigation Snippet"),
        ("publish_navigationsnippet", "Can publish Navigation Snippet"),
    ]

    permissions = []
    for codename, name in codenames:
        perm, _ = Permission.objects.get_or_create(
            content_type=ct,
            codename=codename,
            defaults={"name": name},
        )
        permissions.append(perm)

    for group_name in ("Editors", "Moderators"):
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        group.permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0117_articledetailpage_custom_navigation_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(add_group_permissions, migrations.RunPython.noop),
    ]
