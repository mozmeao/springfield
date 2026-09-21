# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from wagtail.admin.forms.pages import CopyForm

from springfield.cms.slug_updates import find_sibling_with_slug


class SpringfieldCopyForm(CopyForm):
    """Wagtail's page copy form plus a "Keep analytics IDs" opt-out.

    By default a copied page gets freshly generated analytics IDs (see the
    ``after_copy_page`` hook). Ticking this box preserves the source page's IDs
    instead. The checkbox is rendered by the overridden
    ``wagtailadmin/pages/copy.html`` template and read from ``request.POST`` by
    the hook.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["keep_analytics_ids"] = forms.BooleanField(
            required=False,
            initial=False,
            label=_("Keep analytics IDs"),
            help_text=_("Preserve the original page's analytics tracking IDs instead of generating new ones for the copy."),
        )


class UpdateSlugForm(forms.Form):
    """The slug an editor wants a page to move to."""

    slug = forms.SlugField(
        label=_("New slug"),
        help_text=_("The page and all of its translations will move to this slug."),
    )


class ConfirmUpdateSlugForm(forms.Form):
    """Confirmation of a slug update, including what to do with the page that
    currently holds the target slug.

    ``conflicting_page_slug`` is not displayed when no page holds the slug.
    """

    slug = forms.SlugField(widget=forms.HiddenInput)
    conflicting_page_slug = forms.SlugField(
        label=_("New slug for the existing page"),
        help_text=_("The page currently using the target slug moves here, and is unpublished along with its translations."),
    )
    publish = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Publish"),
        help_text=_("Publish the page and its translations once the slug has been updated."),
    )

    def __init__(self, *args, conflicting_page, **kwargs):
        super().__init__(*args, **kwargs)
        self.conflicting_page = conflicting_page

        if conflicting_page is None:
            del self.fields["conflicting_page_slug"]
        else:
            self.fields["conflicting_page_slug"].initial = f"{self['slug'].value()}-old"

    def clean_conflicting_page_slug(self):
        conflicting_page_slug = self.cleaned_data["conflicting_page_slug"]

        if conflicting_page_slug == self.cleaned_data.get("slug"):
            raise ValidationError(_("This must differ from the new slug, otherwise the existing page keeps it."))

        if find_sibling_with_slug(self.conflicting_page, conflicting_page_slug):
            raise ValidationError(_("Another page already uses this slug."))

        return conflicting_page_slug
