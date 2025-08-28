# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import chain
from pathlib import Path
from unittest.mock import call, patch

from django.core.cache import caches
from django.test.utils import override_settings

import markdown
import pytest
from product_details import product_details

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
        release = models.ProductRelease(channel="Aurora", version="42.0a2", product="Firefox for Android")
        assert release.get_absolute_url() == mock_reverse.return_value
        mock_reverse.assert_called_with("firefox.android.releasenotes", args=["42.0a2", "aurora"])

    def test_desktop_releasenotes_url(self, mock_reverse):
        """
        Should return the results of reverse with the correct args
        """
        release = models.ProductRelease(version="42.0", product="Firefox")
        assert release.get_absolute_url() == mock_reverse.return_value
        mock_reverse.assert_called_with("firefox.desktop.releasenotes", args=["42.0", "release"])


@override_settings(RELEASE_NOTES_PATH=RELEASES_PATH, DEV=False)
class TestReleaseModel(TestCase):
    def setUp(self):
        models.ProductRelease.objects.refresh()
        release_cache.clear()

    def _add_in_ff100(self):
        # TODO: remove once FF100 data is properly in the dataset
        last = models.ProductRelease.objects.filter(channel="Nightly").last()
        last.pk = None
        last.version = "100.0a1"
        last.title = "Firefox 100.0a1 Nightly"
        last.slug = "firefox-100.0a1-nightly"
        last.notes = []
        last.save()
        assert last.pk is not None
        release_cache.clear()

    def test_release_major_version(self):
        rel = models.get_release("firefox", "57.0a1")
        assert rel.major_version == "57"

    def test_release_major_version__ff100(self):
        self._add_in_ff100()
        rel = models.get_release("firefox", "100.0a1")
        assert rel.major_version == "100"

    def test_get_bug_search_url(self):
        rel = models.get_release("firefox", "57.0a1")
        assert "=Firefox%2057&" in rel.get_bug_search_url()
        rel.bug_search_url = "custom url"
        assert "custom url" == rel.get_bug_search_url()

    def test_get_bug_search_url__ff100(self):
        self._add_in_ff100()
        rel = models.get_release("firefox", "100.0a1")
        assert "=Firefox%20100&" in rel.get_bug_search_url()
        rel.bug_search_url = "custom url"
        assert "custom url" == rel.get_bug_search_url()

    def test_equivalent_release_for_product(self):
        """Based on the test files the equivalent release for 56 should be 56.0.2"""
        rel = models.get_release("firefox", "56.0", "release")
        android = rel.equivalent_release_for_product("Firefox for Android")
        assert android.version == "56.0.2"
        assert android.product == "Firefox for Android"

    def test_equivalent_release_for_product_none_match(self):
        rel = models.get_release("firefox", "45.0esr")
        android = rel.equivalent_release_for_product("Firefox for Android")
        assert android is None

    def test_note_fixed_in_release(self):
        rel = models.get_release("firefox", "55.0a1")
        note = rel.get_notes()[11]
        with self.activate_locale("en-US"):
            assert note.fixed_in_release.get_absolute_url() == "/en-US/firefox/55.0a1/releasenotes/"

    def test_field_processors(self):
        rel = models.get_release("firefox", "57.0a1")
        # datetime conversion
        assert rel.created.year == 2017
        # datetime conversion
        assert rel.modified.year == 2017
        # date conversion
        assert rel.release_date.year == 2017
        # markdown
        assert rel.system_requirements.startswith('<h2 id="windows">Windows</h2>')
        # version
        assert rel.version_obj.major == 57

        # notes
        note = rel.get_notes()[0]
        # datetime conversion
        assert note.created.year == 2017
        # datetime conversion
        assert note.modified.year == 2017
        # markdown
        assert note.note.startswith("<p>Firefox Nightly")
        assert note.id == 787203

    def test_product_method_gets_specifically_latest_esr_based_on_product_details(self):
        _patched_dict = product_details.firefox_versions
        _patched_dict.update({"FIREFOX_ESR": "999.76"})

        with patch.dict("springfield.releasenotes.models.product_details.firefox_versions", _patched_dict):
            # See https://github.com/mozilla/bedrock/issues/16289
            query = models.ProductRelease.objects.product(product_name="firefox", channel_name="esr")

        raw_query_as_str = str(query.query)
        assert 'AND "releasenotes_productrelease"."channel" LIKE esr' in raw_query_as_str
        assert 'AND "releasenotes_productrelease"."version" = 999.76' in raw_query_as_str

    @override_settings(DEV=False)
    def test_is_public_query(self):
        """Should not return the release value when DEV is false.

        Should also only include public notes."""
        assert models.get_release("firefox for android", "56.0.3") is None
        rel = models.get_release("firefox", "57.0a1")
        assert len(rel.get_notes()) == 4

    @override_settings(DEV=True)
    def test_is_public_field_processor_dev_true(self):
        """Should always be true when DEV is true."""
        models.get_release("firefox for android", "56.0.3")
        rel = models.get_release("firefox", "57.0a1")
        assert len(rel.get_notes()) == 6

    @override_settings(DEV=True)
    def test_invalid_version(self):
        """Should not load data for invalid versions."""
        models.ProductRelease.objects.refresh()
        release_cache.clear()
        assert models.get_release("firefox", "copy-56.0") is None


