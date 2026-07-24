# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from springfield.base.tests import TestCase
from springfield.firefox.referral.models import FirefoxReferralData


class TestFirefoxReferralDataRefresh(TestCase):
    def test_fresh_insert_into_empty_table(self):
        loaded, skipped = FirefoxReferralData.objects.refresh([("ABC1234567", "42"), ("DEF9876543", "0")])
        self.assertEqual(loaded, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(FirefoxReferralData.objects.count(), 2)
        row = FirefoxReferralData.objects.get(referral_id="ABC1234567")
        self.assertEqual(row.install_count, 42)

    def test_replaces_existing_rows(self):
        FirefoxReferralData.objects.create(referral_id="OLD0000001", install_count=99)
        FirefoxReferralData.objects.create(referral_id="OLD0000002", install_count=100)

        loaded, skipped = FirefoxReferralData.objects.refresh([("NEW0000001", "7")])

        self.assertEqual(loaded, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(FirefoxReferralData.objects.count(), 1)
        self.assertFalse(FirefoxReferralData.objects.filter(referral_id="OLD0000001").exists())
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="NEW0000001").exists())

    def test_skips_malformed_rows(self):
        loaded, skipped = FirefoxReferralData.objects.refresh(
            [
                ("GOOD000001", "10"),
                ("", "5"),  # blank referral_id
                ("BAD0000001", "not-an-int"),  # non-integer count
                ("BAD0000002", "-3"),  # negative count
                ("BAD0000003", None),  # None coerces to TypeError
                ("GOOD000002", "0"),
            ]
        )
        self.assertEqual(loaded, 2)
        self.assertEqual(skipped, 4)
        self.assertEqual(
            set(FirefoxReferralData.objects.values_list("referral_id", flat=True)),
            {"GOOD000001", "GOOD000002"},
        )

    def test_skips_referral_id_over_max_length(self):
        # referral_id CharField(max_length=16). Anything longer must be caught
        # by the validator BEFORE bulk_create so we don't retry-storm on the row.
        loaded, skipped = FirefoxReferralData.objects.refresh(
            [
                ("GOOD000001", "1"),
                ("TOOLONG1234567890", "2"),  # 17 chars, over the 16-char limit
            ]
        )
        self.assertEqual(loaded, 1)
        self.assertEqual(skipped, 1)
        self.assertFalse(FirefoxReferralData.objects.filter(referral_id__startswith="TOOLONG").exists())

    def test_skips_install_count_over_int32_max(self):
        # PositiveIntegerField is a 32-bit Postgres integer; anything above
        # 2**31-1 would raise NumericValueOutOfRange inside bulk_create.
        loaded, skipped = FirefoxReferralData.objects.refresh(
            [
                ("GOOD000001", "1"),
                ("BAD0000001", str(2**31)),  # one over the ceiling
                ("BAD0000002", str(2**63)),  # comfortably huge
            ]
        )
        self.assertEqual(loaded, 1)
        self.assertEqual(skipped, 2)
        self.assertEqual(
            set(FirefoxReferralData.objects.values_list("referral_id", flat=True)),
            {"GOOD000001"},
        )

    def test_empty_input_raises_and_preserves_existing_table(self):
        FirefoxReferralData.objects.create(referral_id="XYZ0000001", install_count=1)
        with self.assertRaisesRegex(ValueError, "no valid rows"):
            FirefoxReferralData.objects.refresh([])
        # Table is untouched: an empty snapshot must never wipe live data.
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="XYZ0000001").exists())

    def test_all_malformed_input_raises_and_preserves_existing_table(self):
        FirefoxReferralData.objects.create(referral_id="XYZ0000001", install_count=1)
        garbage = [("", "5"), ("BAD", "not-an-int"), ("BAD2", "-1")]
        with self.assertRaisesRegex(ValueError, "3 rows skipped"):
            FirefoxReferralData.objects.refresh(garbage)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="XYZ0000001").exists())

    def test_last_refreshed_at_is_stamped(self):
        FirefoxReferralData.objects.refresh([("ABC1234567", "1")])
        row = FirefoxReferralData.objects.get(referral_id="ABC1234567")
        self.assertIsNotNone(row.last_refreshed_at)

    def test_string_referral_id_is_stripped(self):
        loaded, _ = FirefoxReferralData.objects.refresh([("  ABC1234567  ", "9")])
        self.assertEqual(loaded, 1)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="ABC1234567").exists())

    def test_generator_input_works(self):
        def gen():
            yield ("GEN0000001", "1")
            yield ("GEN0000002", "2")

        loaded, skipped = FirefoxReferralData.objects.refresh(gen())
        self.assertEqual(loaded, 2)
        self.assertEqual(skipped, 0)

    def test_streams_input_in_batches(self):
        """peak in-memory buffer stays bounded to REFRESH_BATCH_SIZE."""
        rows = [(f"ROW{i:07d}", str(i)) for i in range(7)]

        with mock.patch("springfield.firefox.referral.models.REFRESH_BATCH_SIZE", 3):
            manager = FirefoxReferralData.objects
            with mock.patch.object(manager, "bulk_create", wraps=manager.bulk_create) as spy:
                loaded, skipped = manager.refresh(iter(rows))

        self.assertEqual(loaded, 7)
        self.assertEqual(skipped, 0)
        self.assertEqual(FirefoxReferralData.objects.count(), 7)
        # 7 rows / batch of 3 => flushes of 3, 3, 1 (three bulk_create calls).
        self.assertEqual(spy.call_count, 3)
        for call in spy.call_args_list:
            (batch,) = call.args
            self.assertLessEqual(len(batch), 3)
