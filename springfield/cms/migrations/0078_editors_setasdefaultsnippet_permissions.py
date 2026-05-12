# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def add_editor_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    try:
        editors = Group.objects.get(name="Editors")
    except Group.DoesNotExist:
        return

    try:
        ct = ContentType.objects.get(app_label="cms", model="setasdefaultsnippet")
    except ContentType.DoesNotExist:
        return

    codenames = [
        ("add_setasdefaultsnippet", "Can add Set as Default Snippet"),
        ("change_setasdefaultsnippet", "Can change Set as Default Snippet"),
        ("delete_setasdefaultsnippet", "Can delete Set as Default Snippet"),
        ("publish_setasdefaultsnippet", "Can publish Set as Default Snippet"),
    ]

    permissions = []
    for codename, name in codenames:
        perm, _ = Permission.objects.get_or_create(
            content_type=ct,
            codename=codename,
            defaults={"name": name},
        )
        permissions.append(perm)

    editors.permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0077_setasdefaultsnippet"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(add_editor_permissions, migrations.RunPython.noop),
    ]
