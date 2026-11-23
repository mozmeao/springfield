# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError

import pytest

from springfield.cms.models.pages import FreeFormPage2026, ThanksPage, WhatsNewPage2026
from springfield.cms.models.snippets import BannerSnippet, QRCodeFloatingSnippet, QRCodeSnippet
from springfield.cms.qr_code_urls import QR_CODE_URL_HELP_TEXT, QR_CODE_URL_LABEL, normalize_qr_code_url, validate_qr_code_url


@pytest.mark.parametrize(
    "entered, normalized",
    [
        ("", ""),
        ("   ", ""),
        ("https://www.firefox.com/mobile/", "https://www.firefox.com/mobile/"),
        ("  https://www.firefox.com/  ", "https://www.firefox.com/"),
        ("www.firefox.com/mobile/", "https://www.firefox.com/mobile/"),
        ("firefox.com", "https://firefox.com"),
        ("http://www.firefox.com/", "https://www.firefox.com/"),
        ("HTTP://www.firefox.com/", "https://www.firefox.com/"),
        ("tel:+15551234567", "tel:+15551234567"),
        ("mailto:someone@example.com", "mailto:someone@example.com"),
        ("MAILTO:someone@example.com", "MAILTO:someone@example.com"),
        ("sms:+15551234567", "sms:+15551234567"),
        ("smsto:+15551234567", "smsto:+15551234567"),
        ("ftp://example.com/file", "ftp://example.com/file"),
        ("javascript:alert(1)", "javascript:alert(1)"),
        ("data:text/html,hello", "data:text/html,hello"),
    ],
)
def test_normalize_qr_code_url(entered, normalized):
    assert normalize_qr_code_url(entered) == normalized


@pytest.mark.parametrize(
    "value",
    [
        "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com",
        "tel:+15551234567",
        "mailto:someone@example.com",
        "sms:+15551234567",
        "smsto:+15551234567",
    ],
)
def test_validate_qr_code_url_accepts(value):
    validate_qr_code_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "http://www.firefox.com/",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "https://QR Code content",
        "https://",
        "tel:",
        "mailto:not an address",
    ],
)
def test_validate_qr_code_url_rejects(value):
    with pytest.raises(ValidationError):
        validate_qr_code_url(value)


QR_CODE_URL_MODEL_FIELDS = [
    (BannerSnippet, "qr_code"),
    (QRCodeSnippet, "qr_code"),
    (QRCodeFloatingSnippet, "url"),
    (FreeFormPage2026, "floating_qr_url"),
    (ThanksPage, "floating_qr_url"),
    (WhatsNewPage2026, "floating_qr_url"),
]


@pytest.mark.parametrize("model, field_name", QR_CODE_URL_MODEL_FIELDS)
def test_qr_code_url_model_field_stores_the_normalized_url(model, field_name):
    field = model._meta.get_field(field_name)
    assert field.clean("www.firefox.com/mobile/", model_instance=None) == "https://www.firefox.com/mobile/"
    assert field.clean("", model_instance=None) == ""


@pytest.mark.parametrize("model, field_name", QR_CODE_URL_MODEL_FIELDS)
def test_qr_code_url_model_field_rejects_an_invalid_url(model, field_name):
    with pytest.raises(ValidationError):
        model._meta.get_field(field_name).clean("javascript:alert(1)", model_instance=None)


@pytest.mark.parametrize("model, field_name", QR_CODE_URL_MODEL_FIELDS)
def test_qr_code_url_model_field_uses_the_standard_help_text(model, field_name):
    assert model._meta.get_field(field_name).help_text.startswith(QR_CODE_URL_HELP_TEXT)


@pytest.mark.parametrize("model, field_name", QR_CODE_URL_MODEL_FIELDS[:3])
def test_qr_code_url_snippet_fields_use_the_standard_label(model, field_name):
    assert model._meta.get_field(field_name).verbose_name == QR_CODE_URL_LABEL
