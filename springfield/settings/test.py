# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from springfield.settings import *  # noqa

# this bypasses bcrypt to speed up test fixtures
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

logging.root.setLevel(logging.WARNING)

# Fixed two-version referral invite-code keyring so the crypto tests are
# deterministic and can exercise rotation and per-version regression fixtures.
# Version "1" reuses the shared local/CI dev key from .env-dist. These are not
# production values. Version identifiers are single Crockford base32 characters.
REFERRAL_INVITE_CODE_KEYS = {
    "1": bytes.fromhex("abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"),
    "2": bytes.fromhex("0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0"),
}
REFERRAL_INVITE_CODE_ACTIVE_KEY_VERSION = "1"
