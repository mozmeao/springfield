# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Validation and normalization helpers for referral invite codes.

``settings.py`` imports this module while it is still being evaluated (it calls
``validate_invite_code_keyring`` at Django startup), so it must stay safe to
import from there: pure functions only, and nothing that reads
``django.conf.settings`` or touches the app registry. It deliberately never
logs, echoes, or embeds the referral ID or invite code in an exception message,
because those are the plaintext and ciphertext of the FF1 mapping.
"""

from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured

# Crockford base32 alphabet, uppercase canonical: digits 0-9 then A-Z with
# I, L, O and U removed (the visually ambiguous letters). Exactly 32 symbols,
# so it maps one-to-one onto FF1 radix 32. The ORDER of this string is part of
# the invite-code wire format: reordering it silently invalidates every
# outstanding code, so treat it as frozen once shipped.
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CROCKFORD_SYMBOLS = frozenset(CROCKFORD_ALPHABET)

# Crockford's decoding substitutions for the letters its alphabet leaves out.
# A valid code can never contain `O`, `I` or `L`, so a typed one is always a
# misread `0` or `1` and the intent is unambiguous. Applying them only widens
# what decodes: every string that decoded before still decodes to the same
# referral ID. `U` is deliberately not substituted. It is excluded from the
# alphabet to avoid accidental obscenity rather than because it looks like
# something else, so there is no single character a typed `U` stands for.
CROCKFORD_DECODE_SUBSTITUTIONS = str.maketrans({"O": "0", "I": "1", "L": "1"})

# Assumed input format from Firefox: canonical uppercase Crockford base32 referral IDs.
REFERRAL_ID_LENGTH = 16
# 1 version char + the ciphertext (same length as the referral ID).
INVITE_CODE_LENGTH = 17
# Each keyring key is a 256-bit AES key.
KEY_LENGTH_BYTES = 32


def is_canonical_crockford(value: str) -> bool:
    """True if every character of ``value`` is an uppercase Crockford symbol."""
    return all(char in CROCKFORD_SYMBOLS for char in value)


def validate_referral_id(referral_id: str) -> None:
    """Validate a referral ID has the expected length (``REFERRAL_ID_LENGTH``), canonical uppercase Crockford base32.

    Raises ``ValueError`` on any deviation. The referral ID is expected to
    arrive already-canonical from Firefox, so a lowercase, mixed-case, or
    wrong-length value is an upstream bug rather than user input to forgive.
    The offending value is never included in the message (it is plaintext).
    """
    if not isinstance(referral_id, str):
        raise ValueError("referral_id must be a string")
    if len(referral_id) != REFERRAL_ID_LENGTH:
        raise ValueError(f"referral_id must be exactly {REFERRAL_ID_LENGTH} characters")
    if not is_canonical_crockford(referral_id):
        raise ValueError("referral_id must use only uppercase Crockford base32 characters")


def normalize_invite_code(raw: str) -> str:
    """Normalize invite-code input at the case-insensitivity boundary.

    Strips all whitespace (leading, trailing, and internal, to tolerate codes
    copied out of messengers or wrapped emails), uppercases, then applies
    ``CROCKFORD_DECODE_SUBSTITUTIONS``. This is the only place case-folding and
    glyph-folding happen. Every step downstream operates on the canonical
    uppercase form. Non-string input raises ``ValueError`` so the caller can
    surface a "code not recognized" UX rather than a ``TypeError``.
    """
    if not isinstance(raw, str):
        raise ValueError("invite code must be a string")
    return "".join(raw.split()).upper().translate(CROCKFORD_DECODE_SUBSTITUTIONS)


def validate_invite_code(invite_code: str) -> None:
    """Validate a normalized invite code has the expected length (``INVITE_CODE_LENGTH``), Crockford base32.

    Raises ``ValueError`` on non-string input, wrong length, or any
    non-Crockford character. This catches typos and rejects separators
    (hyphens, dots, underscores) that ``normalize_invite_code`` intentionally
    does not strip. The string check is redundant when called straight after
    ``normalize_invite_code``, but this is also a public helper, so it should
    not turn a non-string into a ``TypeError`` on ``len()``.
    """
    if not isinstance(invite_code, str):
        raise ValueError("invite code must be a string")
    if len(invite_code) != INVITE_CODE_LENGTH:
        raise ValueError(f"invite code must be exactly {INVITE_CODE_LENGTH} characters")
    if not is_canonical_crockford(invite_code):
        raise ValueError("invite code must use only Crockford base32 characters")


def validate_invite_code_keyring(keys: Mapping[str, bytes], active_version: str) -> None:
    """Validate the referral-invite-code keyring at Django startup.

    Misconfiguration must fail loudly at boot, not lazily on the first request,
    so ``settings.py`` calls this and any failure raises ``ImproperlyConfigured``
    (Django then refuses to start). Key material is never included in messages.
    """
    if not keys:
        raise ImproperlyConfigured("REFERRAL_INVITE_CODE_KEYS must not be empty")

    if active_version not in keys:
        raise ImproperlyConfigured(f"REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION {active_version!r} is not present in REFERRAL_INVITE_CODE_KEYS")

    for version, key in keys.items():
        if version not in CROCKFORD_SYMBOLS:
            raise ImproperlyConfigured(f"REFERRAL_INVITE_CODE_KEYS version {version!r} must be a single Crockford base32 character")
        if not isinstance(key, (bytes, bytearray)) or len(key) != KEY_LENGTH_BYTES:
            raise ImproperlyConfigured(f"REFERRAL_INVITE_CODE_KEYS[{version!r}] must be exactly {KEY_LENGTH_BYTES} bytes")
