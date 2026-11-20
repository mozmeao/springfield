# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

QR_CODE_URL_LABEL = "QR Code URL"
QR_CODE_URL_HELP_TEXT = "Enter the full URL, including https://, that you want people to open when they scan the QR code."

# Phones open these directly from a scanned QR code, so they're kept as they are.
NON_WEB_QR_CODE_SCHEMES = ("tel:", "mailto:", "sms:", "smsto:")
# Left untouched so validation rejects them, instead of turning them into https://javascript:...
UNSAFE_SCHEMES = ("javascript:", "data:", "vbscript:", "file:")

INVALID_QR_CODE_URL_MESSAGE = "Enter a web address starting with https://, or a tel:, mailto: or sms: link."

validate_https_url = URLValidator(schemes=["https"], message=INVALID_QR_CODE_URL_MESSAGE)


def normalize_qr_code_url(value):
    value = (value or "").strip()
    lowered = value.lower()
    if not value or lowered.startswith(NON_WEB_QR_CODE_SCHEMES + UNSAFE_SCHEMES):
        return value
    if lowered.startswith("http://"):
        return "https://" + value[len("http://") :]
    if re.match(r"^[a-z][a-z0-9+.-]*://", lowered):
        return value
    return "https://" + value


def validate_qr_code_url(value):
    if value.lower().startswith(NON_WEB_QR_CODE_SCHEMES):
        target = value.split(":", 1)[1]
        if not target or any(character.isspace() for character in target):
            raise ValidationError(INVALID_QR_CODE_URL_MESSAGE)
        return
    validate_https_url(value)
