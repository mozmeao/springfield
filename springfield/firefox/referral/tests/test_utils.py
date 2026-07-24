# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.firefox.referral.utils import (
    REFERRAL_HUB_CODE_LENGTH,
    REFERRAL_INVITATION_CODE_LENGTH,
    ReferralCodeError,
    check_referral_code,
)

# A 16-char code composed entirely of characters that are in the Crockford
# Base 32 alphabet, chosen to touch a mix of digits and letters (including
# ones near the excluded I/L/O/U slots).
VALID_HUB_CODE = "0123456789ABCDEF"
assert len(VALID_HUB_CODE) == REFERRAL_HUB_CODE_LENGTH

VALID_INVITATION_CODE = "0123456789ABCDEFG"
assert len(VALID_INVITATION_CODE) == REFERRAL_INVITATION_CODE_LENGTH


@pytest.mark.parametrize(
    "code, expected_length",
    [
        (VALID_HUB_CODE, REFERRAL_HUB_CODE_LENGTH),
        (VALID_INVITATION_CODE, REFERRAL_INVITATION_CODE_LENGTH),
        # Every non-excluded letter, exercising the alphabet boundaries.
        ("ABCDEFGHJKMNPQRS", REFERRAL_HUB_CODE_LENGTH),
        ("TVWXYZ0123456789", REFERRAL_HUB_CODE_LENGTH),
    ],
)
def test_valid_codes_return_none(code, expected_length):
    assert check_referral_code(code, expected_length) is None


@pytest.mark.parametrize("code", [None, ""])
def test_missing_code(code):
    assert check_referral_code(code, REFERRAL_HUB_CODE_LENGTH) is ReferralCodeError.MISSING


@pytest.mark.parametrize(
    "code",
    [
        "ABCDEFGHJKMNPQR",  # 15, one short
        "ABCDEFGHJKMNPQRST",  # 17, one long
        "A",
        "ABCDEFGHJKMNPQRSABCDEFGHJKMNPQRS",  # 32
    ],
)
def test_wrong_length(code):
    assert check_referral_code(code, REFERRAL_HUB_CODE_LENGTH) is ReferralCodeError.WRONG_LENGTH


@pytest.mark.parametrize(
    "code",
    [
        "abcdefghjkmnpqrs",  # all lowercase, right length, otherwise-valid chars
        "ABCDEFGHJKMNPQRs",  # single trailing lowercase
        "aBCDEFGHJKMNPQRS",  # single leading lowercase
    ],
)
def test_wrong_case(code):
    assert check_referral_code(code, REFERRAL_HUB_CODE_LENGTH) is ReferralCodeError.WRONG_CASE


@pytest.mark.parametrize(
    "code",
    [
        "ABCDEFGHJKMNPQR-",  # hyphen
        "ABCDEFGHJKMNPQ RS"[:16],  # space
        "ABCDEFGHJKMNPQR.",  # period
        "IABCDEFGHJKMNPQR",  # I is excluded
        "LABCDEFGHJKMNPQR",  # L is excluded
        "OABCDEFGHJKMNPQR",  # O is excluded
        "UABCDEFGHJKMNPQR",  # U is excluded
    ],
)
def test_invalid_character(code):
    assert len(code) == REFERRAL_HUB_CODE_LENGTH
    assert code == code.upper()
    assert check_referral_code(code, REFERRAL_HUB_CODE_LENGTH) is ReferralCodeError.INVALID_CHARACTER


def test_check_ordering_case_beats_alphabet():
    # A code that is both lowercase AND contains an out-of-alphabet character
    # should report WRONG_CASE, since that check runs first.
    assert check_referral_code("abcdefghjkmnpqr-", REFERRAL_HUB_CODE_LENGTH) is ReferralCodeError.WRONG_CASE


def test_check_ordering_length_beats_case():
    # A short lowercase code should report WRONG_LENGTH, not WRONG_CASE.
    assert check_referral_code("abc", REFERRAL_HUB_CODE_LENGTH) is ReferralCodeError.WRONG_LENGTH
