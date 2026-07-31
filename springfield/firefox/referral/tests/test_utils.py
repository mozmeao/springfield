# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for referral input validation and startup keyring validation."""

from django.core.exceptions import ImproperlyConfigured

import pytest

from springfield.firefox.referral.utils import (
    normalize_invite_code,
    validate_invite_code,
    validate_invite_code_keyring,
    validate_referral_id,
)

VALID_KEY = bytes(range(32))


def test_validate_referral_id_accepts_canonical():
    validate_referral_id("A7B9K2M4PXQRSTVW")
    validate_referral_id("0000000000000000")
    validate_referral_id("ZZZZZZZZZZZZZZZZ")


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "SHORT",  # too short
        "AAAAAAAAAAAAAAAAA",  # 17 chars, too long
        "a7b9k2m4pxqrstvw",  # lowercase (16 chars)
        "A7B9K2M4PXQRSTVI",  # I is excluded from Crockford (16 chars)
        "A7B9K2M4PXQRSTVL",  # L is excluded (16 chars)
        "A7B9K2M4PXQRSTVO",  # O is excluded (16 chars)
        "A7B9K2M4PXQRSTVU",  # U is excluded (16 chars)
        "A7B9K2M4PXQRST-W",  # separator (16 chars)
        "A7B9K2M4PXQRST W",  # space (16 chars)
    ],
)
def test_validate_referral_id_rejects(value):
    with pytest.raises(ValueError):
        validate_referral_id(value)


def test_normalize_invite_code_strips_whitespace_and_uppercases():
    assert normalize_invite_code("1X3ZQ8R5M7N") == "1X3ZQ8R5M7N"
    assert normalize_invite_code(" 1X3ZQ8R5M7N ") == "1X3ZQ8R5M7N"
    assert normalize_invite_code("  1x3zq8r5m7n  ") == "1X3ZQ8R5M7N"
    assert normalize_invite_code("1x3zq8 r5m7n") == "1X3ZQ8R5M7N"


def test_normalize_invite_code_rejects_non_string():
    with pytest.raises(ValueError):
        normalize_invite_code(None)


def test_normalize_invite_code_folds_crockford_lookalikes():
    assert normalize_invite_code("O0oIiLl") == "0001111"
    # `U` is excluded from the alphabet to avoid accidental obscenity, not
    # because it resembles another symbol, so it is left alone and then fails
    # validation.
    assert normalize_invite_code("u") == "U"


@pytest.mark.parametrize("value", [None, 123, b"1X3ZQ8R5M7NPQRSTV"], ids=["none", "int", "bytes"])
def test_validate_invite_code_rejects_non_string(value):
    with pytest.raises(ValueError):
        validate_invite_code(value)


def test_validate_invite_code_accepts_17_char_crockford():
    validate_invite_code("1X3ZQ8R5M7NPQRSTV")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1X3ZQ8R5M7NPQRST",  # 16 chars, one short
        "1X3ZQ8R5M7NPQRSTV9",  # 18 chars, one long
        "1X3ZQ8R5M7NPQRSTI",  # I not in alphabet (17 chars)
        "1-X3ZQ8R5M7NPQRST",  # separator (17 chars)
    ],
)
def test_validate_invite_code_rejects(value):
    with pytest.raises(ValueError):
        validate_invite_code(value)


def test_keyring_validation_accepts_valid():
    validate_invite_code_keyring({"1": VALID_KEY}, "1")
    validate_invite_code_keyring({"1": VALID_KEY, "2": VALID_KEY}, "2")


def test_keyring_validation_rejects_empty():
    with pytest.raises(ImproperlyConfigured):
        validate_invite_code_keyring({}, "1")


def test_keyring_validation_rejects_active_version_not_present():
    with pytest.raises(ImproperlyConfigured):
        validate_invite_code_keyring({"1": VALID_KEY}, "2")


@pytest.mark.parametrize("bad_key", [b"", b"\x00" * 16, b"\x00" * 31, b"\x00" * 33, "not-bytes"])
def test_keyring_validation_rejects_wrong_key_length(bad_key):
    with pytest.raises(ImproperlyConfigured):
        validate_invite_code_keyring({"1": bad_key}, "1")


@pytest.mark.parametrize("bad_version", ["", "AB", "I", "L", "O", "U", "a", "-"])
def test_keyring_validation_rejects_bad_version_identifier(bad_version):
    with pytest.raises(ImproperlyConfigured):
        validate_invite_code_keyring({bad_version: VALID_KEY}, bad_version)
