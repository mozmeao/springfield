# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from springfield.firefox.referral.utils import validate_invite_code_keyring
from springfield.settings import *  # noqa

# this bypasses bcrypt to speed up test fixtures
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

logging.root.setLevel(logging.WARNING)

# Fixed two-version referral invite-code keyring so the crypto tests are
# deterministic and can exercise rotation and per-version regression fixtures.
# Pinned here rather than sourced from the environment, because
# `REGRESSION_FIXTURES` are ciphertexts under these exact keys. Deriving
# version `1` from `REFERRAL_INVITE_CODE_KEY_V1` would break those fixtures
# for anyone running with their own key. These are not production values.
# Version identifiers are single Crockford base32 characters.
REFERRAL_INVITE_CODE_KEYS = {
    "1": bytes.fromhex("abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"),
    "2": bytes.fromhex("0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0"),
}
REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = "1"

# This keyring replaces the one `base.py` already validated, so run the same
# check on it. A bad edit above then fails as `ImproperlyConfigured` rather
# than as an opaque crypto test failure.
validate_invite_code_keyring(REFERRAL_INVITE_CODE_KEYS, REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION)
