# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Separate from cms.forms because that module is imported while the models load, and
# wagtail.images.forms reads the image model as it is imported. Wagtail resolves
# WAGTAILIMAGES_IMAGE_FORM_BASE when it builds the form, by which time models are ready.

from wagtail.images.forms import BaseImageForm


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
