# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import codecs
import json
import os
import re
import xml.etree.ElementTree as etree
from datetime import timedelta
from glob import glob
from itertools import chain
from operator import attrgetter

from django.conf import settings
from django.core.cache import caches
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint
from django.forms.models import model_to_dict
from django.http import Http404
from django.utils.dateparse import parse_datetime
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.timezone import now

import bleach
import markdown
from django_extensions.db.fields.json import JSONField
from django_extensions.db.models import TimeStampedModel
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from product_details.version_compare import Version

from springfield.base.urlresolvers import reverse
from springfield.releasenotes import version_re


class StrikethroughInlineProcessor(InlineProcessor):
    def handleMatch(self, m, data):
        el = etree.Element("del")
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


class StrikethroughExtension(Extension):
    def extendMarkdown(self, md):
        STRIKETHROUGH_PATTERN = r"~~(.*?)~~"  # like ~~elided~~
        md.inlinePatterns.register(StrikethroughInlineProcessor(STRIKETHROUGH_PATTERN, md), "del", 175)


LONG_RN_CACHE_TIMEOUT = 7200  # 2 hours
cache = caches["release-notes"]
markdowner = markdown.Markdown(
    extensions=[
        "markdown.extensions.tables",
        "markdown.extensions.codehilite",
        "markdown.extensions.fenced_code",
        "markdown.extensions.toc",
        "markdown.extensions.nl2br",
        StrikethroughExtension(),
    ]
)
# based on bleach.sanitizer.ALLOWED_TAGS
ALLOWED_TAGS = {
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "small",
    "strike",
    "strong",
    "ul",
}
ALLOWED_ATTRS = [
    "alt",
    "class",
    "height",
    "href",
    "id",
    "src",
    "srcset",
    "rel",
    "title",
    "width",
]


def process_markdown(value):
    rendered_html = markdowner.reset().convert(value)
    return bleach.clean(rendered_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)


class MarkdownField(models.TextField):
    """Field that takes Markdown text as input and saves HTML to the database"""

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        value = process_markdown(value)
        setattr(model_instance, self.attname, value)
        return value


class ReleaseQuerySet(models.QuerySet):
    def product(self, product_name, channel_name=None, version=None):
        if product_name.lower() == "firefox extended support release":
            product_name = "firefox"
            channel_name = "esr"
        q = self.filter(product__iexact=product_name)
        if channel_name:
            q = q.filter(channel__iexact=channel_name)
        if version:
            q = q.filter(version=version)

        return q.prefetch_related("note_set")

class ReleaseManager(models.Manager):
    def get_queryset(self, include_drafts=False):
        qs = ReleaseQuerySet(self.model, using=self._db)
        if settings.DEV or settings.WAGTAIL_ENABLE_ADMIN or include_drafts:
            return qs

        return qs.filter(is_public=True)

    def product(self, product_name, channel_name=None, version=None, include_drafts=False):
        return self.get_queryset(include_drafts).product(product_name, channel_name, version)

    def all_as_list(self):
        """Return all releases as a list of dicts"""
        return [r.to_dict() for r in self.prefetch_related("note_set").all()]

    def recently_modified_list(self, days_ago=7, mod_date=None):
        if mod_date is None:
            mod_date = now() - timedelta(days=days_ago)

        query = self.filter(Q(modified__gte=mod_date) | Q(note__modified__gte=mod_date) | Q(fixed_note_set__modified__gte=mod_date)).distinct()
        return [r.to_dict() for r in query.prefetch_related("note_set")]


