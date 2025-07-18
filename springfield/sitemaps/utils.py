# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import json
import re
from collections import defaultdict
from unittest.mock import patch

from django.conf import settings
from django.http import HttpResponse
from django.test.client import Client
from django.urls import resolvers

from wagtail.models import Page

from springfield.releasenotes.models import ProductRelease


def get_release_notes_urls():
    urls = {}
    for release in ProductRelease.objects.exclude(product="Thunderbird"):
        # we redirect all release notes for versions 28.x and below to an archive
        # and Firefox for iOS uses a different version numbering scheme
        if release.product != "Firefox for iOS" and release.major_version_int < 29:
            continue

        try:
            rel_path = release.get_absolute_url()
            req_path = release.get_sysreq_url()
        except resolvers.NoReverseMatch:
            continue

        # strip "/en-US" off the front
        if rel_path.startswith("/en-US"):
            rel_path = rel_path[6:]
        if req_path.startswith("/en-US"):
            req_path = req_path[6:]

        urls[rel_path] = ["en-US"]
        urls[req_path] = ["en-US"]

    return urls


def get_static_urls():
    urls = {}
    client = Client()
    excludes = [
        re.compile(r)
        for r in settings.NOINDEX_URLS
        + [
            r".*%\(.*\).*",
            r".*//$",
            r"^media/",
            r"^robots\.txt$",
        ]
    ]

    # start with the ones we know we want
    urls.update(settings.EXTRA_INDEX_URLS)

    # get_resolver is an undocumented but convenient function.
    # Try to retrieve all valid URLs on this site.
    # NOTE: have to use `lists()` here since the standard
    # `items()` only returns the first item in the list for the
    # view since `reverse_dict` is a `MultiValueDict`.
    for key, values in resolvers.get_resolver(None).reverse_dict.lists():
        for value in values:
            path = value[0][0][0]

            # Re: https://github.com/mozilla/bedrock/issues/14480
            # Since the refactor to use Django's i18n mechanism, not our
            # original Prefixer, resolved URLs are automatically prepended
            # with settings.LANGUAGE_CODE, which downstream use of this data
            # is not expecting. The simplest fix is to drop that part of the path.
            _lang_prefix = f"{settings.LANGUAGE_CODE}/"
            path = path.replace(_lang_prefix, "", 1)

            # Exclude pages that we don't want be indexed by search engines.
            # Some other URLs are also unnecessary for the sitemap.
            if any(exclude.search(path) for exclude in excludes):
                continue

            path_prefix = path.split("/", 2)[0]
            nonlocale = path_prefix in settings.SUPPORTED_NONLOCALES
            path = f"/{path}"
            if nonlocale:
                locales = []
            else:
                with patch("lib.l10n_utils.django_render") as render:
                    render.return_value = HttpResponse()
                    client.get("/" + settings.LANGUAGE_CODE + path)

                # Exclude urls that did not call render
                if not render.called:
                    continue

                locales = set(render.call_args[0][2]["translations"].keys())

                # just remove any locales not in our prod list
                locales = list(locales.intersection(settings.PROD_LANGUAGES))

            if path not in urls:
                urls[path] = locales

    return urls


def _path_for_cms_url(page_url, lang_code):
    # If possible, drop the leading slash + lang code from the URL
    # so that we get a locale-agnostic path that we can include in the
    # sitemap.

    _path = page_url
    if _path.startswith(f"/{lang_code}/"):  # be sure we only clip out the first locale (ie, /fr/ not the first part of /france)
        _path = _path.replace(f"/{lang_code}", "", 1)  # we want to leave a leading slash before the rest of the path
    return _path


def get_wagtail_urls():
    urls = defaultdict(list)

    # Get all live, non-private Wagtail pages
    for cms_page in Page.objects.live().public().order_by("path"):
        # We don't want the Wagtail core Root page, nor the site root page,
        # because that isn't surfaced from the CMS (yet) and we don't want our
        # StructuralPage type either, which has a handy annotation to identify
        # it (If you don't know what 'specific' refers to, see
        # https://docs.wagtail.org/en/v6.2.1/reference/pages/model_reference.html#wagtail.models.Page.specific)
        if (
            cms_page.is_root()
            or cms_page.is_site_root()
            # not all pages have the is_structural_page attribute, so default those to False
            or getattr(cms_page.specific, "is_structural_page", False) is True
        ):
            # Don't include these pages in the sitemap
            continue

        _url = cms_page.get_url()
        if _url:
            lang_code = cms_page.locale.language_code
            _path = _path_for_cms_url(page_url=_url, lang_code=lang_code)
            urls[_path].append(lang_code)

    return urls


def get_all_urls():
    urls = get_static_urls()
    urls.update(get_release_notes_urls())
    urls.update(get_wagtail_urls())
    return urls


def update_sitemaps():
    urls = get_all_urls()
    # Output static files
    output_json(urls)


def output_json(urls):
    output_file = settings.ROOT_PATH.joinpath("root_files", "sitemap.json")

    # Output the data as a JSON file for convenience
    with output_file.open("w") as json_file:
        json.dump(urls, json_file)
