# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.http import require_POST

from taggit.models import Tag
from wagtail.admin.ui.tables import BaseColumn
from wagtail.admin.views.generic import DeleteView, IndexView
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.images.permissions import permission_policy as image_permission_policy
from wagtail.permission_policies.base import BasePermissionPolicy
from wagtail.search import index as search_index

from springfield.cms.images.views import InlineFieldColumn, InlineSaveColumn
from springfield.cms.models.images import SpringfieldImage


def user_can_change_any_image(user):
    """Whether the user has the change image permission."""
    return image_permission_policy._check_perm(user, ["change"])


class ImageTagPermissionPolicy(BasePermissionPolicy):
    """Tags can be renamed and deleted by anyone who can change any image. New tags are only
    created by tagging an image."""

    def user_has_permission(self, user, action):
        return action in ("change", "delete") and user_can_change_any_image(user)


def reindex_images(images):
    """Image search matches Tag names, and taggit changes them without saving the images."""
    for image in images:
        search_index.insert_or_update_object(image)


class InlineTagForm(forms.ModelForm):
    """A Tag's name, editable from its row in the image tags listing. The input points back to
    the row's <form> through its `form` attribute, and is prefixed with the tag id to keep it
    unique across the listing."""

    class Meta:
        model = Tag
        fields = ("name",)

    def __init__(self, *args, instance, **kwargs):
        super().__init__(*args, instance=instance, prefix=f"tag-{instance.pk}", **kwargs)
        self.form_id = f"tag-inline-{instance.pk}"
        self.action_url = reverse("image_tags:inline_edit", args=[instance.pk])
        self.delete_url = reverse("image_tags:delete", args=[instance.pk])
        self.fields["name"].widget.attrs["form"] = self.form_id

    def save(self, commit=True):
        tag = super().save(commit=commit)
        if commit:
            reindex_images(SpringfieldImage.objects.filter(tags=tag))
        return tag


@require_POST
def inline_edit_tag(request, tag_id):
    """Save a tag's name from its row in the image tags listing, and return the row's editable
    cells re-rendered. Responds 400, with nothing saved, when the form is invalid."""
    if not user_can_change_any_image(request.user):
        raise PermissionDenied
    tag = get_object_or_404(Tag, pk=tag_id)

    form = InlineTagForm(request.POST, instance=tag)
    is_saved = form.is_valid()
    if is_saved:
        form.save()

    return TemplateResponse(
        request,
        "springfield_images/inline_edit_cells.html",
        {"instance": tag, "form": form, "status_message": _("Saved") if is_saved else _("Not saved")},
        status=200 if is_saved else 400,
    )


class ImageCountColumn(BaseColumn):
    cell_template_name = "springfield_images/tag_image_count_cell.html"


class ImageTagIndexView(IndexView):
    """Every tag in alphabetical order, its name editable per row, with the number of images it's on."""

    columns = [
        InlineFieldColumn("name", label=gettext_lazy("Name")),
        ImageCountColumn("image_count", label=gettext_lazy("Images")),
        InlineSaveColumn("save", label=""),
    ]

    def get_base_queryset(self):
        image_content_type = ContentType.objects.get_for_model(SpringfieldImage)
        return (
            super()
            .get_base_queryset()
            .annotate(image_count=Count("taggit_taggeditem_items", filter=Q(taggit_taggeditem_items__content_type=image_content_type)))
            .order_by(Lower("name"))
        )

    def get_table(self, object_list):
        tags = list(object_list)
        for tag in tags:
            tag.inline_form = InlineTagForm(instance=tag)
        return super().get_table(tags)


class ImageTagDeleteView(DeleteView):
    """Wagtail's delete confirmation, showing how many images have the tag. Tags are not in the
    reference index, so its usage count would always be zero."""

    def get_usage_url(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["image_count"] = SpringfieldImage.objects.filter(tags=self.object).count()
        return context

    def delete_action(self):
        tagged_images = list(SpringfieldImage.objects.filter(tags=self.object))
        super().delete_action()
        reindex_images(tagged_images)


class ImageTagViewSet(ModelViewSet):
    model = Tag
    name = "image_tags"
    url_prefix = "image-tags"
    icon = "tag"
    menu_label = gettext_lazy("Image tags")
    add_to_settings_menu = True
    permission_policy = ImageTagPermissionPolicy(Tag)
    form_fields = ["name"]
    copy_view_enabled = False
    index_view_class = ImageTagIndexView
    delete_view_class = ImageTagDeleteView
    delete_template_name = "springfield_images/tag_confirm_delete.html"

    def get_urlpatterns(self):
        return [
            *super().get_urlpatterns(),
            path("<int:tag_id>/inline-edit/", inline_edit_tag, name="inline_edit"),
        ]
