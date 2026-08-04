# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.firefox.referral.models import FirefoxReferralData

# Ten fixed referral IDs (16-char uppercase Crockford Base32: 0-9, A-Z
# minus I/L/O/U), prefixed TEST. Written directly to the DB as referral
# IDs, bypassing encryption — suitable for local dev only.
# Counts span a range of magnitudes so the Hub template can render every
# tier (single-digit, dozens, hundreds, thousands).
DUMMY_ROWS = [
    ("TEST000000000001", 1),
    ("TEST000000000002", 3),
    ("TESTA1B2C3000000", 5),
    ("TEST00000000000A", 12),
    ("TESTZYXWVT000000", 25),
    ("TESTHJKMNP000000", 87),
    ("TESTQRSTVW000000", 150),
    ("TEST23456X000000", 342),
    ("TEST99999Y000000", 581),
    ("TESTFFFFFF000000", 874),
]

REFERRAL_HUB_URL_TEMPLATE = "http://localhost:8000/en-US/invite/?ref_key={referral_id}"


class Command(BaseCommand):
    help = "Reset TEST-prefixed dummy rows in the FirefoxReferralData table."

    @transaction.atomic
    def handle(self, *args, **options):
        FirefoxReferralData.objects.filter(referral_id__startswith="TEST").delete()
        FirefoxReferralData.objects.bulk_create([FirefoxReferralData(referral_id=rid, install_count=count) for rid, count in DUMMY_ROWS])
        for referral_id, count in DUMMY_ROWS:
            url = REFERRAL_HUB_URL_TEMPLATE.format(referral_id=referral_id)
            self.stdout.write(self.style.SUCCESS(f"{referral_id}, {url}, total successful invites: {count}"))
