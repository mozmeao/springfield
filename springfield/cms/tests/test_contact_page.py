# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from unittest.mock import patch

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.test import RequestFactory

import pytest
import responses
from wagtail.models import Locale, Site

from springfield.cms.fixtures.base_fixtures import get_test_index_page
from springfield.cms.fixtures.contact_page_fixtures import get_form_field_variants
from springfield.cms.models import SimpleRichTextPage
from springfield.cms.models.pages import ContactPage
from springfield.cms.tests.conftest import minimal_site  # noqa: F401

pytestmark = [
    pytest.mark.django_db,
]


def _create_thank_you_page(index_page):
    """Create a simple thank-you page as the redirect target for contact form tests."""
    thank_you = SimpleRichTextPage(
        title="Thank You",
        slug="thank-you",
        content="<p>Thank you for contacting us.</p>",
    )
    index_page.add_child(instance=thank_you)
    thank_you.save_revision().publish()
    return thank_you


# ============================================================================
# ContactPage Tests
# ============================================================================


def test_contact_page_creation(minimal_site: Site) -> None:  # noqa: F811
    """Test that a ContactPage can be created."""
    index_page = get_test_index_page()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Us",
        slug="contact",
        subheading="Get in touch",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    assert page.id is not None
    assert page.title == "Contact Us"
    assert page.subheading == "Get in touch"
    assert page.to_email_address == "test@example.com"
    assert page.redirect_to == thank_you_page


