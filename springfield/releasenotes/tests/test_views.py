# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import json
from datetime import timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils.http import http_date
from django.utils.timezone import now

import pytest

from springfield.releasenotes.models import Note, Release
from springfield.releasenotes.views import releases_index, show_android_sys_req, export_json


@pytest.mark.parametrize(
    "version_string, expected",
    (
        (None, False),
        ("", False),
        ("test", False),
        ("0", False),
        ("45", False),
        ("45.0", False),
        ("45.1.1", False),
        ("45.0a1", False),
        ("45.0a2", False),
        ("46", True),
        ("46.0", True),
        ("46.1.1", True),
        ("46.0a1", True),
        ("46.0a2", True),
        ("47", True),
        ("100", True),
        ("100.0", True),
        ("100.1.1", True),
        ("100.0a1", True),
        ("100.0a2", True),
        ("102", True),
        ("102.0", True),
        ("102.1.1", True),
        ("102.0a1", True),
        ("102.0a2", True),
    ),
)
def test_show_android_sys_req(version_string, expected):
    assert show_android_sys_req(version_string) == expected


@patch("springfield.firefox.views.l10n_utils.render")
def test_releases_index(render_mock, rf):
    """Spot checks, incl confirmation that FF100 will not cause a hiccup"""

    # Dates are from https://wiki.mozilla.org/Release_Management/Calendar but
    # these are here just for testing/dummy purposes
    mock_major_releases_val = {
        "3.6": "2010-01-21",
        "33.0": "2014-10-14",
        "33.1": "2014-11-10",
        "96.0": "2022-01-11",
        "100.0": "2022-05-03",
        "101.0": "2022-05-31",
    }
    mock_minor_releases_val = {
        "3.6.2": "2010-03-22",
        "3.6.3": "2010-04-01",
        "3.6.4": "2010-06-22",
        "3.6.6": "2010-06-26",
        "3.6.7": "2010-07-20",
        "3.6.8": "2010-07-23",
        "3.6.9": "2010-09-07",
        "3.6.10": "2010-09-15",
        "3.6.11": "2010-10-19",
        "3.6.12": "2010-10-27",
        "3.6.13": "2010-12-09",
        "3.6.14": "2011-03-01",
        "3.6.15": "2011-03-04",
        "3.6.16": "2011-03-22",
        "33.0.1": "2014-10-24",
        "33.0.2": "2014-10-28",
        "33.0.3": "2014-11-06",
        "33.1.1": "2014-11-14",
        "96.5": "2022-01-11",  # 100% fake/test
        "100.1": "2022-05-03",  # 100% fake/test
        "100.2": "2022-05-03",  # 100% fake/test
        "101.2": "2022-05-31",  # 100% fake/test
    }

    request = rf.get("/")

    with patch("springfield.releasenotes.views.firefox_desktop") as mock_firefox_desktop:
        mock_firefox_desktop.firefox_history_major_releases = mock_major_releases_val
        mock_firefox_desktop.firefox_history_stability_releases = mock_minor_releases_val

        releases_index(request, "Firefox")

    expected_data = {
        "releases": [
            (101.0, {"major": "101.0", "minor": ["101.2"]}),
            (
                100.0,
                {
                    "major": "100.0",
                    "minor": ["100.1", "100.2"],
                },
            ),
            (
                96.0,
                {
                    "major": "96.0",
                    "minor": ["96.5"],
                },
            ),
            (
                33.1,
                {
                    "major": "33.1",
                    "minor": ["33.1.1"],
                },
            ),
            (
                33.0,
                {
                    "major": "33.0",
                    "minor": ["33.0.1", "33.0.2", "33.0.3"],
                },
            ),
            (
                3.6,
                {
                    "major": "3.6",
                    "minor": [
                        "3.6.2",
                        "3.6.3",
                        "3.6.4",
                        "3.6.6",
                        "3.6.7",
                        "3.6.8",
                        "3.6.9",
                        "3.6.10",
                        "3.6.11",
                        "3.6.12",
                        "3.6.13",
                        "3.6.14",
                        "3.6.15",
                        "3.6.16",
                    ],
                },
            ),
        ],
    }
    render_mock.assert_called_once_with(
        request,
        "firefox/releases/index.html",
        expected_data,
    )


