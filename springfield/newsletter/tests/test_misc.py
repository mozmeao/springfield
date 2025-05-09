# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from springfield.base.tests import TestCase
from springfield.newsletter import utils
from springfield.newsletter.models import Newsletter
from springfield.newsletter.tests import newsletters

newsletters_mock = mock.Mock()
newsletters_mock.return_value = newsletters


class TestNewsletterModel(TestCase):
    def setUp(self):
        Newsletter.objects.create(
            slug="dude",
            data={"title": "Abide", "languages": ["en"]},
        )
        Newsletter.objects.create(
            slug="donnie",
            data={"title": "Walrus", "languages": ["de"]},
        )
        self.data = {
            "dude": {
                "title": "Abide",
                "languages": ["en"],
            },
            "donnie": {
                "title": "Walrus",
                "languages": ["de"],
            },
        }

    def test_refresh_with_change(self):
        self.data["donnie"]["languages"].append("fr")
        count = Newsletter.objects.refresh(self.data)
        self.assertEqual(count, 2)
        # run again to verify updated
        count = Newsletter.objects.refresh(self.data)
        self.assertIsNone(count)

    def test_refresh_no_change(self):
        count = Newsletter.objects.refresh(self.data)
        self.assertIsNone(count)

    def test_serialize(self):
        # utils.get_newsletters returns Newsletter.objects.serialize()
        result = Newsletter.objects.serialize()
        self.assertEqual(result, self.data)


@mock.patch("springfield.newsletter.utils.get_newsletters", newsletters_mock)
class TestGetNewsletterLanguages(TestCase):
    def test_newsletter_langs(self):
        """Without args should return all langs."""
        result = utils.get_languages_for_newsletters()
        good_set = {"en", "es", "fr", "de", "pt", "ru"}
        self.assertSetEqual(good_set, result)

    def test_single_newsletter_langs(self):
        """Should return languages for a single newsletter."""
        result = utils.get_languages_for_newsletters("join-mozilla")
        good_set = {"en", "es"}
        self.assertSetEqual(good_set, result)

    def test_list_newsletter_langs(self):
        """Should return all languages for specified list of newsletters."""
        result = utils.get_languages_for_newsletters(["join-mozilla", "beta"])
        good_set = {"en", "es"}
        self.assertSetEqual(good_set, result)

        result = utils.get_languages_for_newsletters(["firefox-tips", "beta"])
        good_set = {"en", "fr", "de", "pt", "ru"}
        self.assertSetEqual(good_set, result)

    def test_works_with_bad_newsletter(self):
        """If given a bad newsletter name, should still return a set."""
        result = utils.get_languages_for_newsletters(["join-mozilla", "eldudarino"])
        good_set = {"en", "es"}
        self.assertSetEqual(good_set, result)
