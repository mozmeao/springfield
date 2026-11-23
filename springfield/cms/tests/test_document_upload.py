# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from wagtail.documents.forms import get_document_form
from wagtail.documents.models import Document
from wagtail.models import Collection

pytestmark = [pytest.mark.django_db]

# The header `ffmpeg` writes at the start of a WebM file.
WEBM_HEADER = b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04\x42\xf3\x81\x08\x42\x82\x84webm\x42\x87\x81\x04\x42\x85\x81\x02"
# The same header with the document type of a Matroska (`.mkv`) file.
MATROSKA_HEADER = (
    b"\x1a\x45\xdf\xa3\xa3\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04\x42\xf3\x81\x08\x42\x82\x88matroska\x42\x87\x81\x04\x42\x85\x81\x02"
)
PLAIN_TEXT = b"Plain text in a file renamed to .webm"
SIX_MEGABYTES = 6 * 1024 * 1024

NOT_WEBM_ERROR = "This file is not a WebM video. Export the video in WebM format and upload it again."
TOO_BIG_ERROR = "This WebM video is too big (6.0\xa0MB). Reduce it to 5.0\xa0MB or less and upload it again."


def build_upload_form(file_name, content):
    return get_document_form(Document)(
        data={"title": "Uploaded file", "collection": Collection.get_first_root_node().pk},
        files={"file": SimpleUploadedFile(name=file_name, content=content)},
    )


def test_webm_upload_is_accepted():
    form = build_upload_form(file_name="red-pandas.webm", content=WEBM_HEADER)

    assert form.is_valid(), form.errors


@pytest.mark.parametrize(
    "file_name, content",
    [
        ("NOTES.WEBM", PLAIN_TEXT),
        ("recording.webm", MATROSKA_HEADER),
    ],
)
def test_file_named_webm_without_webm_content_is_rejected(file_name, content):
    form = build_upload_form(file_name=file_name, content=content)

    assert form.errors == {"file": [NOT_WEBM_ERROR]}


def test_webm_upload_over_the_size_limit_is_rejected():
    form = build_upload_form(file_name="red-pandas.webm", content=WEBM_HEADER.ljust(SIX_MEGABYTES, b"\0"))

    assert form.errors == {"file": [TOO_BIG_ERROR]}


def test_other_file_types_are_not_checked():
    form = build_upload_form(file_name="report.pdf", content=b"%PDF-1.7".ljust(SIX_MEGABYTES, b"\0"))

    assert form.is_valid(), form.errors


def test_editing_a_document_does_not_check_its_stored_file():
    document = Document.objects.create(title="Stored before the checks", file=ContentFile(content=PLAIN_TEXT, name="notes.webm"))

    form = get_document_form(Document)(data={"title": "Renamed", "collection": document.collection_id}, instance=document)

    assert form.is_valid(), form.errors


def test_upload_form_tells_the_editor_the_webm_requirements():
    form = build_upload_form(file_name="red-pandas.webm", content=WEBM_HEADER)

    assert form.fields["file"].help_text == "A video for a Video or Animation block must be a WebM file of 5.0\xa0MB or less."
