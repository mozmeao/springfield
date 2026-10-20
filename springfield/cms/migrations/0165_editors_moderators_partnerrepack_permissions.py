# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def add_group_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="cms", model="partnerrepack")

    codenames = [
        ("add_partnerrepack", "Can add Partner download"),
        ("change_partnerrepack", "Can change Partner download"),
        ("delete_partnerrepack", "Can delete Partner download"),
        ("publish_partnerrepack", "Can publish Partner download"),
    ]

    permissions = []
    for codename, name in codenames:
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions.append(permission)

    for group_name in ("Editors", "Moderators"):
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        group.permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0164_partnerrepack"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(add_group_permissions, migrations.RunPython.noop),
    ]