class Release(TimeStampedModel):
    CHANNELS = ("Nightly", "Beta", "Release", "ESR")
    PRODUCTS = ("Firefox", "Firefox for Android", "Firefox for iOS", "Firefox Extended Support Release", "Thunderbird")
    PUBLIC_ONLY = not (settings.DEV or settings.WAGTAIL_ENABLE_ADMIN)

    product = models.CharField(max_length=255, choices=[(p, p) for p in PRODUCTS])
    channel = models.CharField(max_length=255, choices=[(c, c) for c in CHANNELS])
    version = models.CharField(max_length=255)
    release_date = models.DateTimeField()
    text = models.TextField(blank=True)
    is_public = models.BooleanField(default=False, help_text="Note: If checked, these Release Notes will be visible on www.firefox.com")
    bug_list = models.TextField(blank=True)
    bug_search_url = models.CharField(max_length=2000, blank=True)
    system_requirements = models.TextField(blank=True)
    reviewed_by_release_manager = models.BooleanField(
        null=True,
        default=False,
        help_text="Purely a visual indicator in the admin - does not show on firefox.com",
    )

    objects = ReleaseManager()

    def get_absolute_url(self):
        if self.product == "Firefox for Android":
            urlname = "firefox.android.releasenotes"
        elif self.product == "Firefox for iOS":
            urlname = "firefox.ios.releasenotes"
        else:
            urlname = "firefox.desktop.releasenotes"

        prefix = "aurora" if self.channel == "Aurora" else "release"
        return reverse(urlname, args=[self.version, prefix])

    @property
    def slug(self):
        product = slugify(self.product)
        channel = self.channel.lower()
        if product.lower() == "firefox-extended-support-release":
            product = "firefox"
            channel = "esr"
        return "-".join([product, self.version, channel])

    @property
    def text_html(self):
        return process_markdown(self.text)

    @property
    def system_requirements_html(self):
        return process_markdown(self.system_requirements)

    @cached_property
    def major_version(self):
        return str(self.version_obj.major)

    @cached_property
    def major_version_int(self):
        return self.version_obj.major or 0

    @cached_property
    def version_obj(self):
        return Version(self.version)

    def get_bug_search_url(self):
        if self.bug_search_url:
            return self.bug_search_url

        if self.product == "Thunderbird":
            return (
                "https://bugzilla.mozilla.org/buglist.cgi?"
                "classification=Client%20Software&query_format=advanced&"
                "bug_status=RESOLVED&bug_status=VERIFIED&bug_status=CLOSED&"
                "target_milestone=Thunderbird%20{version}.0&product=Thunderbird"
                "&resolution=FIXED"
            ).format(version=self.major_version)

        return (
            "https://bugzilla.mozilla.org/buglist.cgi?"
            "j_top=OR&f1=target_milestone&o3=equals&v3=Firefox%20{version}&"
            "o1=equals&resolution=FIXED&o2=anyexact&query_format=advanced&"
            "f3=target_milestone&f2=cf_status_firefox{version}&"
            "bug_status=RESOLVED&bug_status=VERIFIED&bug_status=CLOSED&"
            "v1=mozilla{version}&v2=fixed%2Cverified&limit=0"
        ).format(version=self.major_version)

    def equivalent_release_for_product(self, product):
        """
        Returns the release for a specified product with the same
        channel and major version with the highest minor version,
        or None if no such releases exist
        """
        releases = Release.objects.filter(version__startswith=self.major_version + ".", channel=self.channel, product=product).order_by(
            "-version"
        )
        if not getattr(settings, "DEV", False):
            releases = releases.filter(is_public=True)
        if releases:
            return sorted(
                sorted(releases, reverse=True, key=lambda r: len(r.version.split("."))), reverse=True, key=lambda r: r.version.split(".")[1]
            )[0]

    def equivalent_android_release(self):
        if self.product == "Firefox":
            return self.equivalent_release_for_product("Firefox for Android")

    def equivalent_desktop_release(self):
        if self.product == "Firefox for Android":
            return self.equivalent_release_for_product("Firefox")

    def notes(self, public_only=None):
        """
        Retrieve a list of Note instances that should be shown for this
        release, grouped as either new features or known issues, and sorted
        first by sort_num highest to lowest and then by created date,
        which is applied to both groups,
        and then for new features we also sort by tag in the order specified
        by Note.TAGS, with untagged notes coming first, then finally moving
        any note with the fixed tag that starts with the release version to
        the top, for what we call "dot fixes".
        """
        if public_only is None:
            public_only = self.PUBLIC_ONLY

        tag_index = {tag: i for i, tag in enumerate(Note.TAGS)}
        notes = self.note_set.order_by("-sort_num", "created")
        if public_only:
            notes = notes.filter(is_public=True)
        known_issues = [n for n in notes if n.is_known_issue_for(self)]
        new_features = sorted(
            sorted((n for n in notes if not n.is_known_issue_for(self)), key=lambda note: tag_index.get(note.tag, 0)),
            key=lambda n: n.tag == "Fixed" and n.note.startswith(self.version),
            reverse=True,
        )

        return new_features, known_issues

    def get_notes(self):
        new_features, known_issues = self.notes(public_only=False)
        return list(chain(new_features, known_issues))

    def to_dict(self):
        """Return a dict all all data about the release"""
        data = model_to_dict(self, exclude=["id", "reviewed_by_release_manager"])
        data["title"] = str(self)
        data["slug"] = self.slug
        data["release_date"] = self.release_date.date().isoformat()
        data["created"] = self.created.isoformat()
        data["modified"] = self.modified.isoformat()
        new_features, known_issues = self.notes(public_only=False)
        for note in known_issues:
            note.tag = "Known"
        data["notes"] = [n.to_dict(self) for n in chain(new_features, known_issues)]
        return data

    def to_simple_dict(self):
        """Return a dict of only the basic data about the release"""
        return {
            "version": self.version,
            "product": self.product,
            "channel": self.channel,
            "is_public": self.is_public,
            "slug": self.slug,
            "title": str(self),
        }

    def __str__(self):
        return f"{self.product} {self.version} {self.channel}"

    class Meta:
        ordering = ["-release_date"]
        unique_together = (("product", "version"),)
        get_latest_by = "modified"


