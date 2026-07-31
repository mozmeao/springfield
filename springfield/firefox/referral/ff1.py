# This code is licensed under the Apache License 2.0 (SPDX: Apache-2.0).
# Text of the Apache License 2.0 can be found in the same directory as this file.
#
# Copyright 2017 Capital One Services, LLC.
# Ported to Python from https://github.com/capitalone/fpe (Go) and modified.

# ruff: noqa: E741, N806
"""Vendored NIST FF1 format-preserving encryption.

Source of truth is NIST SP 800-38G, section 5.1 (Algorithm 7 FF1.Encrypt and
Algorithm 8 FF1.Decrypt), using AES from ``cryptography`` as the underlying
block cipher. Ported primarily from Capital One's Go ``fpe`` and cross-checked
function-by-function against str4d's Rust ``fpe``. Both agree with each other
and with the algorithm below.

  Standard:    https://csrc.nist.gov/pubs/sp/800/38/g/upd1/final
  Primary ref: https://github.com/capitalone/fpe (Go)
  Cross-check: https://github.com/str4d/fpe (Rust)

Naming convention: local variables and helper names mirror the SP 800-38G
symbols (``T`` tweak, ``n`` length, ``radix``, ``A``/``B`` halves, ``P``/``Q``,
``R``, ``S``, ``y``, ``c``, ``u``, ``v``, ``b``, ``d``) rather than being
renamed to Pythonic style, so a reviewer with the spec open can verify the
port line-by-line. That intentionally trips single-letter and uppercase-local
lint rules, hence the module-level ``noqa`` above.

Integer-only radix math: ``b`` is derived from ``(radix ** v - 1).bit_length()``
which is exactly ceil(v * log2(radix)), avoiding floating-point rounding. This
matches str4d's power-of-two handling and is exact for our radix 32 case.

The byte layouts below are fixed by the standard. Changing one changes every
ciphertext, so callers that have already shipped values cannot absorb an edit here.
"""

from collections.abc import Sequence

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Default numeral alphabet for radices up to 36, used by the string-based public
# API so the NIST conformance vectors (radix 10 and radix 36, lowercase) work
# out of the box. Callers over a different alphabet (for example Crockford
# base32) pass their own via the ``alphabet`` keyword.
BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

# FF1 always uses 10 Feistel rounds (SP 800-38G §5.1, Algorithm 7, the "for i from 0 to 9" loop).
NUM_ROUNDS = 10

# SP 800-38G section 5.1 requires radix ** minlen >= 100, and Appendix A
# recommends radix ** minlen >= 1,000,000 (suggested, not required) to limit
# guessing attacks. We enforce the stronger one-million floor. It is a security
# floor, not a wire-format constant.
MIN_DOMAIN_SIZE = 1_000_000

# Radix bounds from the spec: 2 <= radix <= 2**16.
MIN_RADIX = 2
MAX_RADIX = 1 << 16


def _num_radix(numerals: Sequence[int], radix: int) -> int:
    """NUM_radix (SP 800-38G §4.6, Algorithm 1): value of a numeral string, MSB first."""
    x = 0
    for numeral in numerals:
        x = x * radix + numeral
    return x


def _str_m_radix(x: int, radix: int, m: int) -> list[int]:
    """STR^m_radix (SP 800-38G §4.6, Algorithm 3): x as m base-``radix`` numerals, MSB first."""
    out = [0] * m
    for k in range(m - 1, -1, -1):
        out[k] = x % radix
        x //= radix
    return out


def _prf(key: bytes, data: bytes) -> bytes:
    """PRF (SP 800-38G §4.6, Algorithm 6): AES-CBC-MAC with a zero IV, returning the last block.

    ``data`` (which is P || Q) is always a whole number of 16-byte blocks, so a
    single CBC encryption over a zero IV yields the CBC-MAC as its final block.
    """
    encryptor = Cipher(algorithms.AES(key), modes.CBC(b"\x00" * 16)).encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return ciphertext[-16:]


