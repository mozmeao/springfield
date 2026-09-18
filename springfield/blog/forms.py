# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from taggit.forms import TagField as TaggitTagField
from wagtail.admin.forms.tags import TagField, validate_tag_length
from wagtail.admin.widgets import AdminTagWidget
from wagtail.models import Locale


class LocaleScopedAdminTagWidget(AdminTagWidget):
    """Wagtail's tag widget pointed at the locale-scoped autocomplete view.

    AdminTagWidget gets its autocomplete URL from the tag model, and Wagtail's view for
    it returns every tag with no filtering. `blog_tag_autocomplete` view returns only
    published tags in the default locale.
    """

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["data-w-tag-url-value"] = reverse("blog_tag_autocomplete")
        return context


class LocaleTagField(TagField):
    """A <TagModel> field that resolves typed names to default-locale <TagModel> instances.

    Wagtail's TagField hands taggit a list of tag *names*, and taggit resolves each name to
    a row. In order to have Tag names be unique per locale rather than globally, this field
    resolves the names itself, scoped to published default-locale tags, and hands taggit
    instances instead.
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
                _("No published tag in the default locale matches: %(names)s. Create it as a %(tag_model)s snippet first.")
                % {"names": ", ".join(unknown), "tag_model": self.tag_model._meta.verbose_name}
            )
        return tags
