# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import PermissionDenied
from django.db.models import prefetch_related_objects
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.http import require_POST

from wagtail.admin.ui.tables import BaseColumn
from wagtail.images import get_image_model
from wagtail.images.permissions import permission_policy
from wagtail.images.views.images import IndexView

from springfield.cms.images.forms import InlineImageForm
from springfield.cms.images.usage import NO_USAGE, get_image_usages


@require_POST
def inline_edit_image(request, image_id):
    """Save an image's title, description, decorative flag and tags from its row in the image
    listing, and return the row's editable cells re-rendered. Responds 400, with nothing saved,
    when the form is invalid.
    """
    image = get_object_or_404(get_image_model(), pk=image_id)
    if not permission_policy.user_has_permission_for_instance(request.user, "change", image):
        raise PermissionDenied

    form = InlineImageForm(request.POST, instance=image)
    is_saved = form.is_valid()
    if is_saved:
        form.save()

    return TemplateResponse(
        request,
        "springfield_images/inline_edit_cells.html",
        {"instance": image, "form": form, "status_message": _("Saved") if is_saved else _("Not saved")},
        status=200 if is_saved else 400,
    )


class InlineFieldColumn(BaseColumn):
    """A listing cell holding one field of the image's inline form."""

    cell_template_name = "springfield_images/inline_field_cell.html"

    def get_cell_context_data(self, instance, parent_context):
        context = super().get_cell_context_data(instance, parent_context)
        context["field_name"] = self.name
        context["field"] = instance.inline_form[self.name]
        return context


class InlineSaveColumn(BaseColumn):
    cell_template_name = "springfield_images/inline_save_cell.html"

    def get_cell_context_data(self, instance, parent_context):
        context = super().get_cell_context_data(instance, parent_context)
        context["form"] = instance.inline_form
        context["status_message"] = ""
        return context


class UsageListColumn(BaseColumn):
    cell_template_name = "springfield_images/usage_cell.html"


class SpringfieldImageIndexView(IndexView):
    """Wagtail's image listing, with the list layout's title, description, decorative flag and
    tags editable per row, and its usage shown as the pages and snippets that use each image."""

    def decorate_paginated_queryset(self, object_list):
        object_list = super().decorate_paginated_queryset(object_list)
        if self.layout != "list":
            return object_list

        images = list(object_list)
        prefetch_related_objects(images, "tags")
        usages = get_image_usages(images)
        for image in images:
            image.usage = usages.get(image.pk, NO_USAGE)
            image.inline_form = InlineImageForm(instance=image)
        return object_list

    @cached_property
    def columns(self):
        if self.layout == "grid":
            return []
        wagtail_columns = {column.name: column for column in super().columns}
        return [
            wagtail_columns["bulk_actions"],
            wagtail_columns["preview"],
            InlineFieldColumn("title", label=gettext_lazy("Title"), sort_key="title", width="20%"),
            InlineFieldColumn("description", label=gettext_lazy("Description"), width="25%"),
            InlineFieldColumn("is_decorative", label=gettext_lazy("Decorative")),
            InlineFieldColumn("tags", label=gettext_lazy("Tags"), width="15%"),
            UsageListColumn("usage", label=gettext_lazy("Usage"), sort_key=wagtail_columns["usage_count"].sort_key),
            InlineSaveColumn("save", label=""),
            wagtail_columns["collection"],
            wagtail_columns["created_at"],
        ]
