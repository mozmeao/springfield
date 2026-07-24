# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the referral ID <-> invite code adapter."""

import random
from unittest.mock import patch

import pytest

from springfield.firefox.referral.crypto import (
    invite_code_to_referral_id,
    invite_url_for_code,
    referral_id_to_invite_code,
)
from springfield.firefox.referral.tests.vectors import REGRESSION_FIXTURES
from springfield.firefox.referral.utils import CROCKFORD_ALPHABET, is_canonical_crockford

REFERRAL_IDS = [referral_id for referral_id, _, _ in REGRESSION_FIXTURES]

CAPTURE_MESSAGE = "springfield.firefox.referral.crypto.capture_message"


# --- Round trip and regression ---------------------------------------------


@pytest.mark.parametrize("referral_id", REFERRAL_IDS)
def test_round_trip_each_key_version(settings, referral_id):
    for version in ("1", "2"):
        settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = version
        code = referral_id_to_invite_code(referral_id)
        assert code[0] == version
        assert len(code) == 16
        assert invite_code_to_referral_id(code) == referral_id


def test_wrapper_round_trip_property_each_version(settings):
    """N random referral IDs round-trip through the wrapper under each key version."""
    rng = random.Random(20260722)
    for version in ("1", "2"):
        settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = version
        for _ in range(500):
            referral_id = "".join(rng.choice(CROCKFORD_ALPHABET) for _ in range(15))
            code = referral_id_to_invite_code(referral_id)
            assert code[0] == version
            assert invite_code_to_referral_id(code) == referral_id


@pytest.mark.parametrize("referral_id, code_v1, code_v2", REGRESSION_FIXTURES)
def test_regression_fixtures(settings, referral_id, code_v1, code_v2):
    settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = "1"
    assert referral_id_to_invite_code(referral_id) == code_v1
    settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = "2"
    assert referral_id_to_invite_code(referral_id) == code_v2
    # Decoding does not depend on the active version, only on the code's prefix.
    assert invite_code_to_referral_id(code_v1) == referral_id
    assert invite_code_to_referral_id(code_v2) == referral_id


def test_encode_is_deterministic():
    first = referral_id_to_invite_code("A7B9K2M4PXQRSTV")
    second = referral_id_to_invite_code("A7B9K2M4PXQRSTV")
    assert first == second


def test_decoded_id_is_canonical_crockford():
    code = referral_id_to_invite_code("A7B9K2M4PXQRSTV")
    result = invite_code_to_referral_id(code)
    assert len(result) == 15
    assert is_canonical_crockford(result)


def test_active_version_switch(settings):
    referral_id = "A7B9K2M4PXQRSTV"
    settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = "1"
    code_v1 = referral_id_to_invite_code(referral_id)
    settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = "2"
    code_v2 = referral_id_to_invite_code(referral_id)
    assert code_v1[0] == "1" and code_v2[0] == "2"
    assert code_v1 != code_v2
    # Codes minted under the old version still decode after the flip.
    assert invite_code_to_referral_id(code_v1) == referral_id
    assert invite_code_to_referral_id(code_v2) == referral_id


# --- Case and whitespace handling ------------------------------------------


def test_input_is_case_insensitive():
    referral_id = "A7B9K2M4PXQRSTV"
    code = referral_id_to_invite_code(referral_id)
    mixed = "".join(char.lower() if index % 2 else char for index, char in enumerate(code))
    assert invite_code_to_referral_id(code) == referral_id
    assert invite_code_to_referral_id(code.lower()) == referral_id
    assert invite_code_to_referral_id(mixed) == referral_id


def test_input_tolerates_whitespace():
    referral_id = "A7B9K2M4PXQRSTV"
    code = referral_id_to_invite_code(referral_id)
    assert invite_code_to_referral_id(f" {code} ") == referral_id
    assert invite_code_to_referral_id(f"  {code.lower()}  ") == referral_id
    assert invite_code_to_referral_id(f"{code[:5]} {code[5:]}") == referral_id


