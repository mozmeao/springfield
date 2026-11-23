# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

from wagtail.documents.forms import BaseDocumentForm

EBML_MAGIC_BYTES = b"\x1a\x45\xdf\xa3"
WEBM_DOCTYPE_ELEMENT = b"\x42\x82\x84webm"
# The EBML header opens the file and is a few dozen bytes long.
EBML_HEADER_READ_SIZE = 128


class SpringfieldDocumentForm(BaseDocumentForm):
    """Wagtail's document form with size and content checks for WebM videos.

    Documents hold any kind of file, and the Video and Animation blocks play the WebM ones.
    The checks apply to uploads named `.webm` and leave every other upload alone.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "file" in self.fields:
            max_size = filesizeformat(settings.WEBM_MAX_UPLOAD_SIZE)
            self.fields["file"].help_text = f"A video for a Video or Animation block must be a WebM file of {max_size} or less."

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if "file" not in self.changed_data or not uploaded_file.name.lower().endswith(".webm"):
            return uploaded_file

        if uploaded_file.size > settings.WEBM_MAX_UPLOAD_SIZE:
            raise ValidationError(
                f"This WebM video is too big ({filesizeformat(uploaded_file.size)}). "
                f"Reduce it to {filesizeformat(settings.WEBM_MAX_UPLOAD_SIZE)} or less and upload it again."
            )
        # WebM is a subset of Matroska and both open with the same bytes, so the document type
        # named in the header is what sets a WebM file apart.
        header = uploaded_file.read(EBML_HEADER_READ_SIZE)
        uploaded_file.seek(0)
        if not (header.startswith(EBML_MAGIC_BYTES) and WEBM_DOCTYPE_ELEMENT in header):
            raise ValidationError("This file is not a WebM video. Export the video in WebM format and upload it again.")
        return uploaded_file
