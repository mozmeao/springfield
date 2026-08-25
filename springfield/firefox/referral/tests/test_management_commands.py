# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io
from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from google.cloud.exceptions import NotFound

from springfield.base.tests import TestCase
from springfield.firefox.referral.models import FirefoxReferralData

COMMAND = "update_referral_data"

# Invite codes are 17-char Crockford Base32 (1 version byte + 16 ciphertext
# chars). The test mock strips the version byte so the stored referral_id is
# the remaining 16 chars — easy to assert against.
INVITE_CODE_A = "1AAAAAAAAAAAAAAAA"  # decrypts → AAAAAAAAAAAAAAAA
INVITE_CODE_B = "1BBBBBBBBBBBBBBBB"  # decrypts → BBBBBBBBBBBBBBBB
REFERRAL_ID_A = INVITE_CODE_A[1:]
REFERRAL_ID_B = INVITE_CODE_B[1:]

FIXTURE_CSV = f"{INVITE_CODE_A},42\n{INVITE_CODE_B},3\n"
DEFAULT_BLOB_NAME = "referral_data-2026-07-22.csv"


def _make_blob(updated, csv_body=FIXTURE_CSV, name=DEFAULT_BLOB_NAME):
    blob = mock.MagicMock()
    # .name has to be set post-construction — MagicMock(name=...) sets the
    # mock's repr name, not an attribute.
    blob.name = name
    blob.updated = updated
    # StringIO already supports the context-manager protocol, so `with blob.open("r") as fh`
    # works without extra MagicMock plumbing.
    blob.open = mock.MagicMock(return_value=io.StringIO(csv_body))
    return blob


def _patch_storage_client(blobs=None, list_blobs_side_effect=None):
    """Patch storage.Client so bucket().list_blobs() yields the given blob(s).

    Pass `list_blobs_side_effect=NotFound(...)` to simulate a missing bucket.
    Pass a single blob or a list of blobs to simulate 1+ published files.
    """
    client = mock.MagicMock(name="client")
    bucket = client.bucket.return_value
    if list_blobs_side_effect is not None:
        bucket.list_blobs.side_effect = list_blobs_side_effect
    else:
        if blobs is None:
            blobs = []
        elif not isinstance(blobs, list):
            blobs = [blobs]
        bucket.list_blobs.return_value = iter(blobs)
    return mock.patch(
        "springfield.firefox.management.commands.update_referral_data.storage.Client",
        return_value=client,
    )