def _generate_s(key: bytes, R: bytes, d: int) -> bytes:
    """Build S (SP 800-38G §5.1, Algorithm 7, step 6 iii).

    S is the first ``d`` bytes of R || CIPH_K(R xor [1]) || CIPH_K(R xor [2]) ...
    where [j] is the 16-byte big-endian encoding of the block counter j. For our
    parameters d <= 16 so only R itself is needed, but the full expansion is
    implemented for conformance with larger domains. A fresh ECB encryptor per
    block keeps the code obviously correct (ECB has no chaining).
    """
    S = bytearray(R)
    j = 1
    while len(S) < d:
        block = bytes(r ^ counter for r, counter in zip(R, j.to_bytes(16, "big")))
        encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        S += encryptor.update(block) + encryptor.finalize()
        j += 1
    return bytes(S[:d])


def _validate_domain(radix: int, n: int) -> None:
    """Enforce the SP 800-38G radix and minimum-domain-size prerequisites."""
    if not (MIN_RADIX <= radix <= MAX_RADIX):
        raise ValueError(f"radix must be between {MIN_RADIX} and {MAX_RADIX}")
    if radix**n < MIN_DOMAIN_SIZE:
        raise ValueError("input domain radix ** n is below the FF1 minimum of 1,000,000")


