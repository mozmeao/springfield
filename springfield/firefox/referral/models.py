# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models, transaction

REFRESH_BATCH_SIZE = 5000


class FirefoxReferralDataManager(models.Manager):
    def refresh(self, rows):
        """Replace all referral data with a fresh snapshot.

        `rows` is an iterable of (referral_id, install_count) tuples, where
        install_count may be an int or a string coercible to a non-negative int.
        Malformed rows (blank referral_id, non-integer or negative install_count)
        are skipped. Returns a (loaded, skipped) tuple.

        Streams input in batches of REFRESH_BATCH_SIZE, so peak memory stays
        bounded regardless of the total row count. At the tens-of-millions
        ceiling, materialising the whole model-instance list would OOM.

        Refuses to wipe the table if the input yields zero valid rows: an
        empty or all-malformed snapshot from Data Engineering is treated as
        a bad publish, not as a "delete everything" instruction. In that
        case the table is left untouched and ValueError is raised so the
        caller (and Sentry) sees the anomaly.

        Invariant: nothing else in the codebase should write to
        `last_refreshed_at` on this model. The `update_referral_data` command's
        skip-when-unchanged check relies on MAX(last_refreshed_at) being the
        wall-clock time of the last successful full-replace. If partial updates
        are ever introduced, that check has to be revisited.
        """
        loaded = 0
        skipped = 0
        buf = []
        validated = self._validated_iter(rows)

        # Peek: pull from the iterator until we find at least one valid row.
        # Only after we have one do we enter the destructive path.
        for is_valid, referral_id, count in validated:
            if not is_valid:
                skipped += 1
                continue
            buf.append(self.model(referral_id=referral_id, install_count=count))
            break
        else:
            raise ValueError(f"FirefoxReferralData refresh received no valid rows ({skipped} rows skipped); refusing to wipe existing data")

        with transaction.atomic(using=self.db):
            self.all().delete()
            for is_valid, referral_id, count in validated:
                if not is_valid:
                    skipped += 1
                    continue
                buf.append(self.model(referral_id=referral_id, install_count=count))
                if len(buf) >= REFRESH_BATCH_SIZE:
                    self.bulk_create(buf)
                    loaded += len(buf)
                    buf = []
            if buf:
                self.bulk_create(buf)
                loaded += len(buf)

        return loaded, skipped

    def _validated_iter(self, rows):
        """Yield (is_valid, referral_id, count) triples from raw input tuples.

        Rejects rows that would violate DB constraints on `bulk_create` (length
        overflow on referral_id, integer overflow on install_count). Catching
        these BEFORE the atomic delete runs prevents a retry-storm where a
        single bad row keeps rolling back the whole refresh on every tick.
        """
        max_len = self.model._meta.get_field("referral_id").max_length
        # Postgres integer upper bound (PositiveIntegerField uses a 32-bit int).
        max_count = 2**31 - 1
        for referral_id, install_count in rows:
            referral_id = (referral_id or "").strip()
            try:
                count = int(install_count)
            except (TypeError, ValueError):
                yield False, None, None
                continue
            if not referral_id or count < 0 or count > max_count:
                yield False, None, None
                continue
            if len(referral_id) > max_len:
                yield False, None, None
                continue
            yield True, referral_id, count


class FirefoxReferralData(models.Model):
    referral_id = models.CharField(max_length=16, unique=True)
    install_count = models.PositiveIntegerField(default=0)
    last_refreshed_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = FirefoxReferralDataManager()

    class Meta:
        app_label = "firefox"

    def __str__(self):
        return f"{self.referral_id}: {self.install_count} installs"
