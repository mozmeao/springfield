# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms
from django.conf import settings


class TranslationsFilterForm(forms.Form):
    original_language = forms.ChoiceField(
        choices=[("", "Any language")] + list(settings.WAGTAIL_CONTENT_LANGUAGES),
        required=False,
        label="Original Language",
        widget=forms.Select(attrs={"class": "w-field__input"}),
    )
    exists_in_language = forms.ChoiceField(
        choices=[("", "Any language")] + list(settings.WAGTAIL_CONTENT_LANGUAGES),
        required=False,
        label="Exists In",
        widget=forms.Select(attrs={"class": "w-field__input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure choices are always up to date
        self.fields["original_language"].choices = [("", "Any language")] + list(settings.WAGTAIL_CONTENT_LANGUAGES)
        self.fields["exists_in_language"].choices = [("", "Any language")] + list(settings.WAGTAIL_CONTENT_LANGUAGES)
