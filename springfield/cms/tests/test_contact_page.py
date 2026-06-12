# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from unittest.mock import patch

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import Client, RequestFactory
from django.utils.functional import Promise

import pytest
import responses
from wagtail.models import Locale, Site

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
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Us",
        slug="contact",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    assert page.id is not None
    assert page.title == "Contact Us"
    assert page.to_email_address == "test@example.com"
    assert page.redirect_to == thank_you_page


@pytest.mark.parametrize("serving_method", ("serve", "serve_preview"))
def test_contact_page_serve(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
    serving_method: str,
) -> None:
    """Test that ContactPage can be served and renders form field labels."""
    index_page = minimal_site.root_page
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Serve Test",
        slug="contact-serve-test",
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
    index_page = minimal_site.root_page
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
    index_page = minimal_site.root_page
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
    assert "This field is required." in resp.text
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
    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
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


@patch("springfield.cms.models.pages.capture_message")
@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_email_send_failure(
    mock_email_class,
    mock_capture_message,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """When email.send() raises, the form re-renders with an error and Sentry is notified."""
    mock_email_class.return_value.send.side_effect = Exception("SMTP connection refused")

    index_page = minimal_site.root_page
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Email Failure Test",
        slug="email-failure-test",
        form_fields=form_field_variants,
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
    assert "no-store" in resp.get("Cache-Control", "")
    mock_capture_message.assert_called_once()
    assert "Failed to send contact form email" in mock_capture_message.call_args[0][0]


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_missing_required(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that a POST missing required fields re-renders with inline errors."""
    index_page = minimal_site.root_page
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

    # POST with only optional fields so all required fields are missing
    request = rf.post(
        page.relative_url(minimal_site),
        {
            "message": "Hello",
        },
    )

    resp = page.serve(request)
    page_content = resp.text

    assert resp.status_code == 200
    # Error text appears inline multiple times (once per missing required field)
    assert page_content.count("This field is required.") >= 3
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_checkbox_group(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that checkbox group values are collected and joined correctly."""
    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
            "services": ["consulting", "implementation"],
        },
    )

    resp = page.serve(request)

    assert resp.status_code == 302
    call_args = mock_email_class.call_args
    email_body = call_args[0][1]
    assert "consulting, implementation" in email_body


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_empty_submission(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that an empty POST (no fields filled in) is rejected."""
    index_page = minimal_site.root_page
    form_field_variants = get_form_field_variants()
    thank_you_page = _create_thank_you_page(index_page)

    # Use only optional fields so required-field validation doesn't trigger first
    optional_fields = [form_field_variants[8], form_field_variants[10]]  # message (textarea), opt_in (checkbox)

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
    assert "Please fill out the form." in page_content
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_honeypot(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """Test that a POST with the honeypot field filled is rejected."""
    index_page = minimal_site.root_page
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
    assert "There was an error sending your message. Please try again." in page_content
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
    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
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
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    hidden_field = {
        "type": "hidden_field",
        "value": {
            "internal_identifier": "source",
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


def test_contact_page_post_requires_csrf_token(
    minimal_site: Site,  # noqa: F811
) -> None:
    """POST without a valid CSRF token is rejected with 403."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="CSRF Test",
        slug="csrf-test",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    client = Client(enforce_csrf_checks=True)
    resp = client.post(page.full_url, {"full_name": "Bot"})
    assert resp.status_code == 403


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

    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 302
    assert len(responses.calls) == 1
    body = json.loads(responses.calls[0].request.body)
    assert body["first_name"] == "Jane"
    assert body["business_email"] == "jane@acme.com"


@responses.activate
@patch("springfield.cms.models.pages.capture_message")
def test_contact_page_post_basket_api_5xx_rejects_submission(
    mock_capture_message,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """5xx basket API response re-renders the form with an error (no Sentry report)."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=500)

    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
    mock_capture_message.assert_not_called()


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

    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
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
    index_page = minimal_site.root_page
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
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "job_title": "Engineer",
            "business_email": "jane@acme.com",
            "business_phone": "555-1234",
            "company_size": "1 - 10",
            "country": "US",
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "Thanks for reaching out!" in resp.content.decode()


# ============================================================================
# TextAreaFieldBlock Tests
# ============================================================================


def test_textarea_field_renders_correctly(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """TextAreaFieldBlock renders a <textarea> with the correct rows, name, and id."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Textarea Render Test",
        slug="textarea-render-test",
        form_fields=[
            {
                "type": "textarea_field",
                "value": {
                    "internal_identifier": "message",
                    "label": "Message",
                    "required": False,
                    "rows": 6,
                },
                "id": "textarea-field",
            }
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    content = page.serve(request).content.decode()

    assert "<textarea" in content
    assert 'name="message"' in content
    assert 'id="message"' in content
    assert 'rows="6"' in content


def test_textarea_field_required_validates(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """A required TextAreaFieldBlock triggers a validation error when left empty."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Textarea Required Test",
        slug="textarea-required-test",
        form_fields=[
            {
                "type": "textarea_field",
                "value": {
                    "internal_identifier": "message",
                    "label": "Message",
                    "required": True,
                    "rows": 4,
                },
                "id": "textarea-field",
            }
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"message": ""})
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "This field is required." in resp.content.decode()


@patch("springfield.cms.models.pages.EmailMessage")
def test_textarea_field_value_in_email(
    mock_email_class,
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """A submitted textarea value is included in the form email body."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Textarea Email Test",
        slug="textarea-email-test",
        form_fields=[
            {
                "type": "textarea_field",
                "value": {
                    "internal_identifier": "message",
                    "label": "Message",
                    "required": False,
                    "rows": 4,
                },
                "id": "textarea-field",
            }
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {"message": "Hello, I have a question about your product."},
    )
    resp = page.serve(request)

    assert resp.status_code == 302
    email_body = mock_email_class.call_args[0][1]
    assert "Hello, I have a question about your product." in email_body


def test_validate_form_data_per_field_errors(
    minimal_site: Site,  # noqa: F811
) -> None:
    """validate_form_data returns a dict keyed by identifier for missing required fields."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Validate Test",
        slug="validate-test",
        form_fields=get_form_field_variants()[:2],  # first_name and last_name, both required
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    post_data = QueryDict("")  # empty POST
    errors = page.validate_form_data(post_data)

    assert "first_name" in errors
    assert "last_name" in errors
    assert "__all__" not in errors  # no global errors when individual fields are caught
    assert errors["first_name"] == ["This field is required."]


def test_validate_form_data_valid_returns_empty_dict(
    minimal_site: Site,  # noqa: F811
) -> None:
    """validate_form_data returns {} (falsy) for a valid submission."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Validate Valid Test",
        slug="validate-valid-test",
        form_fields=get_form_field_variants()[:2],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    post_data = QueryDict("first_name=Jane&last_name=Doe")
    errors = page.validate_form_data(post_data)

    assert errors == {}


def test_validate_form_data_empty_form(
    minimal_site: Site,  # noqa: F811
) -> None:
    """validate_form_data adds '__all__' error when form has no data at all."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    # Only optional fields so required-field errors don't fire
    optional_fields = [
        {
            "type": "text_field",
            "value": {"internal_identifier": "message", "label": "Message", "required": False},
            "id": "text-field-msg",
        }
    ]
    page = ContactPage(
        title="Validate Empty Test",
        slug="validate-empty-test",
        form_fields=optional_fields,
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    post_data = QueryDict("")
    errors = page.validate_form_data(post_data)

    assert "__all__" in errors
    assert len(errors["__all__"]) == 1


def test_validation_error_strings_are_translatable() -> None:
    """validate_form_data returns lazy strings so errors can be localised at render time."""
    page = ContactPage(to_email_address="test@example.com")
    # An empty submission with no configured fields triggers the "fill out the form" error
    errors = page.validate_form_data({})
    assert errors
    assert isinstance(errors["__all__"][0], Promise), "Validation errors must use gettext_lazy for i18n support"


# ============================================================================
# Form Value Persistence Tests
# ============================================================================


def test_get_form_data_for_context_text_and_checkbox(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """_get_form_data_for_context returns strings for text-like fields, lists for
    checkbox groups, and excludes hidden fields."""
    index_page = minimal_site.root_page
    page = ContactPage(
        title="Form Data Helper Test",
        slug="form-data-helper-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": False},
                "id": "f1",
            },
            {
                "type": "checkbox_group_field",
                "value": {
                    "internal_identifier": "services",
                    "label": "Services",
                    "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
                },
                "id": "f2",
            },
            {
                "type": "hidden_field",
                "value": {"internal_identifier": "source", "label": "Source", "default_value": "web"},
                "id": "f3",
            },
        ],
        to_email_address="test@example.com",
        thank_you_message="<p>Thanks</p>",
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    post_data = QueryDict("name=Jane+Doe&services=a&services=b")
    form_data = page._get_form_data_for_context(post_data)

    assert form_data["name"] == "Jane Doe"
    assert form_data["services"] == ["a", "b"]
    assert "source" not in form_data


def test_get_context_includes_form_data(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """get_context() passes form_data from request into the template context."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Context Form Data Test",
        slug="context-form-data-test",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    request.form_data = {"name": "Jane Doe"}
    context = page.get_context(request)

    assert context["form_data"] == {"name": "Jane Doe"}


def test_get_context_form_data_defaults_to_empty_dict(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """get_context() defaults form_data to {} on GET requests (no form_data on request)."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Context Default Test",
        slug="context-default-test",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    context = page.get_context(request)

    assert context["form_data"] == {}


def test_form_persistence_text_field(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, the submitted text field value is pre-filled."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Text Persistence Test",
        slug="text-persistence-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "company", "label": "Company", "required": False},
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # company filled, full_name empty (required) → validation error → form re-renders
    request = rf.post(page.relative_url(minimal_site), {"company": "Acme Corp"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert 'value="Acme Corp"' in content


def test_form_persistence_email_field(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, the submitted email field value is pre-filled."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Email Persistence Test",
        slug="email-persistence-test",
        form_fields=[
            {
                "type": "email_field",
                "value": {"internal_identifier": "contact_email", "label": "Email", "required": False},
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"contact_email": "jane@example.com"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert 'value="jane@example.com"' in content


def test_form_persistence_phone_field(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, the submitted phone field value is pre-filled."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Phone Persistence Test",
        slug="phone-persistence-test",
        form_fields=[
            {
                "type": "phone_field",
                "value": {"internal_identifier": "phone", "label": "Phone", "required": False},
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"phone": "555-1234"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert 'value="555-1234"' in content


def test_form_persistence_textarea_field(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, the submitted textarea value is pre-filled."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Textarea Persistence Test",
        slug="textarea-persistence-test",
        form_fields=[
            {
                "type": "textarea_field",
                "value": {"internal_identifier": "message", "label": "Message", "required": False, "rows": 4},
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"message": "Hello world"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert ">Hello world<" in content


def test_form_persistence_select_field(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, the previously selected option is marked as selected."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Select Persistence Test",
        slug="select-persistence-test",
        form_fields=[
            {
                "type": "select_field",
                "value": {
                    "internal_identifier": "interest",
                    "label": "Area of Interest",
                    "required": False,
                    "options": [
                        {"value": "privacy", "label": "Privacy"},
                        {"value": "security", "label": "Security"},
                    ],
                },
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"interest": "privacy"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert 'value="privacy" selected' in content
    assert 'value="security" selected' not in content


def test_form_persistence_checkbox_group(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, previously checked checkbox group options are re-checked."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Checkbox Group Persistence Test",
        slug="checkbox-group-persistence-test",
        form_fields=[
            {
                "type": "checkbox_group_field",
                "value": {
                    "internal_identifier": "services",
                    "label": "Services",
                    "options": [
                        {"value": "consulting", "label": "Consulting"},
                        {"value": "support", "label": "Support"},
                        {"value": "training", "label": "Training"},
                    ],
                },
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(
        page.relative_url(minimal_site),
        {"services": ["consulting", "support"]},
    )
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert 'value="consulting" checked' in content
    assert 'value="support" checked' in content
    assert 'value="training" checked' not in content


def test_form_persistence_checkbox_field(
    minimal_site: Site,  # noqa: F811
    rf: RequestFactory,
) -> None:
    """After a validation error, a checked single checkbox remains checked."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Checkbox Persistence Test",
        slug="checkbox-persistence-test",
        form_fields=[
            {
                "type": "checkbox_field",
                "value": {"internal_identifier": "agree", "label": "I agree", "required": False},
                "id": "f1",
            },
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # agree is checked ("on"), full_name is required and missing → validation error
    request = rf.post(page.relative_url(minimal_site), {"agree": "on"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert 'value="on" checked' in content
