# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.firefox.referral.models import FirefoxReferralData

# Ten fixed (referral_id, install_count) pairs. Referral IDs are 10-char
# uppercase Crockford Base 32 (0-9, A-Z minus I/L/O/U), prefixed TEST.
# Counts span a range of magnitudes so the Hub template can render every
# tier (single-digit, dozens, hundreds, thousands).
DUMMY_ROWS = [
    ("TEST000001", 0),
    ("TEST000002", 1),
    ("TESTA1B2C3", 5),
    ("TEST00000A", 12),
    ("TESTZYXWVT", 25),
    ("TESTHJKMNP", 87),
    ("TESTQRSTVW", 150),
    ("TEST23456X", 342),
    ("TEST99999Y", 999),
    ("TESTFFFFFF", 4321),
]

REFERRAL_HUB_URL_TEMPLATE = "http://localhost:8000/en-US/invite/?code={referral_id}"


class Command(BaseCommand):
    help = "Reset TEST-prefixed dummy rows in the FirefoxReferralData table."

    @transaction.atomic
    def handle(self, *args, **options):
        FirefoxReferralData.objects.filter(referral_id__startswith="TEST").delete()
        FirefoxReferralData.objects.bulk_create([FirefoxReferralData(referral_id=rid, install_count=count) for rid, count in DUMMY_ROWS])
        for referral_id, count in DUMMY_ROWS:
            url = REFERRAL_HUB_URL_TEMPLATE.format(referral_id=referral_id)
            self.stdout.write(self.style.SUCCESS(f"{referral_id}, {url}, total successful invites: {count}"))
