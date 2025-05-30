# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from itertools import chain
from pathlib import Path
from unittest.mock import call, patch

from django.core.cache import caches
from django.test.utils import override_settings

import markdown

from springfield.base.tests import TestCase
from springfield.releasenotes import models

RELEASES_PATH = str(Path(__file__).parent)
release_cache = caches["release-notes"]


@patch("springfield.releasenotes.models.reverse")
class TestReleaseNotesURL(TestCase):
    def test_aurora_android_releasenotes_url(self, mock_reverse):
        """
        Should return the results of reverse with the correct args
        """
        release = models.Release(channel="Aurora", version="42.0a2", product="Firefox for Android")
        assert release.get_absolute_url() == mock_reverse.return_value
        mock_reverse.assert_called_with("firefox.android.releasenotes", args=["42.0a2", "aurora"])

    def test_desktop_releasenotes_url(self, mock_reverse):
        """
        Should return the results of reverse with the correct args
        """
        release = models.Release(version="42.0", product="Firefox")
        assert release.get_absolute_url() == mock_reverse.return_value
        mock_reverse.assert_called_with("firefox.desktop.releasenotes", args=["42.0", "release"])


@patch.object(models.Release, "objects")
class TestGetRelease(TestCase):
    def setUp(self):
        release_cache.clear()

    def test_get_release(self, manager_mock):
        manager_mock.product().get.return_value = "dude is released"
        assert models.get_release("Firefox", "57.0") == "dude is released"
        manager_mock.product.assert_called_with("Firefox", models.Release.CHANNELS[0], "57.0", False)

    def test_get_release_esr(self, manager_mock):
        manager_mock.product().get.return_value = "dude is released"
        assert models.get_release("Firefox Extended Support Release", "51.0") == "dude is released"
        manager_mock.product.assert_called_with("Firefox Extended Support Release", "esr", "51.0", False)

    def test_get_release_none_match(self, manager_mock):
        """Make sure the proper exception is raised if no file matches the query"""
        manager_mock.product().get.side_effect = models.Release.DoesNotExist
        assert models.get_release("Firefox", "57.0") is None

        expected_calls = chain.from_iterable((call("Firefox", ch, "57.0", False), call().get()) for ch in models.Release.CHANNELS)
        manager_mock.product.assert_has_calls(expected_calls)


@override_settings(RELEASE_NOTES_PATH=RELEASES_PATH, DEV=False)
class TestGetLatestRelease(TestCase):
    def setUp(self):
        models.Release.objects.refresh()
        release_cache.clear()

    def test_latest_release(self):
        correct_release = models.get_release("firefox for android", "56.0.2")
        assert models.get_latest_release("firefox for android", "release") == correct_release

    def test_non_public_release_not_duped(self):
        # refresh again
        models.Release.objects.refresh()
        release_cache.clear()
        # non public release
        # should NOT raise multiple objects error
        assert models.get_release("firefox for android", "56.0.3", include_drafts=True)


class StrikethroughExtensionTestCase(TestCase):
    def test_strikethrough_rendered_to_del(self):
        # Show the StrikethroughExtension works
        self.assertEqual(
            markdown.markdown("*hello~~test~~*", extensions=[models.StrikethroughExtension()]),
            "<p><em>hello<del>test</del></em></p>",
        )

        # And without strikethough extension - no transformation
        self.assertEqual(
            markdown.markdown("*hello~~test~~*"),
            "<p><em>hello~~test~~</em></p>",
        )


class TestReleaseQueries(TestCase):
    def setUp(self):
        one_week_ago = now() - timedelta(days=7)
        two_weeks_ago = now() - timedelta(days=14)
        self.r1 = models.Release.objects.create(
            product="Firefox",
            channel="Nightly",
            version="87.0a2",
            release_date=now(),
        )
        self.r2 = models.Release.objects.create(
            product="Firefox",
            channel="Nightly",
            version="88.0a2",
            release_date=now(),
        )
        # modified now
        self.r3 = models.Release.objects.create(
            product="Firefox",
            channel="Nightly",
            version="89.0a2",
            release_date=now(),
        )
        self.r1.modified = two_weeks_ago
        self.r1.save(modified=False)
        self.r2.modified = one_week_ago
        self.r2.save(modified=False)

    def test_recently_modified_release(self):
        """Should only return releases modified more recently than `days_ago`"""
        data = models.Release.objects.recently_modified_list(days_ago=5)
        versions = [o["version"] for o in data]
        assert self.r1.version not in versions
        assert self.r2.version not in versions
        assert self.r3.version in versions

    def test_recently_modified_note(self):
        """Should also return releases with notes modified more recently than `days_ago`"""
        self.r1.note_set.create(note="The Dude minds, man")
        data = models.Release.objects.recently_modified_list(days_ago=5)
        versions = [o["version"] for o in data]
        assert self.r1.version in versions
        assert self.r2.version not in versions
        assert self.r3.version in versions

    def test_recently_modified_fixed_in_note(self):
        """Should also return releases with notes modified more recently than `days_ago`"""
        self.r2.fixed_note_set.create(note="The Dude minds, man")
        data = models.Release.objects.recently_modified_list(days_ago=5)
        versions = [o["version"] for o in data]
        assert self.r1.version not in versions
        assert self.r2.version in versions
        assert self.r3.version in versions

    def test_distinct_recently_modified(self):
        note = models.Note.objects.create(note="The Dude minds, man")
        note2 = models.Note.objects.create(note="Careful, man, there’s a beverage here.")
        self.r3.note_set.add(note)
        self.r2.note_set.add(note)
        self.r3.note_set.add(note2)
        data = models.Release.objects.recently_modified_list(days_ago=5)
        versions = [o["version"] for o in data]
        assert self.r1.version not in versions
        assert self.r2.version in versions
        assert self.r3.version in versions
        assert len(versions) == 2


class TestNote(TestCase):
    def test_to_dict__simple__no_relations(self):
        # Very simple test of the to_dict() method, mainly
        # to prove that progressive_rollout is included
        data = dict(
            bug=1234,
            note="Test note",
            tag="this is a tag",
            sort_num=1,
            is_public=True,
            progressive_rollout=True,
        )

        note = Note(**data)
        note.save()

        dumped_dict = note.to_dict()
        for key in [
            "bug",
            "note",
            "tag",
            "sort_num",
            "is_public",
            "progressive_rollout",
        ]:
            assert dumped_dict[key] == data[key]

        assert "created" in dumped_dict
        assert "modified" in dumped_dict

    def test_to_dict__relevant_country_field(self):
        # Country data is bootstrapped by a data migration

        iceland = models.Country.objects.get(code="IS")
        india = models.Country.objects.get(code="IN")

        data = dict(
            bug=1234,
            note="Test note",
            tag="this is a tag",
            sort_num=1,
            is_public=True,
            progressive_rollout=True,
        )

        note = models.Note(**data)
        note.save()

        assert note.relevant_countries.count() == 0
        dumped_dict = note.to_dict()
        assert dumped_dict["relevant_countries"] == []

        note.relevant_countries.add(india)
        note.relevant_countries.add(iceland)
        assert note.relevant_countries.count() == 2

        dumped_dict = note.to_dict()
        assert dumped_dict["relevant_countries"] == [
            {"name": "Iceland", "code": "IS"},
            {"name": "India", "code": "IN"},
        ]
