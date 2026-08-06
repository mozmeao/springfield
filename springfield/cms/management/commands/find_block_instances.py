# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Find all instances of a given block class across every page's StreamFields.

Recursively walks each page's StreamField content (including nested StructBlock,
ListBlock, and StreamBlock children) looking for a block whose class matches the
given name. Block classes created by factory functions (e.g. TwoColumnCardsBlock
in springfield/cms/blocks.py) are defined with a leading underscore
(_TwoColumnCardsBlock), so the match strips leading underscores before comparing.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse

from wagtail import blocks
from wagtail.fields import StreamField
from wagtail.models import Page, Site


def walk_blocks(block, value):
    """Recursively yield (block, value) pairs for a block definition and its stored value."""
    yield block, value
    if isinstance(block, blocks.StreamBlock):
        for child in value:
            yield from walk_blocks(child.block, child.value)
    elif isinstance(block, blocks.StructBlock):
        for name, sub_block in block.child_blocks.items():
            yield from walk_blocks(sub_block, value[name])
    elif isinstance(block, blocks.ListBlock):
        for item in value:
            yield from walk_blocks(block.child_block, item)


def admin_base_url():
    """Base URL to prefix admin-only paths with, so they're clickable outside a request."""
    if settings.WAGTAILADMIN_BASE_URL:
        return settings.WAGTAILADMIN_BASE_URL
    site = Site.objects.filter(is_default_site=True).first()
    return site.root_url if site else ""


def page_url(page):
    """Front-end URL for live pages; admin draft-preview URL for pages that aren't live yet."""
    if page.live:
        return page.get_full_url()
    return admin_base_url() + reverse("wagtailadmin_pages:view_draft", args=[page.pk])


def find_block_instances(class_name):
    """Return (page, field_name, value) tuples for every instance of class_name found."""
    matches = []
    for page in Page.objects.specific():
        for field in page._meta.get_fields():
            if not isinstance(field, StreamField):
                continue
            stream_value = getattr(page, field.name)
            for block, value in walk_blocks(field.stream_block, stream_value):
                if block.__class__.__name__.lstrip("_") == class_name:
                    matches.append((page, field.name, value))
    return matches


class Command(BaseCommand):
    help = "Find all instances of a given block class across every page's StreamFields."

    def add_arguments(self, parser):
        parser.add_argument("class_name", help="Block class name to search for, e.g. TwoColumnCardsBlock")

    def handle(self, *args, **options):
        class_name = options["class_name"]
        matches = find_block_instances(class_name)

        if not matches:
            self.stdout.write(self.style.WARNING(f"No instances of {class_name} found.\n"))
            return

        pages = {}
        for page, field_name, _value in matches:
            pages.setdefault(page, set()).add(field_name)

        rows = []
        for page, field_names in pages.items():
            try:
                url = page_url(page)
            except Exception:
                url = "—"
            rows.append((str(page.pk), page.locale.language_code, page.title, ", ".join(sorted(field_names)), url))

        headers = ("PK", "Locale", "Title", "Field(s)", "URL")
        widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

        def format_row(values):
            return "  ".join(value.ljust(width) for value, width in zip(values, widths))

        self.stdout.write(format_row(headers) + "\n")
        self.stdout.write("  ".join("-" * width for width in widths) + "\n")
        for row in rows:
            self.stdout.write(format_row(row) + "\n")

        self.stdout.write(self.style.SUCCESS(f"\n{len(matches)} instance(s) across {len(pages)} page(s).\n"))
