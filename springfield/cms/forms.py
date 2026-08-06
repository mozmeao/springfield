# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from taggit.forms import TagField as TaggitTagField
from wagtail.admin.forms.pages import CopyForm
from wagtail.admin.forms.tags import TagField, validate_tag_length
from wagtail.admin.widgets import AdminTagWidget
from wagtail.models import Locale


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


class LocaleScopedAdminTagWidget(AdminTagWidget):
    """Wagtail's tag widget pointed at the locale-scoped autocomplete view.

    AdminTagWidget derives its autocomplete URL from the tag model, and Wagtail's view for
    it returns every locale's tags plus unpublished ones — names BlogTagField would then
    reject. Suggesting only what can be saved keeps that rejection out of the editor's way.
    """

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["data-w-tag-url-value"] = reverse("cms_blog_tag_autocomplete")
        return context


class BlogTagField(TagField):
    """A tag field that resolves typed names to default-locale BlogTag instances.

    Wagtail's TagField hands taggit a list of tag *names*, and taggit resolves each name to
    a row. BlogTag names are unique per locale rather than globally, so that lookup can
    land on another locale's row. This field resolves the names itself, scoped to published
    default-locale tags, and hands taggit instances instead.

    The tag model arrives in the `tag_model` kwarg that Wagtail's TaggableManager form-field
    override injects, so this field never imports BlogTag.
    """

    widget = LocaleScopedAdminTagWidget

    def clean(self, value):
        # TaggitTagField.clean parses the raw input into a list of names. The direct parent,
        # Wagtail's TagField.clean, is bypassed on purpose: it silently drops names that
        # match no tag, and returns names where this field returns instances.
        names = TaggitTagField.clean(self, value)
        validate_tag_length(names, self.tag_model.name.field.max_length)

        tags = list(self.tag_model.objects.filter(name__in=names, locale=Locale.get_default()).live())
        unknown = sorted(set(names) - {tag.name for tag in tags})
        if unknown:
            raise ValidationError(
                _("No published tag in the default locale matches: %(names)s. Create it as a Blog Tag snippet first.") % {"names": ", ".join(unknown)}
            )
        return tags