@pytest.mark.parametrize("serving_method", ("serve", "serve_preview"))
def test_contact_page_serve(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
    serving_method: str,
) -> None:
    """Test that ContactPage can be served and renders form field labels."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Serve Test",
        slug="contact-serve-test",
        subheading="Contact us today",
        form_fields=form_field_variants[:3],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    resp = getattr(page, serving_method)(request, mode_name="irrelevant")
    page_content = resp.text

    assert "Contact Serve Test" in page_content
    assert form_field_variants[0]["value"]["label"] in page_content
    assert form_field_variants[2]["value"]["label"] in page_content


def test_contact_page_get_is_never_cached(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that GET responses include never-cache headers.

    The contact page contains a CSRF token, so it must not be cached by a CDN
    or shared cache — otherwise different users receive the same stale token
    and their form submissions are rejected with 403.
    """
    index_page = get_test_index_page()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Cache Test",
        slug="contact-cache-test",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    resp = page.serve(request)

    cache_control = resp.get("Cache-Control", "")
    assert "no-store" in cache_control


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_errors_is_never_cached(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that POST-with-errors responses also include never-cache headers.

    A re-rendered form (after validation failure) still contains a CSRF token
    and must not be cached.
    """
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Cache Error Test",
        slug="contact-cache-error-test",
        form_fields=form_field_variants,
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {})
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "Please fill in at least one field." in resp.text
    cache_control = resp.get("Cache-Control", "")
    assert "no-store" in cache_control
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_valid(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that a valid POST sends an email and redirects."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Post Test",
        slug="contact-post-test",
        form_fields=form_field_variants,
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "company": "Acme",
            "email": "jane@example.com",
            "phone": "555-1234",
            "interest": "privacy",
            "services": ["consulting", "support"],
        },
    )

    resp = page.serve(request)

    assert resp.status_code == 302
    assert resp["Location"] == thank_you_page.url
    mock_email_class.assert_called_once()
    call_args = mock_email_class.call_args
    assert call_args[0][0] == "Contact form submission: Contact Post Test"
    assert call_args[0][3] == ["recipient@example.com"]
    mock_email_class.return_value.send.assert_called_once()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_missing_required(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that a POST missing required fields re-renders with errors."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Validation Test",
        slug="contact-validation-test",
        form_fields=form_field_variants,
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # POST with missing required fields (full_name, email, interest are required)
    request = rf.post(
        page.relative_url(minimal_site),
        {
            "company": "Acme",
            "phone": "555-1234",
        },
    )

    resp = page.serve(request)
    page_content = resp.text

    assert resp.status_code == 200
    assert "Full Name is required." in page_content
    assert "Email Address is required." in page_content
    assert "Area of Interest is required." in page_content
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_checkbox_group(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that checkbox group values are collected and joined correctly."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Checkbox Test",
        slug="contact-checkbox-test",
        form_fields=form_field_variants,
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "interest": "privacy",
            "services": ["consulting", "implementation"],
        },
    )

    resp = page.serve(request)

    assert resp.status_code == 302
    call_args = mock_email_class.call_args
    email_body = call_args[0][1]
    assert "consulting, implementation" in email_body


def test_contact_page_post_empty_submission(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that an empty POST (no fields filled in) is rejected."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    # Use only optional fields so required-field validation doesn't trigger first
    optional_fields = [form_field_variants[1], form_field_variants[3]]  # company, phone

    page = ContactPage(
        title="Contact Empty Test",
        slug="contact-empty-test",
        form_fields=optional_fields,
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {})
    resp = page.serve(request)
    page_content = resp.text

    assert resp.status_code == 200
    assert "Please fill in at least one field." in page_content


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_honeypot(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that a POST with the honeypot field filled is rejected."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Honeypot Test",
        slug="contact-honeypot-test",
        form_fields=form_field_variants,
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Bot Name",
            "email": "bot@example.com",
            "interest": "privacy",
            "office_fax": "I am a bot",
        },
    )

    resp = page.serve(request)
    page_content = resp.text

    assert resp.status_code == 200
    assert "Form submission failed." in page_content
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_valid_redirects_to_localised_page(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that a valid POST redirects to the locale-appropriate version of redirect_to.

    The CMS editor configures redirect_to pointing at the en-US thank-you page.
    A user whose active locale is fr should be redirected to the fr translation
    of that page, not the en-US original.
    """
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    en_us_thank_you = _create_thank_you_page(index_page)

    fr_locale = Locale.objects.get(language_code="fr")
    fr_thank_you = en_us_thank_you.copy_for_translation(fr_locale, copy_parents=True)
    fr_thank_you.save_revision().publish()

    page = ContactPage(
        title="Contact Locale Test",
        slug="contact-locale-test",
        form_fields=form_field_variants,
        to_email_address="recipient@example.com",
        redirect_to=en_us_thank_you,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "interest": "privacy",
        },
    )
    # Simulate an active fr locale for this request
    request.LANGUAGE_CODE = "fr"
    with patch("wagtail.models.i18n.Locale.get_active", return_value=fr_locale):
        resp = page.serve(request)

    assert resp.status_code == 302
    assert resp["Location"] == fr_thank_you.url


