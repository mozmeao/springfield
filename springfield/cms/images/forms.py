# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Separate from cms.forms because that module is imported while the models load, and
# wagtail.images.forms reads the image model as it is imported. Wagtail resolves
# WAGTAILIMAGES_IMAGE_FORM_BASE when it builds the form, by which time models are ready.

from django import forms

from wagtail.admin.forms.tags import validate_tag_length
from wagtail.admin.widgets import AdminTagWidget
from wagtail.images.forms import BaseImageForm
from wagtail.search import index as search_index

from springfield.cms.models.images import SpringfieldImage


class SpringfieldImageForm(BaseImageForm):
    """Wagtail's image form with the title left empty for the editor to fill in.

    Wagtail wires a `w-sync` controller from the file input to the title input, so choosing a
    file pre-fills the title with the file's name minus its extension. A file name describes
    the file rather than the image, and one offered as a title is usually the one kept.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get("file"):
            self.fields["file"].widget.attrs.pop("data-controller", None)


class InlineImageForm(forms.ModelForm):
    """The fields of an image that can be edited from its row in the image listing.

    The inputs sit in separate table cells, outside the row's <form> element, so each one
    points back to it through a `form` attribute. Field names are prefixed with the image id
    to keep them unique across the listing.
    """

    # Declared rather than listed in Meta.fields, because a ModelForm reads a listed tags field
    # with a query of its own for every instance. The tags are taken from instance.tags.all()
    # instead, which the image listing prefetches for all its rows at once.
    tags = SpringfieldImage._meta.get_field("tags").formfield(widget=AdminTagWidget)

    class Meta:
        model = SpringfieldImage
        fields = ("title", "description", "is_decorative")
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, instance, **kwargs):
        super().__init__(*args, instance=instance, prefix=f"image-{instance.pk}", **kwargs)
        self.form_id = f"image-inline-{instance.pk}"
        self.initial["tags"] = list(instance.tags.all())
        for field in self.fields.values():
            field.widget.attrs["form"] = self.form_id

    def clean_tags(self):
        tags = self.cleaned_data["tags"]
        validate_tag_length(tags)
        return tags

    def save(self, commit=True):
        image = super().save(commit=commit)
        if commit:
            image.tags.set(self.cleaned_data["tags"])
            # Tags are written after the image row, so reindex to make the new tags searchable.
            search_index.insert_or_update_object(image)
        return image
