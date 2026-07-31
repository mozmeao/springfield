# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Regenerate the pinned REGRESSION_FIXTURES for the referral crypto tests.

Run under the test keyring so the output matches the pinned fixtures (the test
settings define the two-version keyring the fixtures are generated against):

    DJANGO_SETTINGS_MODULE=springfield.settings.test python manage.py regenerate_referral_fixtures

Then paste the printed block into
`springfield/firefox/referral/tests/vectors.py` (REGRESSION_FIXTURES).

The values are drift anchors, not independent vectors: they are produced by the
real crypto under the test keyring and round-trip-verified here before printing.
The referral IDs are derived from REFERRAL_ID_LENGTH, so this self-adjusts if the
referral-ID length ever changes.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from springfield.firefox.referral import crypto
from springfield.firefox.referral.utils import CROCKFORD_ALPHABET, REFERRAL_ID_LENGTH


def representative_referral_ids(length: int) -> list[str]:
    """Deterministic, representative referral IDs of exactly `length` chars.

    All are built from the Crockford alphabet so they are always valid, and the
    set spans all-min, all-max, sequential (both directions), a mixed value, and
    two `TEST`-prefixed values.
    """
    sequential = CROCKFORD_ALPHABET * (length // len(CROCKFORD_ALPHABET) + 1)
    mixed = "A7B9K2M4PXQRSTVWXYZ23456789BCDFGH" * (length // 33 + 1)
    return [
        "0" * length,
        "Z" * length,
        "F" * length,
        sequential[:length],
        sequential[::-1][:length],
        mixed[:length],
        ("TEST" + "0" * length)[:length],
        ("TEST" + "Z" * length)[:length],
    ]


class Command(BaseCommand):
    help = "Print the REGRESSION_FIXTURES block for the referral crypto tests."

    def handle(self, *args, **options):
        versions = sorted(settings.REFERRAL_INVITE_CODE_KEYS)
        original_version = settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION

        lines = ["REGRESSION_FIXTURES = ["]
        try:
            for referral_id in representative_referral_ids(REFERRAL_ID_LENGTH):
                codes = []
                for version in versions:
                    settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = version
                    code = crypto.referral_id_to_invite_code(referral_id)
                    if crypto.invite_code_to_referral_id(code) != referral_id:
                        raise AssertionError(f"round-trip failed under version {version}")
                    codes.append(code)
                quoted = ", ".join(f'"{value}"' for value in [referral_id, *codes])
                lines.append(f"    ({quoted}),")
        finally:
            settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = original_version
        lines.append("]")

        self.stdout.write("\n".join(lines))
