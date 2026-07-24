# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from enum import Enum

# Crockford Base 32 alphabet: 0-9 plus A-Z minus I, L, O, U.
CROCKFORD_BASE32_ALPHABET = frozenset("0123456789ABCDEFGHJKMNPQRSTVWXYZ")

REFERRAL_HUB_CODE_LENGTH = 16
REFERRAL_INVITATION_CODE_LENGTH = 17


class ReferralCodeError(str, Enum):
    MISSING = "missing"
    WRONG_LENGTH = "wrong_length"
    WRONG_CASE = "wrong_case"
    INVALID_CHARACTER = "invalid_character"


def check_referral_code(code: str | None, expected_length: int) -> ReferralCodeError | None:
    """Return None if `code` looks plausible, else a ReferralCodeError describing the failure.

    The ordering (missing, then length, then case, then alphabet) is deliberate: it lets the
    Sentry signal distinguish "someone typed the whole thing lowercase" from "someone stuck a
    hyphen in", which is useful for spotting scanning patterns.
    """
    if not code:
        return ReferralCodeError.MISSING
    if len(code) != expected_length:
        return ReferralCodeError.WRONG_LENGTH
    if code != code.upper():
        return ReferralCodeError.WRONG_CASE
    if not set(code).issubset(CROCKFORD_BASE32_ALPHABET):
        return ReferralCodeError.INVALID_CHARACTER
    return None