@override_settings(REFERRAL_DATA_GCS_BUCKET="fake-bucket", REFERRAL_DATA_GCS_OBJECT_NAME_PREFIX="referral_data")
class TestUpdateReferralDataCommand(TestCase):
    def setUp(self):
        super().setUp()
        # Mock decryption: strip the version prefix, yielding the remaining
        # 16 chars as the referral_id. Real crypto is tested in test_crypto.py.
        patcher = mock.patch(
            "springfield.firefox.management.commands.update_referral_data.invite_code_to_referral_id",
            side_effect=lambda code: code[1:],
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # Enable the ENABLE_REFERRAL_IMPORT switch for all tests by default.
        # test_waffle_switch_off_skips_import overrides this to False.
        switch_patcher = mock.patch("springfield.base.waffle.switch_is_active", return_value=True)
        switch_patcher.start()
        self.addCleanup(switch_patcher.stop)

    def test_happy_path_loads_rows_into_empty_db(self):
        blob = _make_blob(updated=timezone.now())
        with _patch_storage_client(blob):
            call_command(COMMAND, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 2)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id=REFERRAL_ID_A, install_count=42).exists())
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id=REFERRAL_ID_B, install_count=3).exists())

    def test_picks_newest_of_multiple_published_files(self):
        # Data Eng leaves prior publishes in the bucket; we import the newest
        # by lex-sort of the blob name (chronological for their format).
        invite_code_old = "1CCCCCCCCCCCCCCC1"
        invite_code_new = "1DDDDDDDDDDDDDDD1"
        old_body = f"{invite_code_old},1\n"
        new_body = f"{invite_code_new},2\n"
        older = _make_blob(
            updated=timezone.now() - timedelta(days=1),
            csv_body=old_body,
            name="referral_data-2026-07-21.csv",
        )
        newer = _make_blob(
            updated=timezone.now(),
            csv_body=new_body,
            name="referral_data-2026-07-22.csv",
        )
        # List in intentionally scrambled order to prove we sort, not "trust list order".
        with _patch_storage_client([newer, older]):
            call_command(COMMAND, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 1)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id=invite_code_new[1:]).exists())
        # Only the newest blob's stream should have been opened.
        newer.open.assert_called_once()
        older.open.assert_not_called()

    def test_skip_when_newest_blob_older_than_max_last_refreshed(self):
        # Seed the table so max(last_refreshed_at) is "now".
        FirefoxReferralData.objects.create(referral_id="SEED000001", install_count=1)
        older = timezone.now() - timedelta(hours=1)

        blob = _make_blob(updated=older)
        with _patch_storage_client(blob):
            call_command(COMMAND, quiet=True)

        # Skip path: table unchanged, blob.open not called.
        self.assertEqual(FirefoxReferralData.objects.count(), 1)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="SEED000001").exists())
        blob.open.assert_not_called()

    def test_force_bypasses_skip(self):
        FirefoxReferralData.objects.create(referral_id="SEED000001", install_count=1)
        older = timezone.now() - timedelta(hours=1)

        blob = _make_blob(updated=older)
        with _patch_storage_client(blob):
            call_command(COMMAND, force=True, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 2)
        self.assertFalse(FirefoxReferralData.objects.filter(referral_id="SEED000001").exists())

    def test_fresh_deploy_empty_table_always_imports(self):
        # db_max is None; blob.updated being "old" must not skip.
        old = timezone.now() - timedelta(days=30)
        blob = _make_blob(updated=old)
        with _patch_storage_client(blob):
            call_command(COMMAND, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 2)

    @override_settings(DEV=False)
    def test_waffle_switch_off_skips_import(self):
        # When ENABLE_REFERRAL_IMPORT is inactive the command must exit before
        # touching GCS or the DB.
        blob = _make_blob(updated=timezone.now())
        with _patch_storage_client(blob), mock.patch("springfield.base.waffle.switch_is_active", return_value=False):
            call_command(COMMAND, quiet=True)

        blob.open.assert_not_called()
        self.assertEqual(FirefoxReferralData.objects.count(), 0)

    @override_settings(REFERRAL_DATA_GCS_BUCKET="")
    def test_empty_bucket_setting_no_ops(self):
        # storage.Client() must not be constructed if the bucket setting is empty.
        with mock.patch("springfield.firefox.management.commands.update_referral_data.storage.Client") as client_cls:
            call_command(COMMAND, quiet=True)
            client_cls.assert_not_called()

        self.assertEqual(FirefoxReferralData.objects.count(), 0)

    def test_no_matching_files_is_graceful_skip(self):
        # Bucket exists but no publishes yet (or the prefix doesn't match).
        FirefoxReferralData.objects.create(referral_id="KEEP000001", install_count=99)
        with _patch_storage_client([]):
            call_command(COMMAND, quiet=True)

        # Table preserved, no exception raised.
        self.assertEqual(FirefoxReferralData.objects.count(), 1)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="KEEP000001").exists())

    def test_missing_bucket_is_graceful_skip(self):
        # Bucket doesn't exist (deleted, renamed, wrong env). list_blobs raises
        # NotFound; command must swallow and log, not page Sentry every tick.
        FirefoxReferralData.objects.create(referral_id="KEEP000001", install_count=99)
        with _patch_storage_client(list_blobs_side_effect=NotFound("bucket gone")):
            call_command(COMMAND, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 1)

    def test_rows_with_extra_columns_are_dropped(self):
        # _iter_rows requires exactly two columns. If Data Eng ever emits a
        # third column, those rows are dropped rather than silently accepted
        # with the extras ignored, so the schema drift is more visible.
        body = f"{INVITE_CODE_A},42\n{INVITE_CODE_B},3,unexpected\n"
        blob = _make_blob(updated=timezone.now(), csv_body=body)
        with _patch_storage_client(blob):
            call_command(COMMAND, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 1)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id=REFERRAL_ID_A).exists())
        self.assertFalse(FirefoxReferralData.objects.filter(referral_id=REFERRAL_ID_B).exists())

    def test_failed_decryption_counts_as_skipped(self):
        # An invite code that fails decryption is counted as a skipped row,
        # not a crash. The remaining valid codes are still imported.
        bad_code = "NOTAVALIDCODE1234"  # wrong length/format, decrypt will raise
        body = f"{bad_code},42\n{INVITE_CODE_B},3\n"
        blob = _make_blob(updated=timezone.now(), csv_body=body)

        # Override: bad_code raises, good code decrypts normally.
        def _decrypt(code):
            if code == bad_code:
                raise ValueError("bad invite code")
            return code[1:]

        with (
            _patch_storage_client(blob),
            mock.patch(
                "springfield.firefox.management.commands.update_referral_data.invite_code_to_referral_id",
                side_effect=_decrypt,
            ),
        ):
            call_command(COMMAND, quiet=True)

        self.assertEqual(FirefoxReferralData.objects.count(), 1)
        self.assertTrue(FirefoxReferralData.objects.filter(referral_id=REFERRAL_ID_B).exists())

    def test_empty_csv_raises_and_preserves_existing_data(self):
        # An empty snapshot from Data Eng must not wipe the table. The command
        # should let refresh()'s ValueError propagate so run-db-update.sh
        # flags failure_detected and DMS is not pinged.
        FirefoxReferralData.objects.create(referral_id="KEEP000001", install_count=99)
        blob = _make_blob(updated=timezone.now(), csv_body="")
        with _patch_storage_client(blob), self.assertRaisesRegex(ValueError, "no valid rows"):
            call_command(COMMAND, quiet=True)

        self.assertTrue(FirefoxReferralData.objects.filter(referral_id="KEEP000001").exists())

    def test_list_blobs_uses_prefix_dash(self):
        # Verify the command passes the trailing-dash prefix so it doesn't
        # accidentally match unrelated objects that happen to start with the
        # bare prefix.
        blob = _make_blob(updated=timezone.now())
        with _patch_storage_client(blob) as client_cls:
            call_command(COMMAND, quiet=True)

        list_kwargs = client_cls.return_value.bucket.return_value.list_blobs.call_args.kwargs
        self.assertEqual(list_kwargs.get("prefix"), "referral_data-")