def test_contact_page_hidden_field_not_visible(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """HiddenFieldBlock renders as <input type='hidden'> with the default value."""
    index_page = get_test_index_page()
    thank_you_page = _create_thank_you_page(index_page)

    hidden_field = {
        "type": "hidden_field",
        "value": {
            "settings": {"internal_identifier": "source"},
            "default_value": "contact-page",
        },
        "id": "hidden-field",
    }

    page = ContactPage(
        title="Hidden Field Test",
        slug="hidden-field-test",
        form_fields=[hidden_field],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    resp = page.serve(request)
    content = resp.content.decode()

    assert 'type="hidden"' in content
    assert 'name="source"' in content
    assert 'value="contact-page"' in content


# ============================================================================
# ContactPage.clean() Validation Tests
# ============================================================================


def test_contact_page_clean_requires_email_or_basket(
    minimal_site: Site,  # noqa: F811
) -> None:
    """ContactPage.clean() raises if both to_email_address and basket_api_path are blank."""
    page = ContactPage(
        title="Clean Test",
        slug="clean-test",
        to_email_address="",
        basket_api_path="",
        thank_you_message="<p>Thank you!</p>",
    )
    with pytest.raises(ValidationError):
        page.clean()


def test_contact_page_clean_rejects_both_email_and_basket(
    minimal_site: Site,  # noqa: F811
) -> None:
    """ContactPage.clean() raises if both to_email_address and basket_api_path are set."""
    page = ContactPage(
        title="Clean Both Test",
        slug="clean-both-test",
        to_email_address="test@example.com",
        basket_api_path="/news/subscribe/",
        thank_you_message="<p>Thank you!</p>",
    )
    with pytest.raises(ValidationError):
        page.clean()


def test_contact_page_clean_requires_redirect_or_thank_you(
    minimal_site: Site,  # noqa: F811
) -> None:
    """ContactPage.clean() raises if both redirect_to and thank_you_message are blank."""
    page = ContactPage(
        title="Clean Redirect Test",
        slug="clean-redirect-test",
        to_email_address="test@example.com",
        redirect_to=None,
        thank_you_message="",
    )
    with pytest.raises(ValidationError):
        page.clean()


def test_contact_page_clean_validates_basket_path_format(
    minimal_site: Site,  # noqa: F811
) -> None:
    """ContactPage.clean() raises if basket_api_path doesn't start with /."""
    page = ContactPage(
        title="Basket Path Test",
        slug="basket-path-test",
        basket_api_path="news/subscribe/",
        thank_you_message="<p>Thank you!</p>",
    )
    with pytest.raises(ValidationError):
        page.clean()


def test_contact_page_clean_rejects_full_url_as_basket_path(
    minimal_site: Site,  # noqa: F811
) -> None:
    """ContactPage.clean() raises if basket_api_path looks like a full URL."""
    page = ContactPage(
        title="Basket URL Test",
        slug="basket-url-test",
        basket_api_path="https://basket.mozilla.org/news/subscribe/",
        thank_you_message="<p>Thank you!</p>",
    )
    with pytest.raises(ValidationError):
        page.clean()


# ============================================================================
# Basket API Tests
# ============================================================================


@responses.activate
def test_contact_page_post_basket_api_called(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Valid POST with basket_api_path calls the basket URL with the correct JSON body."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=200)

    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Basket API Test",
        slug="basket-api-test",
        form_fields=form_field_variants,
        basket_api_path="/news/subscribe/",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "interest": "privacy",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 302
    assert len(responses.calls) == 1
    body = json.loads(responses.calls[0].request.body)
    assert body["full_name"] == "Jane Doe"
    assert body["email"] == "jane@example.com"


@responses.activate
def test_contact_page_post_basket_api_5xx_rejects_submission(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """5xx basket API response re-renders the form with an error (no Sentry report)."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=500)

    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Basket 5xx Test",
        slug="basket-5xx-test",
        form_fields=form_field_variants,
        basket_api_path="/news/subscribe/",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "interest": "privacy",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "Form submission failed." in resp.content.decode()


@responses.activate
@patch("springfield.cms.models.pages.capture_message")
def test_contact_page_post_basket_api_4xx_reports_to_sentry(
    mock_capture_message,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """4xx basket API response re-renders with an error AND sends a Sentry event."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=400)

    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Basket 4xx Test",
        slug="basket-4xx-test",
        form_fields=form_field_variants,
        basket_api_path="/news/subscribe/",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "interest": "privacy",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "Form submission failed." in resp.content.decode()
    mock_capture_message.assert_called_once()
    call_args = mock_capture_message.call_args
    assert "400" in call_args[0][0]


# ============================================================================
# thank_you_message Tests
# ============================================================================


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_valid_shows_thank_you_message(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """When thank_you_message is set and no redirect_to, valid POST re-renders
    with the thank you content instead of the form."""
    index_page = get_test_index_page()
    form_field_variants = get_form_field_variants()

    page = ContactPage(
        title="Thank You Message Test",
        slug="thank-you-message-test",
        form_fields=form_field_variants,
        to_email_address="test@example.com",
        thank_you_message="<p>Thanks for reaching out!</p>",
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "interest": "privacy",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "Thanks for reaching out!" in resp.content.decode()
