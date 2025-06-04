# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import datetime
import json
import re
from copy import copy
from operator import attrgetter

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch
from django.utils.http import parse_http_date_safe
from django.utils.timezone import now
from django.views.decorators.cache import cache_page
from django.views.decorators.http import last_modified, require_safe

from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.viewsets import ModelViewSet

from lib import l10n_utils
from springfield.base.urlresolvers import reverse
from springfield.firefox.firefox_details import firefox_desktop
from springfield.firefox.templatetags.helpers import android_builds, ios_builds
from springfield.releasenotes.models import (
    Release,
    Note,
    get_latest_release_or_404,
    get_release_or_404,
    get_releases_or_404,
)
from springfield.releasenotes.serializers import NoteSerializer, ReleaseSerializer
from springfield.releasenotes.utils import HttpResponseJSON, get_last_modified_date

SUPPORT_URLS = {
    "Firefox for Android": "https://support.mozilla.org/products/mobile",
    "Firefox for iOS": "https://support.mozilla.org/products/ios",
    "Firefox": "https://support.mozilla.org/products/firefox",
}
RNA_JSON_CACHE_TIME = getattr(settings, "RNA_JSON_CACHE_TIME", 600)


def release_notes_template(channel, product, version=None):
    channel = channel or "release"
    version = version or 0

    if product == "Firefox" and channel == "Aurora" and version >= 35:
        return "firefox/releases/dev-browser-notes.html"

    dir = "firefox"

    return f"{dir}/releases/{channel.lower()}-notes.html"


def equivalent_release_url(release):
    equivalent_release = release.equivalent_android_release() or release.equivalent_desktop_release()
    if equivalent_release:
        return equivalent_release.get_absolute_url()


def get_download_url(release):
    if release.product == "Firefox for Android":
        return android_builds(release.channel)[0]["download_link"]
    elif release.product == "Firefox for iOS":
        return ios_builds(release.channel)[0]["download_link"]
    else:
        if release.channel == "Aurora":
            return reverse("firefox.channel.desktop", fragment="developer")
        elif release.channel == "Beta":
            return reverse("firefox.channel.desktop", fragment="beta")
        else:
            return reverse("firefox")


def show_android_sys_req(version):
    if version:
        match = re.match(r"\d{1,3}", version)
        if match:
            num_version = int(match.group(0))
            return num_version >= 46

    return False


def check_url(product, version):
    if product == "Firefox for Android":
        # System requirement pages for Android releases exist from 46.0 and upward.
        if show_android_sys_req(version):
            return reverse("firefox.android.system_requirements", args=[version])
        else:
            return settings.FIREFOX_MOBILE_SYSREQ_URL
    elif product == "Firefox for iOS":
        return reverse("firefox.ios.system_requirements", args=[version])
    else:
        return reverse("firefox.system_requirements", args=[version])


@require_safe
def release_notes(request, version, product="Firefox"):
    if not version:
        raise Http404

    # Show a "coming soon" page for any unpublished Firefox releases
    include_drafts = product in ["Firefox", "Firefox for Android"]

    try:
        release = get_release_or_404(version, product, include_drafts)
    except Http404:
        release = get_release_or_404(version + "beta", product, include_drafts)
        return HttpResponseRedirect(release.get_absolute_url())

    # add MDN link to all non-iOS releases. bug 1553566
    # avoid adding duplicate notes
    release_notes = copy(release.get_notes())
    if release.product != "Firefox for iOS":
        release_notes.insert(
            0,
            {
                "id": "mdn",
                "is_public": True,
                "tag": "Developer",
                "sort_num": 1,
                "note": f'<a class="mdn-icon" rel="external" '
                f'href="https://developer.mozilla.org/docs/Mozilla/Firefox/Releases/'
                f'{release.major_version}">Developer Information</a>',
            },
        )

    return l10n_utils.render(
        request,
        release_notes_template(release.channel, product, int(release.major_version)),
        {
            "version": version,
            "download_url": get_download_url(release),
            "support_url": SUPPORT_URLS.get(product, "https://support.mozilla.org/"),
            "check_url": check_url(product, version),
            "release": release,
            "release_notes": release_notes,
            "equivalent_release_url": equivalent_release_url(release),
        },
    )


