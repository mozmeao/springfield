# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from unittest.mock import patch

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory

import pytest
import responses
from wagtail.models import Locale, Site

from springfield.cms.fixtures.contact_page_fixtures import get_form_field_variants
from springfield.cms.models import SimpleRichTextPage
from springfield.cms.models.pages import ContactPage

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


# Page creation and serving


def test_contact_page_creation(minimal_site: Site) -> None:
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


def test_contact_page_clean_requires_email_or_basket(
    minimal_site: Site,
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
    minimal_site: Site,
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
    minimal_site: Site,
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
    minimal_site: Site,
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
    minimal_site: Site,
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


@pytest.mark.parametrize("serving_method", ("serve", "serve_preview"))
def test_contact_page_serve(
    minimal_site: Site,
    rf: RequestFactory,
    serving_method: str,
) -> None:
    """Test that ContactPage can be served and renders form field labels."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Contact Serve Test",
        slug="contact-serve-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "full_name", "label": "Full Name", "required": True},
                "id": "f1",
            },
            {
                "type": "email_field",
                "value": {"internal_identifier": "email", "label": "Email Address", "required": True},
                "id": "f2",
            },
            {
                "type": "phone_field",
                "value": {"internal_identifier": "phone", "label": "Phone Number", "required": False},
                "id": "f3",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    resp = getattr(page, serving_method)(request, mode_name="irrelevant")
    page_content = resp.text

    assert "Contact Serve Test" in page_content
    assert "Full Name" in page_content
    assert "Phone Number" in page_content


def test_contact_page_get_is_never_cached(
    minimal_site: Site,
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
    minimal_site: Site,
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
    assert "no-store" in resp.get("Cache-Control", "")
    mock_email_class.assert_not_called()


# GET and form field rendering


def test_no_js_notification_present(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """The contact page renders a noscript notification with orange color."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="NoJS Test",
        slug="nojs-test",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    resp = page.serve(request)
    content = resp.text

    assert "<noscript>" in content
    assert "fl-notification-orange" in content


def test_contact_page_get_context_form_data_defaults_to_empty_dict(
    minimal_site: Site,
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


def test_contact_page_country_select_field_renders_countries(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """CountrySelectField renders a <select> populated with country options."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Country Select Test",
        slug="country-select-test",
        form_fields=[
            {
                "type": "country_select_field",
                "value": {
                    "internal_identifier": "country",
                    "label": "Country",
                    "required": True,
                },
                "id": "country-select-field",
            }
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    response = page.serve(request)
    content = response.text

    assert response.status_code == 200
    # The select should contain country options — check for a few known codes
    assert 'value="US"' in content or 'value="GB"' in content


def test_contact_page_country_select_field_renders_localized_countries(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """CountrySelectField renders a <select> populated with localized labels for country options."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    fr_locale = Locale.objects.get(language_code="fr")

    page = ContactPage(
        title="Test de sélection de pays",
        slug="test-select-pays",
        form_fields=[
            {
                "type": "country_select_field",
                "value": {
                    "internal_identifier": "pays",
                    "label": "Pays",
                    "required": True,
                },
                "id": "pays-select-field",
            }
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    fr_page = page.copy_for_translation(fr_locale)
    fr_page.save_revision().publish()

    request = rf.get(fr_page.relative_url(minimal_site))
    response = fr_page.serve(request)
    content = response.text

    assert response.status_code == 200
    assert 'option value="FR">France' in content


def test_contact_page_textarea_field_renders_correctly(
    minimal_site: Site,
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


# Form validation


def test_contact_page_post_requires_csrf_token(
    minimal_site: Site,
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


def test_contact_page_includes_form_data_in_context(
    minimal_site: Site,
    client: Client,
) -> None:
    """get_context() passes form_data from request into the template context."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Context Form Data Test",
        slug="context-form-data-test",
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
        form_fields=get_form_field_variants(),
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    response = client.post(page.full_url, {"first_name": "Jane Doe"})
    assert response.status_code == 200
    context = response.context
    assert context["form_data"]
    assert context["form_data"]["first_name"] == "Jane Doe"


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_validates_missing_required_fields(
    mock_email_class,
    minimal_site: Site,
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
    request = rf.post(page.relative_url(minimal_site), {"message": "Hello"})
    resp = page.serve(request)
    assert resp.status_code == 200
    # Error text appears inline multiple times (once per missing required field)
    assert resp.text.count("This field is required.") >= 3
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_validates_empty_submission(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """Test that an empty POST (no fields filled in) is rejected."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    # Use only optional fields so required-field validation doesn't trigger first
    page = ContactPage(
        title="Contact Empty Test",
        slug="contact-empty-test",
        form_fields=[
            {
                "type": "textarea_field",
                "value": {"internal_identifier": "message", "label": "Message", "required": False, "rows": 4},
                "id": "f1",
            },
            {
                "type": "checkbox_field",
                "value": {"internal_identifier": "opt_in", "label": "I agree", "required": False},
                "id": "f2",
            },
        ],
        to_email_address="recipient@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {})

    resp = page.serve(request)
    assert resp.status_code == 200
    assert "Please fill out the form." in resp.text
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_validates_honeypot(
    mock_email_class,
    minimal_site: Site,
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

    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.text
    mock_email_class.assert_not_called()


def test_contact_page_empty_submission_with_required_field_shows_only_field_errors(
    minimal_site: Site,
    client: Client,
) -> None:
    """When required fields are missing, show per-field errors only, not the global empty error."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Required Only Field Errors",
        slug="required-only-field-errors",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "first_name", "label": "First name", "required": True},
                "id": "f1",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    response = client.post(page.full_url, {})
    content = response.content.decode()
    assert response.status_code == 200
    assert "This field is required." in content
    assert "Please fill out the form." not in content


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_renders_error_message_and_classes(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """When a required field is missing, the field wrapper gets fl-field-error and a message."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Inline Error Test",
        slug="inline-error-test",
        form_fields=get_form_field_variants()[:1],  # first_name only, required
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {})

    resp = page.serve(request)
    assert resp.status_code == 200
    assert "fl-field-wrap fl-field-error" in resp.text
    assert "fl-field-error-message" in resp.text
    assert "This field is required." in resp.text


def test_contact_page_validates_required_textarea_field(
    minimal_site: Site,
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


def test_contact_page_displays_text_field_value_after_validation_error(
    minimal_site: Site,
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

    # company filled, full_name empty (required) → validation error → redirect → GET re-renders
    request = rf.post(page.relative_url(minimal_site), {"company": "Acme Corp"})
    resp = page.serve(request)
    assert resp.status_code == 200
    assert 'value="Acme Corp"' in resp.content.decode()


def test_contact_page_displays_email_field_value_after_validation_error(
    minimal_site: Site,
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
    assert resp.status_code == 200
    assert 'value="jane@example.com"' in resp.content.decode()


def test_contact_page_displays_phone_field_value_after_validation_error(
    minimal_site: Site,
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
    assert resp.status_code == 200
    assert 'value="555-1234"' in resp.content.decode()


def test_contact_page_displays_textarea_field_value_after_validation_error(
    minimal_site: Site,
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
    assert resp.status_code == 200
    assert ">Hello world<" in resp.content.decode()


def test_contact_page_displays_select_field_value_after_validation_error(
    minimal_site: Site,
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
    assert resp.status_code == 200
    assert 'value="privacy" selected' in resp.content.decode()
    assert 'value="security" selected' not in resp.content.decode()


def test_contact_page_displays_checkbox_group_value_after_validation_error(
    minimal_site: Site,
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

    request = rf.post(page.relative_url(minimal_site), {"services": ["consulting", "support"]})

    resp = page.serve(request)
    assert resp.status_code == 200
    assert 'value="consulting" checked' in resp.content.decode()
    assert 'value="support" checked' in resp.content.decode()
    assert 'value="training" checked' not in resp.content.decode()


def test_contact_page_displays_checkbox_field_value_after_validation_error(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """After a validation error, a checked single checkbox remains checked."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Checkbox Field Persistence Test",
        slug="checkbox-field-persistence-test",
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
    assert resp.status_code == 200
    assert 'value="on" checked' in resp.content.decode()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_displays_country_select_field_value_after_validation_error(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """When validation fails, the previously selected country stays selected."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Country Persist Test",
        slug="country-persist-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "name-field",
            },
            {
                "type": "country_select_field",
                "value": {
                    "internal_identifier": "country",
                    "label": "Country",
                    "required": False,
                },
                "id": "country-select-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # POST with country but missing required name — triggers validation error
    request = rf.post(page.relative_url(minimal_site), {"country": "DE"})
    response = page.serve(request)
    assert response.status_code == 200
    assert 'value="DE" selected' in response.text
    mock_email_class.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_validates_country_select_field(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """Validates the country select field."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Country Validation Test",
        slug="country-validation-test",
        form_fields=[
            {
                "type": "country_select_field",
                "value": {
                    "internal_identifier": "country",
                    "label": "Country",
                    "required": False,
                },
                "id": "country-select-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"country": "not-an-option"})
    response = page.serve(request)
    assert response.status_code == 200
    assert "Please select a valid option" in response.text
    mock_email_class.assert_not_called()


# Hidden field


def test_contact_page_hidden_field_not_visible(
    minimal_site: Site,
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


@responses.activate
def test_contact_page_hidden_field_post_value_overrides_default(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """When a hidden field is submitted with a non-empty value, that POST value is forwarded to the basket API instead of default_value."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=200)

    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Hidden Field Override Test",
        slug="hidden-field-override-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "f1",
            },
            {
                "type": "hidden_field",
                "value": {
                    "internal_identifier": "source",
                    "default_value": "default-source",
                },
                "id": "hidden-field",
            },
        ],
        basket_api_path="/news/subscribe/",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"name": "Jane", "source": "overridden-source"})
    page.serve(request)

    body = json.loads(responses.calls[0].request.body)
    assert body["source"] == "overridden-source"


@responses.activate
def test_contact_page_hidden_field_missing_from_post_rejects_submission(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """A hidden field stripped from POST signals tampering: reject, never call basket."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=200)

    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Hidden Field Tamper Test",
        slug="hidden-field-tamper-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "f1",
            },
            {
                "type": "hidden_field",
                "value": {"internal_identifier": "source", "label": "Source", "default_value": "fallback-source"},
                "id": "hidden-field",
            },
        ],
        basket_api_path="/news/subscribe/",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # POST the visible field but omit the hidden field — simulates tampering
    request = rf.post(page.relative_url(minimal_site), {"name": "Jane"})
    response = page.serve(request)

    assert response.status_code == 200  # re-rendered with error, not redirected
    assert len(responses.calls) == 0  # basket never called


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_hidden_field_post_value_is_sent_in_email(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """When a hidden field has a non-empty POST value, it appears in the email body instead of default_value."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Hidden Field Email Override Test",
        slug="hidden-field-email-override-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "f1",
            },
            {
                "type": "hidden_field",
                "value": {"internal_identifier": "source", "default_value": "default-source"},
                "id": "hidden-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"name": "Jane", "source": "overridden-source"})
    page.serve(request)

    email_body = mock_email_class.call_args[0][1]
    assert "overridden-source" in email_body
    assert "default-source" not in email_body


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_validates_hidden_field_missing_from_post(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """A hidden field stripped from POST signals tampering: reject, never send email."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Hidden Field Tamper Email Test",
        slug="hidden-field-tamper-email-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "f1",
            },
            {
                "type": "hidden_field",
                "value": {"internal_identifier": "source", "label": "Source", "default_value": "fallback-source"},
                "id": "hidden-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"name": "Jane"})
    response = page.serve(request)

    assert response.status_code == 200
    mock_email_class.assert_not_called()


def test_contact_page_empty_submission_check_ignores_hidden_field_data(
    minimal_site: Site,
    client: Client,
) -> None:
    """A submission where only hidden fields carry values counts as empty."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Empty Ignores Hidden",
        slug="empty-ignores-hidden",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "message", "label": "Message", "required": False},
                "id": "f1",
            },
            {
                "type": "hidden_field",
                "value": {"internal_identifier": "source", "label": "Source", "default_value": "web"},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # Hidden fields always arrive in POST — include it, and leave the visible field empty.
    response = client.post(page.full_url, {"source": "web"})
    assert response.status_code == 200
    assert "Please fill out the form." in response.content.decode()


def test_contact_page_invalid_email_shows_localized_message(
    minimal_site: Site,
    client: Client,
) -> None:
    """A malformed email produces the localized invalid-email message, not Django's default."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Invalid Email Message",
        slug="invalid-email-message",
        form_fields=[
            {
                "type": "email_field",
                "value": {"internal_identifier": "business_email", "label": "Email", "required": True},
                "id": "f1",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    response = client.post(page.full_url, {"business_email": "not-an-email"})
    content = response.content.decode()
    assert response.status_code == 200
    assert "Please enter a valid email address." in content
    assert "Enter a valid email address." not in content  # Django's default must not leak


def test_contact_page_hidden_field_query_param_overrides_default_on_get(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """On GET, a hidden field renders the value of its query_param_override param when present in the URL."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Hidden Field Query Param Test",
        slug="hidden-field-query-param-test",
        form_fields=[
            {
                "type": "hidden_field",
                "value": {
                    "internal_identifier": "lead_source",
                    "default_value": "website",
                    "query_param_override": "ls",
                },
                "id": "hidden-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site), {"ls": "partner"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert 'name="lead_source"' in content
    assert 'value="partner"' in content
    assert 'value="website"' not in content


def test_contact_page_hidden_field_query_param_absent_uses_default_on_get(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """On GET without the query_param_override param, the hidden field renders its default_value."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Hidden Field Query Param Default Test",
        slug="hidden-field-query-param-default-test",
        form_fields=[
            {
                "type": "hidden_field",
                "value": {
                    "internal_identifier": "lead_source",
                    "default_value": "website",
                    "query_param_override": "ls",
                },
                "id": "hidden-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site))
    resp = page.serve(request)
    content = resp.content.decode()

    assert 'value="website"' in content


def test_contact_page_hidden_field_query_param_value_is_escaped(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """A user-controlled query param value is HTML-escaped when rendered into the hidden field."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Hidden Field Query Param Escape Test",
        slug="hidden-field-query-param-escape-test",
        form_fields=[
            {
                "type": "hidden_field",
                "value": {
                    "internal_identifier": "lead_source",
                    "default_value": "website",
                    "query_param_override": "ls",
                },
                "id": "hidden-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.get(page.relative_url(minimal_site), {"ls": '"><script>alert(1)</script>'})
    resp = page.serve(request)
    content = resp.content.decode()

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content


def test_contact_page_hidden_field_value_preserved_on_validation_error(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """On a validation-error re-render the hidden field keeps its submitted POST value."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)

    page = ContactPage(
        title="Hidden Field Error Persistence Test",
        slug="hidden-field-error-persistence-test",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "f1",
            },
            {
                "type": "hidden_field",
                "value": {
                    "internal_identifier": "lead_source",
                    "default_value": "website",
                    "query_param_override": "ls",
                },
                "id": "hidden-field",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    # name is required and missing → validation error → form re-renders in place
    request = rf.post(page.relative_url(minimal_site), {"lead_source": "partner"})
    resp = page.serve(request)
    content = resp.content.decode()

    assert resp.status_code == 200
    assert "This field is required." in content
    assert 'name="lead_source"' in content
    assert 'value="partner"' in content


# Valid form submission


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_sends_email_and_redirects_on_valid_post(
    mock_email_class,
    minimal_site: Site,
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
            "lead_source": "techrider.de",
            "cta": "Request Private Briefing",
            "opt_in": True,
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
def test_contact_page_valid_post_redirects_to_localized_page(
    mock_email_class,
    minimal_site: Site,
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
            "lead_source": "techrider.de",
            "cta": "Request Private Briefing",
            "opt_in": True,
        },
    )
    # Simulate an active fr locale for this request
    request.LANGUAGE_CODE = "fr"
    with patch("wagtail.models.i18n.Locale.get_active", return_value=fr_locale):
        resp = page.serve(request)

    assert resp.status_code == 302
    assert resp["Location"] == fr_thank_you.url


@patch("springfield.cms.models.pages.capture_message")
@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_handles_failure_sending_email(
    mock_email_class,
    mock_capture_message,
    minimal_site: Site,
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
            "lead_source": "techrider.de",
            "cta": "Request Private Briefing",
            "opt_in": True,
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
    assert "no-store" in resp.get("Cache-Control", "")
    mock_capture_message.assert_called_once()
    assert "Failed to send contact form email" in mock_capture_message.call_args[0][0]


@responses.activate
def test_contact_page_calls_basket_api_on_valid_post(
    minimal_site: Site,
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
            "lead_source": "techrider.de",
            "cta": "Request Private Briefing",
            "opt_in": True,
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
def test_contact_page_shows_error_message_on_basket_api_5xx(
    mock_capture_message,
    minimal_site: Site,
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

    valid_data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "company": "Acme",
        "job_title": "Engineer",
        "business_email": "jane@acme.com",
        "business_phone": "555-1234",
        "company_size": "1 - 10",
        "country": "US",
        "lead_source": "techrider.de",
        "cta": "Request Private Briefing",
        "opt_in": True,
    }
    request = rf.post(page.relative_url(minimal_site), valid_data)
    resp = page.serve(request)
    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
    mock_capture_message.assert_not_called()


@responses.activate
@patch("springfield.cms.models.pages.capture_message")
def test_contact_page_shows_error_message_and_reports_to_sentry_on_basket_api_4xx(
    mock_capture_message,
    minimal_site: Site,
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

    valid_data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "company": "Acme",
        "job_title": "Engineer",
        "business_email": "jane@acme.com",
        "business_phone": "555-1234",
        "company_size": "1 - 10",
        "country": "US",
        "lead_source": "techrider.de",
        "cta": "Request Private Briefing",
        "opt_in": True,
    }
    request = rf.post(page.relative_url(minimal_site), valid_data)
    resp = page.serve(request)
    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
    mock_capture_message.assert_called_once()
    call_args = mock_capture_message.call_args
    assert "400" in call_args[0][0]


@responses.activate
@patch("springfield.cms.models.pages.capture_message")
@pytest.mark.parametrize("status_code", [422, 429])
def test_contact_page_does_not_report_to_sentry_on_expected_api_errors(
    mock_capture_message,
    minimal_site: Site,
    rf: RequestFactory,
    status_code: int,
) -> None:
    """4xx basket API response re-renders with an error BUT does not send a Sentry event on 422 and 429 responses."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=status_code)

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

    spam_data = {
        "first_name": "Test",
        "last_name": "; DROP TABLE users;",
        "company": "Acme",
        "job_title": "Engineer",
        "business_email": "test@acme.com",
        "business_phone": "555-1234",
        "company_size": "1 - 10",
        "country": "US",
        "lead_source": "techrider.de",
        "cta": "Request Private Briefing",
        "opt_in": True,
    }
    request = rf.post(page.relative_url(minimal_site), spam_data)
    resp = page.serve(request)
    assert resp.status_code == 200
    assert "There was an error sending your message. Please try again." in resp.content.decode()
    mock_capture_message.assert_not_called()


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_post_valid_shows_thank_you_message(
    mock_email_class,
    minimal_site: Site,
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
            "lead_source": "techrider.de",
            "cta": "Request Private Briefing",
            "opt_in": True,
        },
    )
    resp = page.serve(request)

    assert resp.status_code == 200
    assert "Thanks for reaching out!" in resp.content.decode()


# Basket API payload and email message formatting


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_sends_textarea_field_value_in_email(
    mock_email_class,
    minimal_site: Site,
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


@responses.activate
def test_contact_page_basket_payload_uses_string_format(
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """Basket receives checkbox groups joined into a string and checkboxes as 'on'."""
    basket_url = f"{django_settings.BASKET_URL}/news/subscribe/"
    responses.add(responses.POST, basket_url, status=200)

    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Basket String Format",
        slug="basket-string-format",
        form_fields=[
            {
                "type": "checkbox_group_field",
                "value": {
                    "internal_identifier": "services",
                    "label": "Services",
                    "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
                },
                "id": "f1",
            },
            {
                "type": "checkbox_field",
                "value": {"internal_identifier": "agree", "label": "Agree", "required": False},
                "id": "f2",
            },
        ],
        basket_api_path="/news/subscribe/",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"services": ["a", "b"], "agree": "on"})
    page.serve(request)

    body = json.loads(responses.calls[0].request.body)
    assert body["services"] == "a, b"
    assert body["agree"] == "on"


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_formats_checkbox_group_values_for_email_message(
    mock_email_class,
    minimal_site: Site,
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
            "lead_source": "techrider.de",
            "cta": "Request Private Briefing",
            "opt_in": True,
        },
    )

    resp = page.serve(request)

    assert resp.status_code == 302
    call_args = mock_email_class.call_args
    email_body = call_args[0][1]
    assert "consulting, implementation" in email_body


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_renders_checkbox_as_string_for_email_message(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """A checked single checkbox appears as 'on' in the email, never as 'True'."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Email Checkbox Format",
        slug="email-checkbox-format",
        form_fields=[
            {
                "type": "text_field",
                "value": {"internal_identifier": "name", "label": "Name", "required": True},
                "id": "f1",
            },
            {
                "type": "checkbox_field",
                "value": {"internal_identifier": "agree", "label": "Agree", "required": False},
                "id": "f2",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"name": "Jane", "agree": "on"})
    page.serve(request)

    email_body = mock_email_class.call_args[0][1]
    assert "on" in email_body
    assert "True" not in email_body


@patch("springfield.cms.models.pages.EmailMessage")
def test_contact_page_strips_rich_text_from_checkbox_label_for_email_message(
    mock_email_class,
    minimal_site: Site,
    rf: RequestFactory,
) -> None:
    """A checkbox field's rich-text label is rendered as plain text (HTML tags stripped) in the email."""
    index_page = minimal_site.root_page
    thank_you_page = _create_thank_you_page(index_page)
    page = ContactPage(
        title="Rich Text Label Email",
        slug="rich-text-label-email",
        form_fields=[
            {
                "type": "checkbox_field",
                "value": {
                    "internal_identifier": "agree",
                    "label": "<p>I <strong>agree</strong> to the terms</p>",
                    "required": False,
                },
                "id": "f1",
            },
        ],
        to_email_address="test@example.com",
        redirect_to=thank_you_page,
    )
    index_page.add_child(instance=page)
    page.save_revision().publish()

    request = rf.post(page.relative_url(minimal_site), {"agree": "on"})
    page.serve(request)

    email_body = mock_email_class.call_args[0][1]
    assert "I agree to the terms" in email_body
    assert "<strong>" not in email_body
    assert "<p>" not in email_body
