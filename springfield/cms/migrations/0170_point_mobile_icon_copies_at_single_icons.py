# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration pointing icons stored under a mobile-24 copy's path value (e.g.
# "mobile-24-add-add-24") at the one remaining file for that icon ("add"), since
# each icon now ships a single SVG. Without it those icons would render blank and
# fail validation the next time an editor saves the page.

import json
import re

from django.db import migrations
from django.db.models import JSONField, TextField, Value
from django.db.models.functions import Cast

from wagtail.fields import StreamField

OLD_TO_NEW_ICON = {
    "mobile-24-add-add-24": "add",
    "mobile-24-alerts-info-help-critical-fill-24": "critical-fill",
    "mobile-24-alerts-info-help-information-24": "information",
    "mobile-24-alerts-info-help-information-fill-24": "information-fill",
    "mobile-24-alerts-info-help-warning-24": "warning",
    "mobile-24-alerts-info-help-warning-fill-24": "warning-fill",
    "mobile-24-app-menu-more-options-app-menu-space-24": "app-menu-space",
    "mobile-24-arrows-chevrons-arrow-clockwise-24": "arrow-clockwise",
    "mobile-24-arrows-chevrons-arrow-trending-24": "arrow-trending",
    "mobile-24-arrows-chevrons-back-24": "back",
    "mobile-24-arrows-chevrons-chevron-down-24": "chevron-down",
    "mobile-24-arrows-chevrons-chevron-left-24": "chevron-left",
    "mobile-24-arrows-chevrons-chevron-right-24": "chevron-right",
    "mobile-24-arrows-chevrons-chevron-up-24": "chevron-up",
    "mobile-24-arrows-chevrons-forward-24": "forward",
    "mobile-24-bookmark-bookmark-24": "bookmark",
    "mobile-24-bookmark-bookmark-fill-24": "bookmark-fill",
    "mobile-24-checkmark-checkmark-24": "checkmark",
    "mobile-24-data-clearance-data-clearance-24": "data-clearance",
    "mobile-24-delete-delete-24": "delete",
    "mobile-24-devices-device-mobile-24": "device-mobile",
    "mobile-24-edit-copy-paste-signature-properties-24": "signature-properties",
    "mobile-24-experiments-experiments-24": "experiments",
    "mobile-24-extensions-extension-critical-24": "extension-critical",
    "mobile-24-extensions-extension-fill-24": "extension-fill",
    "mobile-24-extensions-extension-warning-24": "extension-warning",
    "mobile-24-external-link-external-link-24": "external-link",
    "mobile-24-globe-globe-24": "globe",
    "mobile-24-history-history-24": "history",
    "mobile-24-home-home-24": "home",
    "mobile-24-lightbulb-lightbulb-24": "lightbulb",
    "mobile-24-lock-lock-24": "lock",
    "mobile-24-lock-lock-warning-24": "lock-warning",
    "mobile-24-mail-email-shield-24": "email-shield",
    "mobile-24-passkey-passkey-24": "passkey",
    "mobile-24-permissions-login-24": "login",
    "mobile-24-pin-pin-24": "pin",
    "mobile-24-pin-pin-fill-24": "pin-fill",
    "mobile-24-print-print-24": "print",
    "mobile-24-private-mode-private-mode-circle-fill-24": "private-mode-circle-fill",
    "mobile-24-search-find-in-page-24": "find-in-page",
    "mobile-24-search-search-24": "search",
    "mobile-24-shield-shield-24": "shield",
    "mobile-24-shopping-packaging-24": "packaging",
    "mobile-24-shopping-price-24": "price",
    "mobile-24-shopping-quality-24": "quality",
    "mobile-24-shopping-shipping-24": "shipping",
    "mobile-24-shopping-shopping-24": "shopping",
    "mobile-24-sort-sort-24": "sort",
    "mobile-24-subtract-subtract-24": "subtract",
    "mobile-24-sync-sync-24": "sync",
    "mobile-24-tabs-tab-24": "tab",
    "mobile-24-themes-themes-24": "themes",
    "mobile-24-translate-translate-24": "translate",
}
OLD_ICON_PATTERN = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, OLD_TO_NEW_ICON)) + r")(?![\w-])")


def replace_icons(text):
    return OLD_ICON_PATTERN.sub(lambda match: OLD_TO_NEW_ICON[match.group()], text)


def migrate_stream_fields(apps):
    """Rewrite the stored JSON text directly: loading it as a StreamValue would drop
    blocks the current definitions no longer declare."""
    for model in [*apps.get_app_config("cms").get_models(), *apps.get_app_config("blog").get_models()]:
        for field in model._meta.local_concrete_fields:
            if not isinstance(field, StreamField):
                continue
            rows = model.objects.annotate(stored=Cast(field.name, TextField())).values_list("pk", "stored")
            for pk, stored in rows.iterator():
                replaced = replace_icons(stored or "")
                if replaced != (stored or ""):
                    model.objects.filter(pk=pk).update(**{field.name: Value(json.loads(replaced), output_field=JSONField())})


def migrate_revisions(apps):
    """Rewrite drafts too, or publishing one would bring the old value back."""
    Revision = apps.get_model("wagtailcore", "Revision")
    for revision in Revision.objects.all().iterator():
        stored = json.dumps(revision.content)
        replaced = replace_icons(stored)
        if replaced != stored:
            Revision.objects.filter(pk=revision.pk).update(content=json.loads(replaced))


def forwards(apps, schema_editor):
    migrate_stream_fields(apps)
    migrate_revisions(apps)
    ArticleDetailPage = apps.get_model("cms", "ArticleDetailPage")
    for old_icon, new_icon in OLD_TO_NEW_ICON.items():
        ArticleDetailPage.objects.filter(icon=old_icon).update(icon=new_icon)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0169_freeformpage2026_marketing_attribution_mode_and_more"),
        ("blog", "0006_blogarticlepage_image_alt_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
