# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max

from google.cloud import storage
from google.cloud.exceptions import NotFound

from springfield.base.waffle import switch
from springfield.firefox.referral.crypto import invite_code_to_referral_id
from springfield.firefox.referral.models import FirefoxReferralData
from springfield.utils.management.decorators import alert_sentry_on_exception


def _iter_rows(reader):
    """Yield (invite_code, count_str) tuples from a csv.reader.

    The CSV has no header row. Skips blank lines and rows without exactly
    two columns (surfaces schema drift rather than silently ignoring extras).
    """
    for row in reader:
        if not row:
            continue
        if len(row) != 2:
            continue
        yield row[0], row[1]


def _decrypt_rows(rows):
    """Decrypt invite codes to referral IDs, skipping rows that fail.

    Yields (referral_id, count_str) tuples. An invite code that fails
    decryption (bad format, unknown key version) yields (None, count_str)
    so _validated_iter counts it as a skipped row rather than aborting
    the whole refresh. Sentry is notified by invite_code_to_referral_id
    itself on decryption failure.
    """
    for invite_code, count in rows:
        try:
            referral_id = invite_code_to_referral_id(invite_code)
        except Exception:
            yield None, count
            continue
        yield referral_id, count


@alert_sentry_on_exception
class Command(BaseCommand):
    help = (
        "Refreshes the FirefoxReferralData table from the newest CSV published "
        "to GCS by Data Engineering. Data Eng writes one CSV per publish, named "
        "'{REFERRAL_DATA_GCS_OBJECT_NAME_PREFIX}-YYYY-MM-DD.csv'; the command "
        "lists that prefix, picks the lex-newest name (chronologically latest "
        "for that date format), and imports it. Expected CSV shape (no header):\n"
        "    1ABCDEFGHJKMNPQST,42\n"
        "Each invite code is decrypted to a referral ID before storage. "
        "Skips when the newest blob has not been updated since the last "
        "successful import, unless --force is passed."
    )

    def add_arguments(self, parser):
        parser.add_argument("-q", "--quiet", action="store_true", default=False)
        parser.add_argument("-f", "--force", action="store_true", default=False)

    def _log(self, msg):
        if not self.quiet:
            self.stdout.write(msg)

    def handle(self, *args, **options):
        self.quiet = options["quiet"]
        force = options["force"]

        if not switch("ENABLE_REFERRAL_IMPORT"):
            self._log("ENABLE_REFERRAL_IMPORT switch is off; skipping referral data import")
            return

        bucket_name = settings.REFERRAL_DATA_GCS_BUCKET
        prefix = settings.REFERRAL_DATA_GCS_OBJECT_NAME_PREFIX
        if not bucket_name:
            self._log("REFERRAL_DATA_GCS_BUCKET not configured; skipping referral data import")
            return

        client = storage.Client()
        # Trailing '-' matches the publish-name shape ("{prefix}-YYYY-...") and
        # avoids matching unrelated objects whose names happen to start with
        # the prefix but continue with different characters.
        list_prefix = f"{prefix}-"
        try:
            blobs = list(client.bucket(bucket_name).list_blobs(prefix=list_prefix))
        except NotFound:
            self._log(f"Bucket {bucket_name!r} not found; skipping referral data import")
            return

        if not blobs:
            self._log(f"No referral data files matching prefix {list_prefix!r} in bucket {bucket_name!r}; skipping")
            return

        # Data Eng's timestamp format sorts chronologically as ASCII, so the
        # lex-max name is the newest publish.
        blob = max(blobs, key=lambda b: b.name)

        db_max = FirefoxReferralData.objects.aggregate(m=Max("last_refreshed_at"))["m"]
        if db_max and blob.updated <= db_max and not force:
            self._log(f"Newest referral data file {blob.name!r} has no updates since last import; skipping")
            return

        with blob.open("r") as fh:
            reader = csv.reader(fh)
            loaded, skipped = FirefoxReferralData.objects.refresh(_decrypt_rows(_iter_rows(reader)))

        self._log(f"Loaded {loaded} referral rows from {blob.name!r} ({skipped} skipped)")