class Note(TimeStampedModel):
    TAGS = ("New", "Changed", "HTML5", "Feature", "Language", "Developer", "Enterprise", "Fixed", "Community")

    bug = models.IntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    releases = models.ManyToManyField(Release, blank=True)
    is_known_issue = models.BooleanField(default=False)
    fixed_in_release = models.ForeignKey(Release, on_delete=models.SET_NULL, null=True, blank=True, related_name="fixed_note_set")
    tag = models.CharField(max_length=255, blank=True, choices=[(t, t) for t in TAGS])
    sort_num = models.IntegerField(default=0)
    is_public = models.BooleanField(default=True)
    progressive_rollout = models.BooleanField(default=False)
    relevant_countries = models.ManyToManyField(
        "Country",
        blank=True,
        help_text=(
            "Select the countries where this Note applies, as part of a "
            "progressive rollout. This info will only be shown on the Release "
            "page if 'Progressive rollout', above, is ticked."
        ),
    )

    related_field_to_github = "releases"

    @property
    def note_html(self):
        return process_markdown(self.note)

    def is_known_issue_for(self, release):
        return self.is_known_issue and self.fixed_in_release != release

    def to_dict(self, release=None):
        data = model_to_dict(
            self,
            exclude=[
                "releases",
                "is_known_issue",
            ],
        )
        data["created"] = self.created.isoformat()
        data["modified"] = self.modified.isoformat()
        if self.fixed_in_release:
            data["fixed_in_release"] = self.fixed_in_release.to_simple_dict()
        else:
            del data["fixed_in_release"]

        if release and self.is_known_issue_for(release):
            data["tag"] = "Known"

        if self.relevant_countries.count():
            data["relevant_countries"] = [x.to_dict() for x in self.relevant_countries.all()]

        return data

    def __str__(self):
        return self.note

    class Meta:
        get_latest_by = "modified"


class Country(TimeStampedModel):
    # Simple model for associating a Country with a Note

    name = models.CharField(
        blank=False,
        max_length=128,
    )
    code = models.CharField(
        blank=False,
        help_text="3166-1-alpha-2 code",
        max_length=2,
    )

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ["name"]
        constraints = [
            UniqueConstraint(
                fields=["name", "code"],
                name="unique_country_name_for_code",
            ),
        ]

    def to_dict(self):
        data = model_to_dict(self)
        del data["id"]  # no need to dump out the internal ID for a Country
        return data


### END RNA MODELS


def get_release(product, version, channel=None, include_drafts=False):
    channels = [channel] if channel else Release.CHANNELS
    if product.lower() == "firefox extended support release":
        channels = ["esr"]
    for channel in channels:
        try:
            return Release.objects.product(product, channel, version, include_drafts).get()
        except Release.DoesNotExist:
            continue

    return None


def get_release_or_404(version, product, include_drafts=False):
    release = get_release(product, version, None, include_drafts)
    if release is None:
        raise Http404

    return release


def get_releases(product, channel, num_results=10):
    return Release.objects.product(product, channel)[:num_results]


def get_releases_or_404(product, channel, num_results=10):
    releases = get_releases(product, channel, num_results)
    if releases:
        return releases

    raise Http404


def get_latest_release(product, channel="release"):
    try:
        release = Release.objects.product(product, channel)[0]
    except IndexError:
        release = None

    return release


def get_latest_release_or_404(product, channel):
    release = get_latest_release(product, channel)
    if release:
        return release

    raise Http404
