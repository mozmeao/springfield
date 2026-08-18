# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Referral ID <-> invite code mapping.

Thin adapter over the vendored FF1 primitive (:mod:`ff1`). Callers use these
three functions and never touch FF1 directly. The mapping is deterministic,
reversible, and format-preserving. Different referral IDs can never collide to
the same invite code because FF1 is a permutation.

Nothing here does database access or logs secrets. The only thing ever logged
is the single-character key version (safe to log), and only on a decode failure.
"""

from django.conf import settings

from sentry_sdk import capture_message, new_scope

from springfield.firefox.referral import ff1
from springfield.firefox.referral.utils import (
    CROCKFORD_ALPHABET,
    normalize_invite_code,
    validate_invite_code,
    validate_referral_id,
)

# Crockford base32 is radix 32.
RADIX = 32

# FF1 requires a tweak input. We intentionally pass empty bytes: the key is
# dedicated to referral-invite-code encryption and forbidden from other uses,
# so there is no other context to separate from and a tweak would add nothing.
# This is a frozen wire-format constant. See the spec section "FF1 tweak".
FF1_TWEAK = b""


def referral_id_to_invite_code(referral_id: str) -> str:
    """Turn a referral ID into an invite code (version char + FF1 ciphertext).

    The invite code is the active key version character followed by the FF1
    ciphertext of the referral ID. Deterministic for a given active key,
    canonical uppercase, and a pure function (no I/O). Raises `ValueError` if
    the referral ID is not canonical uppercase Crockford base32.
    """
    validate_referral_id(referral_id)

    version = settings.REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION
    key = settings.REFERRAL_INVITE_CODE_KEYS[version]

    ciphertext = ff1.ff1_encrypt(key, FF1_TWEAK, RADIX, referral_id, alphabet=CROCKFORD_ALPHABET)
    return f"{version}{ciphertext}"


def invite_url_for_code(invite_code: str) -> str:
    """Build the shareable download URL for an invite code.

    Kept as a function so the URL structure lives in exactly one place. The
    Crockford alphabet is URL-safe, so no percent-encoding is needed. Raises
    `ValueError` on a malformed invite code.
    """
    validate_invite_code(invite_code)
    return f"{settings.CANONICAL_URL}/get-firefox/?invitation={invite_code}"


def invite_code_to_referral_id(invite_code: str) -> str:
    """Reverse an invite code back to its referral ID.

    Input is treated case-insensitively and tolerates surrounding whitespace.
    Round-trips exactly with :func:`referral_id_to_invite_code`. There is no
    integrity check by design: any well-formed code with a known key version
    decrypts to some referral ID, so the caller must decide whether that ID
    corresponds to a real referrer. Raises `ValueError` on bad format or an
    unknown key version, and reports each rejection to Sentry at warning level.
    """
    try:
        normalized = normalize_invite_code(invite_code)
        validate_invite_code(normalized)
    except ValueError:
        _report_decode_failure("bad_format")
        raise

    # Position 0 is the key version, the rest is the ciphertext.
    version = normalized[0]
    ciphertext = normalized[1:]

    keys = settings.REFERRAL_INVITE_CODE_KEYS
    if version not in keys:
        _report_decode_failure("version_not_in_keyring", version=version)
        raise ValueError("invite code key version is not in the keyring")

    key = keys[version]
    return ff1.ff1_decrypt(key, FF1_TWEAK, RADIX, ciphertext, alphabet=CROCKFORD_ALPHABET)


def _report_decode_failure(category: str, *, version: str | None = None) -> None:
    """Report a decode rejection to Sentry at warning level.

    Fingerprinted by category so Sentry dedupes typo floods and a spike in
    either category (`bad_format` or `version_not_in_keyring`) stands out.
    Only the key version character is attached, never the code or referral ID.
    """
    with new_scope() as scope:
        scope.set_tag("referral_invite_code_error", category)
        scope.fingerprint = ["referral-invite-code-decode", category]
        if version is not None:
            scope.set_extra("key_version", version)
        capture_message(f"invite_code_to_referral_id rejected input: {category}", level="warning")
