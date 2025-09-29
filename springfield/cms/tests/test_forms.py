# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.test import TestCase, override_settings

from springfield.cms.forms import TranslationsFilterForm


class TranslationsFilterFormTestCase(TestCase):
    """Test cases for the TranslationsFilterForm."""

    @override_settings(
        WAGTAIL_CONTENT_LANGUAGES=[
            ("en-US", "English (US)"),
            ("de", "German"),
            ("fr", "French"),
            ("es-ES", "Spanish (Spain)"),
            ("it", "Italian"),
        ]
    )
    def test_original_language_form_choices_include_all_languages(self):
        """Test that form choices include all configured languages."""
        form = TranslationsFilterForm()
        original_language_choices = form.fields["original_language"].choices

        # Should have "All languages" option plus all configured languages
        expected_choices = [
            ("", "All languages"),
            ("en-US", "English (US)"),
            ("de", "German"),
            ("fr", "French"),
            ("es-ES", "Spanish (Spain)"),
            ("it", "Italian"),
        ]
        self.assertEqual(original_language_choices, expected_choices)

    def test_original_language_form_validation_with_valid_language(self):
        """Test form validation with valid language code."""
        form = TranslationsFilterForm(data={"original_language": "en-US"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["original_language"], "en-US")

    def test_original_language_form_validation_with_empty_language(self):
        """Test form validation with empty language (all languages)."""
        form = TranslationsFilterForm(data={"original_language": ""})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["original_language"], "")

    def test_original_language_form_validation_with_invalid_language(self):
        """Test form validation with invalid language code."""
        form = TranslationsFilterForm(data={"original_language": "invalid-code"})
        self.assertFalse(form.is_valid())
        self.assertIn("original_language", form.errors)

    def test_form_initial_empty_state(self):
        """Test form initial state with no data."""
        form = TranslationsFilterForm({})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data.get("original_language"), "")

    def test_form_field_attributes(self):
        """Test that form field has correct attributes."""
        form = TranslationsFilterForm()
        field = form.fields["original_language"]

        # Test field properties
        self.assertEqual(field.label, "Original Language")
        self.assertFalse(field.required)
        self.assertEqual(field.widget.attrs.get("class"), "w-field__input")

    def test_form_dynamic_choices_update(self):
        """Test that choices are updated dynamically on form initialization."""
        # First create form with default settings
        with override_settings(WAGTAIL_CONTENT_LANGUAGES=[("en-US", "English (US)")]):
            form1 = TranslationsFilterForm()
            choices1 = form1.fields["original_language"].choices
            expected1 = [("", "All languages"), ("en-US", "English (US)")]
            self.assertEqual(choices1, expected1)

        # Then create form with different settings
        with override_settings(WAGTAIL_CONTENT_LANGUAGES=[("de", "German"), ("fr", "French")]):
            form2 = TranslationsFilterForm()
            choices2 = form2.fields["original_language"].choices
            expected2 = [("", "All languages"), ("de", "German"), ("fr", "French")]
            self.assertEqual(choices2, expected2)