def _feistel_setup(T: bytes, radix: int, n: int) -> tuple[int, int, int, int, int, bytes]:
    """Compute the round-invariant values u, v, b, d and the P block.

    These depend only on (tweak length, radix, n), not on the plaintext, so
    encrypt and decrypt share them. See SP 800-38G §5.1, Algorithm 7, steps 1, 3, 4, 5.
    """
    t = len(T)

    # Step 1: split point.
    u = n // 2
    v = n - u

    # Step 3: b = ceil(ceil(v * log2(radix)) / 8), computed with integer math.
    # (radix ** v - 1).bit_length() == ceil(v * log2(radix)) exactly.
    v_bits = (radix**v - 1).bit_length()
    b = -(-v_bits // 8)

    # Step 4: d = 4 * ceil(b / 4) + 4.
    d = 4 * (-(-b // 4)) + 4

    # Step 5: the fixed 16-byte P block.
    #   [1,2,1] || radix (3 bytes) || [10] || u mod 256 || n (4 bytes) || t (4 bytes)
    P = bytes([1, 2, 1]) + radix.to_bytes(3, "big") + bytes([10, u % 256]) + n.to_bytes(4, "big") + t.to_bytes(4, "big")

    return t, u, v, b, d, P


def _encrypt_numerals(key: bytes, T: bytes, radix: int, X: Sequence[int]) -> list[int]:
    """FF1.Encrypt over a numeral list (SP 800-38G §5.1, Algorithm 7)."""
    n = len(X)
    _validate_domain(radix, n)
    t, u, v, b, d, P = _feistel_setup(T, radix, n)

    # Step 2: split X into halves.
    A = list(X[:u])
    B = list(X[u:])

    # Step 6: 10 Feistel rounds.
    for i in range(NUM_ROUNDS):
        # Step 6 i: Q = T || [0]^((-t-b-1) mod 16) || [i] || [NUM_radix(B)]^b.
        num_pad = (-t - b - 1) % 16
        Q = T + b"\x00" * num_pad + bytes([i]) + _num_radix(B, radix).to_bytes(b, "big")

        # Step 6 ii and iii: R = PRF(P || Q), then expand to S.
        R = _prf(key, P + Q)
        S = _generate_s(key, R, d)

        # Step 6 iv: y = NUM(S).
        y = int.from_bytes(S, "big")

        # Step 6 v: m alternates between the two half-lengths.
        m = u if i % 2 == 0 else v

        # Step 6 vi and vii: c = (NUM_radix(A) + y) mod radix^m, as m numerals.
        c = (_num_radix(A, radix) + y) % (radix**m)
        C = _str_m_radix(c, radix, m)

        # Step 6 viii and ix: A = B, B = C.
        A = B
        B = C

    # Step 7.
    return A + B


def _decrypt_numerals(key: bytes, T: bytes, radix: int, X: Sequence[int]) -> list[int]:
    """FF1.Decrypt over a numeral list (SP 800-38G §5.1, Algorithm 8)."""
    n = len(X)
    _validate_domain(radix, n)
    t, u, v, b, d, P = _feistel_setup(T, radix, n)

    # Step 2: split X into halves.
    A = list(X[:u])
    B = list(X[u:])

    # Step 6: rounds run in reverse, i from 9 down to 0.
    for i in range(NUM_ROUNDS - 1, -1, -1):
        # Step 6 i: Q uses NUM_radix(A) on decrypt (the mirror of encrypt's B).
        num_pad = (-t - b - 1) % 16
        Q = T + b"\x00" * num_pad + bytes([i]) + _num_radix(A, radix).to_bytes(b, "big")

        # Step 6 ii and iii.
        R = _prf(key, P + Q)
        S = _generate_s(key, R, d)

        # Step 6 iv.
        y = int.from_bytes(S, "big")

        # Step 6 v.
        m = u if i % 2 == 0 else v

        # Step 6 vi and vii: c = (NUM_radix(B) - y) mod radix^m, as m numerals.
        c = (_num_radix(B, radix) - y) % (radix**m)
        C = _str_m_radix(c, radix, m)

        # Step 6 viii and ix: B = A, A = C.
        B = A
        A = C

    # Step 7.
    return A + B


def _validate_alphabet(radix: int, alphabet: str) -> None:
    """Check the alphabet can represent every numeral the cipher can produce.

    FF1 output digits span the full 0..radix-1 range regardless of which digits
    the input used, so an alphabet shorter than the radix would encode fine and
    then fail with an ``IndexError`` on the way back out. Duplicate symbols are
    rejected for the same reason: they make the numeral mapping non-invertible,
    which would silently break the round trip rather than raise.
    """
    if len(alphabet) < radix:
        raise ValueError("alphabet must have at least radix symbols")
    if len(set(alphabet[:radix])) != radix:
        raise ValueError("alphabet must not repeat a symbol within the first radix symbols")


def _string_to_numerals(text: str, radix: int, alphabet: str) -> list[int]:
    """Map each character to its numeral value via ``alphabet``.

    Raises ``ValueError`` if a character is not in the alphabet or its value is
    out of range for the radix. The offending value is not echoed (it may be
    plaintext or ciphertext).
    """
    index = {char: value for value, char in enumerate(alphabet)}
    numerals: list[int] = []
    for char in text:
        value = index.get(char)
        if value is None or value >= radix:
            raise ValueError("input contains a character outside the given alphabet or radix")
        numerals.append(value)
    return numerals


def _numerals_to_string(numerals: Sequence[int], alphabet: str) -> str:
    """Inverse of :func:`_string_to_numerals`."""
    return "".join(alphabet[numeral] for numeral in numerals)


def ff1_encrypt(key: bytes, tweak: bytes, radix: int, plaintext: str, *, alphabet: str = BASE36_ALPHABET) -> str:
    """Encrypt ``plaintext`` with FF1, returning a same-length ciphertext string.

    ``plaintext`` is interpreted over ``alphabet`` (the first ``radix`` symbols
    define the numeral values). Output uses the same alphabet, so the mapping is
    format-preserving.
    """
    _validate_alphabet(radix, alphabet)
    X = _string_to_numerals(plaintext, radix, alphabet)
    Y = _encrypt_numerals(key, tweak, radix, X)
    return _numerals_to_string(Y, alphabet)


def ff1_decrypt(key: bytes, tweak: bytes, radix: int, ciphertext: str, *, alphabet: str = BASE36_ALPHABET) -> str:
    """Decrypt an FF1 ciphertext string, the inverse of :func:`ff1_encrypt`."""
    _validate_alphabet(radix, alphabet)
    X = _string_to_numerals(ciphertext, radix, alphabet)
    Y = _decrypt_numerals(key, tweak, radix, X)
    return _numerals_to_string(Y, alphabet)