@require_safe
def system_requirements(request, version, product="Firefox"):
    release = get_release_or_404(version, product)
    dir = "firefox"
    return l10n_utils.render(request, f"{dir}/releases/system_requirements.html", {"release": release, "version": version})


def latest_release(product="firefox", platform=None, channel=None):
    if not platform:
        platform = "desktop"
    elif platform == "android":
        product = "firefox for android"
    elif platform == "ios":
        product = "firefox for ios"

    if not channel:
        channel = "release"
    elif channel in ["developer", "earlybird"]:
        channel = "beta"
    elif channel == "organizations":
        channel = "esr"

    return get_latest_release_or_404(product, channel)


@require_safe
def latest_notes(request, product="firefox", platform=None, channel=None):
    release = latest_release(product, platform, channel)
    return HttpResponseRedirect(release.get_absolute_url())


@require_safe
def latest_sysreq(request, product="firefox", platform=None, channel=None):
    release = latest_release(product, platform, channel)
    return HttpResponseRedirect(release.get_sysreq_url())


@require_safe
def releases_index(request, product):
    releases = {}
    major_releases = []

    if product == "Firefox":
        major_releases = firefox_desktop.firefox_history_major_releases
        minor_releases = firefox_desktop.firefox_history_stability_releases

    for release in major_releases:
        major_version = float(re.findall(r"^\d+\.\d+", release)[0])
        # The version numbering scheme of Firefox changes sometimes. The second
        # number has not been used since Firefox 4, then reintroduced with
        # Firefox ESR 24 (Bug 870540). On this index page, 24.1.x should be
        # fallen under 24.0. This pattern is a tricky part.
        # The outlier is 33.1 which is in major_releases for some reason.
        major_pattern = r"^" + re.escape(
            f"{major_version:.0f}." if major_version > 4 and release not in ["33.0", "33.1"] else f"{major_version:.1f}."
        )
        releases[major_version] = {
            "major": release,
            "minor": sorted(
                [x for x in minor_releases if re.findall(major_pattern, x) if x not in major_releases], key=lambda x: [int(y) for y in x.split(".")]
            ),
        }

    return l10n_utils.render(request, f"{product.lower()}/releases/index.html", {"releases": sorted(releases.items(), reverse=True)})


@require_safe
def nightly_feed(request):
    """Serve an Atom feed with the latest changes in Firefox Nightly"""
    notes = {}
    releases = get_releases_or_404("firefox", "nightly", 5)

    for release in releases:
        try:
            link = reverse("firefox.desktop.releasenotes", args=(release.version, "release"))
        except NoReverseMatch:
            continue

        for note in release.get_notes():
            if note.id in notes:
                continue

            if note.is_public and note.tag:
                note.link = f"{link}#note-{note.id}"
                note.version = release.version
                notes[note.id] = note

    # Sort by date in descending order
    notes = sorted(notes.values(), key=attrgetter("modified"), reverse=True)

    return l10n_utils.render(request, "firefox/releases/nightly-feed.xml", {"notes": notes}, content_type="application/atom+xml")


def auth_token(request):
    if request.user.is_active and request.user.is_staff:
        token, created = Token.objects.get_or_create(user=request.user)
        return HttpResponse(content=json.dumps({"token": token.key}), content_type="application/json")
    else:
        return HttpResponseForbidden()


class NoteViewSet(ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer


class ReleaseViewSet(ModelViewSet):
    queryset = Release.objects.all()
    serializer_class = ReleaseSerializer


class NestedNoteView(generics.ListAPIView):
    model = Note
    serializer_class = NoteSerializer

    def get_queryset(self):
        release = get_object_or_404(Release, pk=self.kwargs.get("pk"))
        return release.note_set.all()


@cache_page(RNA_JSON_CACHE_TIME)
@last_modified(get_last_modified_date)
@require_safe
def export_json(request):
    if request.GET.get("all") == "true":
        return HttpResponseJSON(Release.objects.all_as_list(), cors=True)

    mod_date = parse_http_date_safe(request.headers.get("If-Modified-Since"))
    if mod_date:
        mod_date = datetime.datetime.fromtimestamp(mod_date, datetime.UTC)
    else:
        mod_date = now() - datetime.timedelta(days=30)

    return HttpResponseJSON(Release.objects.recently_modified_list(mod_date=mod_date), cors=True)
