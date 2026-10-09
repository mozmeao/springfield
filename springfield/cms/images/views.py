# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from wagtail.images import get_image_model
from wagtail.images.permissions import permission_policy

from springfield.cms.images.forms import InlineImageForm


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