@pytest.mark.parametrize("bad", ["1-X3ZQ8R5M7NPQRS", "1_X3ZQ8R5M7NPQRS", "1.X3ZQ8R5M7NPQRS"])
def test_rejects_separators(bad):
    with pytest.raises(ValueError):
        invite_code_to_referral_id(bad)


# --- Rejection of malformed input ------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        "SHORT",
        "TOOLONGREF12",  # 12 chars
        "a7b9k2m4px",  # lowercase, not canonical
        "A7B9K2M4PI",  # I not in Crockford alphabet
    ],
)
def test_referral_id_to_invite_code_rejects_malformed(bad):
    with pytest.raises(ValueError):
        referral_id_to_invite_code(bad)


@pytest.mark.parametrize("code", ["", "1", "1X3ZQ8R5M7NPQRS", "1X3ZQ8R5M7NPQRST9"])
def test_decode_rejects_wrong_length(code):
    with pytest.raises(ValueError):
        invite_code_to_referral_id(code)


def test_decode_rejects_unknown_version():
    # Position 0 is a valid Crockford char but not in the test keyring {1, 2}.
    with pytest.raises(ValueError):
        invite_code_to_referral_id("3000000000000000")


@pytest.mark.parametrize("bad", [None, 123, b"1X3ZQ8R5M7N"])
def test_decode_rejects_non_string(bad):
    with pytest.raises(ValueError):
        invite_code_to_referral_id(bad)


# --- Tampering / no integrity check by design ------------------------------


def test_bitflip_ciphertext_char_decodes_to_a_different_id():
    referral_id = "A7B9K2M4PXQRSTV"
    code = referral_id_to_invite_code(referral_id)
    swap = "0" if code[5] != "0" else "1"
    mutated = code[:5] + swap + code[6:]
    assert mutated != code
    result = invite_code_to_referral_id(mutated)
    # No integrity check: it still decodes, to a valid but different referral ID
    # (guaranteed different because FF1 is a bijection).
    assert len(result) == 15 and is_canonical_crockford(result)
    assert result != referral_id


def test_bitflip_version_to_unknown_raises():
    code = referral_id_to_invite_code("A7B9K2M4PXQRSTV")
    mutated = "3" + code[1:]  # version 3 is not in the keyring
    with pytest.raises(ValueError):
        invite_code_to_referral_id(mutated)


# --- URL builder ------------------------------------------------------------


def test_invite_url_for_code():
    assert invite_url_for_code("1X3ZQ8R5M7NPQRST") == "https://www.firefox.com/get-firefox/?invitation=1X3ZQ8R5M7NPQRST"


# --- Sentry observability ---------------------------------------------------


def test_bad_format_is_reported_to_sentry():
    with patch(CAPTURE_MESSAGE) as capture:
        with pytest.raises(ValueError):
            invite_code_to_referral_id("not a valid code")
    assert capture.call_count == 1
    args, kwargs = capture.call_args
    assert kwargs["level"] == "warning"
    assert "bad_format" in args[0]


def test_unknown_version_is_reported_to_sentry():
    with patch(CAPTURE_MESSAGE) as capture:
        with pytest.raises(ValueError):
            invite_code_to_referral_id("3000000000000000")
    assert capture.call_count == 1
    args, kwargs = capture.call_args
    assert kwargs["level"] == "warning"
    assert "version_not_in_keyring" in args[0]


def test_valid_decode_does_not_report_to_sentry():
    code = referral_id_to_invite_code("A7B9K2M4PXQRSTV")
    with patch(CAPTURE_MESSAGE) as capture:
        invite_code_to_referral_id(code)
    assert capture.call_count == 0


def test_non_string_input_is_reported_to_sentry():
    with patch(CAPTURE_MESSAGE) as capture:
        with pytest.raises(ValueError):
            invite_code_to_referral_id(None)
    assert capture.call_count == 1
    args, kwargs = capture.call_args
    assert kwargs["level"] == "warning"
    assert "bad_format" in args[0]