@patch("springfield.firefox.views.l10n_utils.render")
def test_releases_index__product_other_than_firefox(render_mock, rf):
    request = rf.get("/")
    releases_index(request, "someproduct")
    render_mock.assert_called_once_with(
        request,
        "someproduct/releases/index.html",
        {"releases": []},
    )


class TestExportJSON(TestCase):
    def setUp(self):
        over_20_days = now() - timedelta(days=22)
        over_30_days = now() - timedelta(days=32)
        over_40_days = now() - timedelta(days=42)
        self.r1 = Release.objects.create(
            product="Firefox",
            channel="Nightly",
            version="87.0a2",
            release_date=now(),
        )
        self.r2 = Release.objects.create(
            product="Firefox",
            channel="Nightly",
            version="88.0a2",
            release_date=now(),
        )
        # modified now
        self.r3 = Release.objects.create(
            product="Firefox",
            channel="Nightly",
            version="89.0a2",
            release_date=now(),
        )
        self.r1.modified = over_40_days
        self.r1.save(modified=False)
        self.r2.modified = over_30_days
        self.r2.save(modified=False)
        self.r3.modified = over_20_days
        self.r3.save(modified=False)
        self.rf = RequestFactory()

    def test_recently_modified_release(self):
        """Should only return releases modified more recently than 30 days ago"""
        resp = export_json(self.rf.get("/"))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version not in release_versions
        assert self.r2.version not in release_versions
        assert self.r3.version in release_versions

    def test_if_modified_since(self):
        """Should only return releases modified more recently than last-modified param"""
        over_30_days_ago = now() - timedelta(days=34)
        header_date = http_date(over_30_days_ago.timestamp())
        resp = export_json(self.rf.get("/", HTTP_IF_MODIFIED_SINCE=header_date))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version not in release_versions
        assert self.r2.version in release_versions
        assert self.r3.version in release_versions

    def test_if_modified_since_not_modified(self):
        """Should return an empty list if nothing has been modified since"""
        header_date = http_date(now().timestamp())
        resp = export_json(self.rf.get("/", HTTP_IF_MODIFIED_SINCE=header_date))
        data = json.loads(resp.content)
        assert data == []

    def test_invalid_if_modified_since_header(self):
        """Should go back to 14 day default if param is not ISO date"""
        header_date = "this is our concern Dude"
        resp = export_json(self.rf.get("/", HTTP_IF_MODIFIED_SINCE=header_date))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version not in release_versions
        assert self.r2.version not in release_versions
        assert self.r3.version in release_versions

    def test_recently_modified_note(self):
        """Should also return releases with notes modified more recently than 14 days ago"""
        self.r1.note_set.create(note="The Dude minds, man")
        resp = export_json(self.rf.get("/"))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version in release_versions
        assert self.r2.version not in release_versions
        assert self.r3.version in release_versions

    def test_recently_modified_note_distinct(self):
        """Should also return releases with notes modified more recently than 14 days ago"""
        note = Note.objects.create(note="The Dude minds, man")
        note2 = Note.objects.create(note="Careful, man, there’s a beverage here.")
        self.r1.note_set.add(note)
        self.r1.note_set.add(note2)
        resp = export_json(self.rf.get("/"))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version in release_versions
        assert self.r2.version not in release_versions
        assert self.r3.version in release_versions
        assert len(release_versions) == 2

    def test_recently_modified_fixed_in_note(self):
        """Should also return releases with notes modified more recently than 14 days ago"""
        self.r2.fixed_note_set.create(note="The Dude minds, man")
        resp = export_json(self.rf.get("/"))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version not in release_versions
        assert self.r2.version in release_versions
        assert self.r3.version in release_versions

    def test_all_as_list(self):
        """Should return all releases with no dupes"""
        note = Note.objects.create(note="The Dude minds, man")
        note2 = Note.objects.create(note="Careful, man, there’s a beverage here.")
        self.r1.note_set.add(note)
        self.r1.note_set.add(note2)
        resp = export_json(self.rf.get("/", {"all": "true"}))
        data = json.loads(resp.content)
        release_versions = [o["version"] for o in data]
        assert self.r1.version in release_versions
        assert self.r2.version in release_versions
        assert self.r3.version in release_versions
        assert len(release_versions) == 3
