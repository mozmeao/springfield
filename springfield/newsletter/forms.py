# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from operator import itemgetter

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_unicode_slug
from django.forms import widgets

from product_details import product_details

from lib.l10n_utils.fluent import ftl, ftl_lazy
from springfield.base.forms import EmailInput, PrivacyWidget, strip_parenthetical
from springfield.newsletter import utils


def validate_newsletters(newsletters):
    if not newsletters:
        raise ValidationError("No Newsletter Provided")

    newsletters = [n.replace(" ", "") for n in newsletters]
    for newsletter in newsletters:
        try:
            validate_unicode_slug(newsletter)
        except ValidationError:
            raise ValidationError("Invalid newsletter")

    return newsletters


def get_lang_choices(newsletters=None):
    """
    Return a localized list of choices for language.

    List looks like: [[lang_code, lang_name], [lang_code, lang_name], ...]

    :param newsletters: Either a comma separated string or a list of newsletter ids.
    """
    lang_choices = []
    languages = utils.get_languages_for_newsletters(newsletters)

    for lang in languages:
        if lang in product_details.languages:
            lang_name = product_details.languages[lang]["native"]
        else:
            try:
                locale = [loc for loc in product_details.languages if loc.startswith(lang)][0]
            except IndexError:
                continue
            lang_name = product_details.languages[locale]["native"]
        lang_choices.append([lang, strip_parenthetical(lang_name)])
    return sorted(lang_choices, key=itemgetter(1))


class BooleanTabularRadioSelect(widgets.RadioSelect):
    """
    A Select Widget intended to be used with BooleanField.
    """

    template_name = "newsletter/forms/tabular_radio_select.html"
    wrap_label = False

    def __init__(self, attrs=None):
        choices = (
            ("true", ftl("newsletter-form-yes")),
            ("false", ftl("newsletter-form-no")),
        )
        super().__init__(attrs, choices)

    def format_value(self, value):
        try:
            return {
                True: "true",
                False: "false",
                "true": "true",
                "false": "false",
            }[value]
        except KeyError:
            return "unknown"

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        return {
            True: True,
            False: False,
            "true": True,
            "false": False,
        }.get(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["wrap_label"] = False
        return context


class NewsletterForm(forms.Form):
    """
    Form to let a user subscribe to or unsubscribe from a newsletter
    on the manage existing newsletters page.  Used in a FormSet.
    """

    title = forms.CharField(required=False)
    description = forms.CharField(required=False)
    subscribed_radio = forms.BooleanField(
        widget=BooleanTabularRadioSelect,
        required=False,  # they have to answer, but answer can be False
    )
    subscribed_check = forms.BooleanField(
        widget=widgets.CheckboxInput,
        required=False,  # they have to answer, but answer can be False
    )
    newsletter = forms.CharField(widget=forms.HiddenInput)


class NewsletterFooterForm(forms.Form):
    """
    Form used to subscribe to a single newsletter, typically in the
    footer of a page (see newsletters/middleware.py) but sometimes
    on a dedicated page.
    """

    choice_labels = {
        "mozilla-foundation": ftl("multi-newsletter-form-checkboxes-label-mozilla"),
        "mozilla-and-you": ftl("multi-newsletter-form-checkboxes-label-firefox"),
        "nothing-personal-college-interest-waitlist": "Exclusive college-related content",  # issue 15218.
    }

    email = forms.EmailField(widget=EmailInput(attrs={"required": "required", "data-testid": "newsletter-email-input"}))
    # first/last_name not yet included in email_newsletter_form helper
    # currently used on /contribute/friends/ (custom markup)
    first_name = forms.CharField(widget=forms.TextInput, required=False)
    last_name = forms.CharField(widget=forms.TextInput, required=False)
    privacy = forms.BooleanField(widget=PrivacyWidget(attrs={"data-testid": "newsletter-privacy-checkbox"}))
    source_url = forms.CharField(required=False)
    newsletters = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple())

    # has to take a newsletters argument so it can figure
    # out which languages to list in the form.
    def __init__(self, newsletters, locale, data=None, multi_opt_in_required=False, *args, **kwargs):
        regions = product_details.get_regions(locale)
        regions = sorted(iter(regions.items()), key=itemgetter(1))

        try:
            if isinstance(newsletters, str):
                newsletters = newsletters.split(",")
            newsletters = validate_newsletters(newsletters)
        except ValidationError:
            # replace with most common good newsletter
            # form validation will work with submitted data
            newsletters = ["mozilla-and-you"]

        is_multi_newsletter = len(newsletters) > 1
        lang = locale.lower()
        if "-" in lang:
            lang, country = lang.split("-", 1)
        else:
            country = ""
            regions.insert(0, ("", ftl_lazy("newsletter-form-select-country-or-region", fallback="newsletter-form-select-country")))
        lang_choices = get_lang_choices(newsletters)
        languages = [x[0] for x in lang_choices]
        if lang not in languages:
            # The lang from their locale is not one that our newsletters
            # are translated into. Initialize the language field to no
            # choice, to force the user to pick one of the languages that
            # we do support.
            lang = ""
            lang_choices.insert(0, ("", ftl_lazy("newsletter-form-available-languages")))

        super().__init__(data, *args, **kwargs)

        required_args = {
            "required": "required",
            "aria-required": "true",
        }
        country_select_args = {"data-testid": "newsletter-country-select"}
        country_widget = widgets.Select(attrs=required_args | country_select_args)
        country_label = ftl_lazy("newsletter-form-select-country-or-region", fallback="newsletter-form-select-country")
        self.fields["country"] = forms.ChoiceField(widget=country_widget, choices=regions, initial=country, required=False, label=country_label)
        lang_widget = widgets.Select(attrs=required_args)
        lang_label = ftl_lazy("newsletter-form-select-language", fallback="newsletter-form-available-languages")
        self.fields["lang"] = forms.TypedChoiceField(widget=lang_widget, choices=lang_choices, initial=lang, required=False, label=lang_label)
        self.fields["newsletters"].choices = [(n, self.choice_labels.get(n, n)) for n in newsletters]

        # Automatically check newsletter choices unless opt-in is explicitly required.
        if is_multi_newsletter and multi_opt_in_required:
            self.fields["newsletters"].initial = None
        else:
            self.fields["newsletters"].initial = newsletters

    def clean_newsletters(self):
        return validate_newsletters(self.cleaned_data["newsletters"])

    def clean_source_url(self):
        su = self.cleaned_data["source_url"].strip()
        if su:
            # limit to 255 characters by truncation
            return su[:255]

        return su
