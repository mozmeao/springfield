# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Conformance and property tests for the vendored FF1 primitive.

The NIST vectors prove our FF1 is bit-exact with the standard. The Capital One
vectors prove it agrees with an independent reference across radix 32 (which
NIST does not publish), radix 26, all key sizes, and the S-expansion path. The
property test proves encrypt and decrypt are exact inverses over our alphabet.
"""

import random

import pytest

from springfield.firefox.referral.ff1 import (
    MIN_DOMAIN_SIZE,
    ff1_decrypt,
    ff1_encrypt,
)
from springfield.firefox.referral.tests.vectors import (
    NIST_FF1_VECTORS,
    RANDOM_FF1_VECTORS,
)
from springfield.firefox.referral.utils import CROCKFORD_ALPHABET, REFERRAL_ID_LENGTH

ALL_VECTORS = [pytest.param(v, id=v.get("label", v["plaintext"])) for v in NIST_FF1_VECTORS + RANDOM_FF1_VECTORS]

# Any valid 32-byte AES key. The conformance tests use the keys pinned with
# their vectors, so this is only for the tests where the key value is irrelevant.
VALID_KEY = bytes(range(32))


@pytest.mark.parametrize("v", ALL_VECTORS)
def test_ff1_encrypt_matches_reference(v):
    key, tweak = bytes.fromhex(v["key"]), bytes.fromhex(v["tweak"])
    got = ff1_encrypt(key, tweak, v["radix"], v["plaintext"])
    assert got == v["expected"], f"FF1 vector failed: {v['plaintext']} (radix {v['radix']}) -> {got}, expected {v['expected']}"


@pytest.mark.parametrize("v", ALL_VECTORS)
def test_ff1_decrypt_round_trips(v):
    key, tweak = bytes.fromhex(v["key"]), bytes.fromhex(v["tweak"])
    assert ff1_decrypt(key, tweak, v["radix"], v["expected"]) == v["plaintext"]


def test_random_vectors_include_the_s_expansion_path():
    """At least one pinned vector must have d > 16 so generate_s runs its loop.

    For radix 10, n=64: v=32, ceil(v*log2(10))=107, b=ceil(107/8)=14,
    d=4*ceil(14/4)+4=20. That is the radix10_len64 vector. This test locks in
    the coverage so nobody quietly removes the only long-input vector.
    """
    long_vectors = [v for v in RANDOM_FF1_VECTORS if len(v["plaintext"]) >= 60]
    assert long_vectors, "expected a long input vector exercising the S expansion"
    for v in long_vectors:
        n = len(v["plaintext"])
        u = n // 2
        vlen = n - u
        b = -(-((v["radix"] ** vlen - 1).bit_length()) // 8)
        d = 4 * (-(-b // 4)) + 4
        assert d > 16


def test_round_trip_property_over_crockford():
    """Encrypt then decrypt is identity for many random Crockford inputs."""
    rng = random.Random(20260722)
    for _ in range(2000):
        # Hand-picked spread of even and odd input lengths (odd exercises the
        # unequal-half Feistel path), including the production `REFERRAL_ID_LENGTH`.
        n = rng.choice([10, 11, 14, REFERRAL_ID_LENGTH, 19, 24])
        plaintext = "".join(rng.choice(CROCKFORD_ALPHABET) for _ in range(n))
        ciphertext = ff1_encrypt(VALID_KEY, b"", 32, plaintext, alphabet=CROCKFORD_ALPHABET)
        assert len(ciphertext) == n
        assert ff1_decrypt(VALID_KEY, b"", 32, ciphertext, alphabet=CROCKFORD_ALPHABET) == plaintext


def test_character_value_out_of_range_for_radix_is_rejected():
    # 'w' is index 32 in the default base-36 alphabet, out of range for radix 32.
    # This is a distinct branch from a character that is absent from the alphabet.
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", 32, "wwwwwwwwww")


def test_domain_below_minimum_is_rejected():
    # radix 32, n=3 -> 32**3 = 32768, below the 1,000,000 floor.
    assert 32**3 < MIN_DOMAIN_SIZE
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", 32, "ABC", alphabet=CROCKFORD_ALPHABET)
    with pytest.raises(ValueError):
        ff1_decrypt(VALID_KEY, b"", 32, "ABC", alphabet=CROCKFORD_ALPHABET)


def test_radix_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", 1, "0000000000")
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", (1 << 16) + 1, "0000000000")


def test_character_outside_alphabet_is_rejected():
    # 'I' is not in the Crockford alphabet.
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", 32, "IIIIIIIIII", alphabet=CROCKFORD_ALPHABET)


def test_alphabet_shorter_than_radix_is_rejected():
    # Input only uses symbols the short alphabet has, so the encode side would
    # succeed. Without the up-front check the failure surfaces as an
    # `IndexError` on the way back out, once the cipher emits a numeral above 15.
    short = CROCKFORD_ALPHABET[:16]
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", 32, "0123456789", alphabet=short)
    with pytest.raises(ValueError):
        ff1_decrypt(VALID_KEY, b"", 32, "0123456789", alphabet=short)


def test_alphabet_with_duplicate_symbols_is_rejected():
    # A repeated symbol makes the numeral mapping non-invertible, so the round
    # trip would silently return the wrong plaintext rather than raise.
    duplicated = "0" + CROCKFORD_ALPHABET[:31]
    assert len(duplicated) == 32
    with pytest.raises(ValueError):
        ff1_encrypt(VALID_KEY, b"", 32, "0123456789", alphabet=duplicated)