@patch.object(models.ProductRelease, "objects")
class TestGetRelease(TestCase):
    def setUp(self):
        release_cache.clear()

    def test_get_release(self, manager_mock):
        manager_mock.product().get.return_value = "dude is released"
        assert models.get_release("Firefox", "57.0") == "dude is released"
        manager_mock.product.assert_called_with("Firefox", models.ProductRelease.CHANNELS[0], "57.0", False)

    def test_get_release_esr(self, manager_mock):
        manager_mock.product().get.return_value = "dude is released"
        assert models.get_release("Firefox Extended Support Release", "51.0") == "dude is released"
        manager_mock.product.assert_called_with("Firefox Extended Support Release", "esr", "51.0", False)

    def test_get_release_none_match(self, manager_mock):
        """Make sure the proper exception is raised if no file matches the query"""
        manager_mock.product().get.side_effect = models.ProductRelease.DoesNotExist
        assert models.get_release("Firefox", "57.0") is None

        expected_calls = chain.from_iterable((call("Firefox", ch, "57.0", False), call().get()) for ch in models.ProductRelease.CHANNELS)
        manager_mock.product.assert_has_calls(expected_calls)


@override_settings(RELEASE_NOTES_PATH=RELEASES_PATH, DEV=False)
class TestGetLatestRelease(TestCase):
    def setUp(self):
        models.ProductRelease.objects.refresh()
        release_cache.clear()

    def test_latest_release(self):
        correct_release = models.get_release("firefox for android", "56.0.2")
        assert models.get_latest_release("firefox for android", "release") == correct_release

    def test_non_public_release_not_duped(self):
        # refresh again
        models.ProductRelease.objects.refresh()
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


@pytest.mark.parametrize(
    "input_md, expected",
    (
        ("basic test", "<p>basic test</p>"),
        ("This is [a link](https://example.com)", '<p>This is <a href="https://example.com">a link</a></p>'),
        (
            (
                "<video width='320' height='240' controls loop='true' preload='true' autoplay='true' muted='true' playsinline='true' poster='example.jpg' foo bar baz>"  # noqa: E501
                "<source src='example.mp4' type='video/mp4' rel='prefetch' foo bar evilattribute/>"
                "<source src='example.webm' type='video/webm' rel='prefetch' foo bar/>"
                "Your browser does not support the video tag."
                "</video>"
            ),
            (
                '<video width="320" height="240" controls loop="true" preload="true" autoplay muted="true" playsinline="true" poster="example.jpg">'  # noqa: E501
                '<source src="example.mp4" type="video/mp4" rel="prefetch">'
                '<source src="example.webm" type="video/webm" rel="prefetch">'
                "Your browser does not support the video tag."
                "</video>"
            ),
        ),
        (
            (
                "<video src='example.mp4' type='video/mp4' width='320' height='240' controls loop='true' preload='true' autoplay='true' muted='true' playsinline='true' poster='example.jpg' foo bar baz>"  # noqa: E501
                "Your browser does not support the video tag."
                "</video>"
            ),
            (
                '<video src="example.mp4" type="video/mp4" width="320" height="240" controls loop="true" preload="true" autoplay muted="true" playsinline="true" poster="example.jpg">'  # noqa: E501
                "Your browser does not support the video tag."
                "</video>"
            ),
        ),
    ),
)
def test_process_markdown(input_md, expected):
    processed = models.process_markdown(input_md)
    assert processed == expected
