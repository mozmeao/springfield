# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError
from django.db import IntegrityError

import pytest
from wagtail.models import CollectionViewRestriction

from springfield.cms.models import StableDocumentURL, stable_url_for_document


def test_a_document_with_no_assignment_has_no_stable_url(db, pdf_document):
    assert not hasattr(pdf_document, "stable_url")
    assert stable_url_for_document(pdf_document) is None


def test_an_assigned_document_reports_its_stable_url(db, assigned_document):
    assert assigned_document.stable_url.path == "subprocessors"
    assert stable_url_for_document(assigned_document) == "/documents/subprocessors"


def test_assigning_a_document_updates_stable_url_for_document(db, pdf_document):
    assert stable_url_for_document(pdf_document) is None
    StableDocumentURL.objects.create(path="subprocessors", label="Sub-processors", document=pdf_document)
    assert stable_url_for_document(pdf_document) == "/documents/subprocessors"


def test_a_document_cannot_hold_two_stable_paths(db, assigned_document):
    # assigned_document already has a StableDocumentURL
    assert assigned_document.stable_url is not None
    # Creating another StableDocumentURL for the assigned_document raises an error.
    with pytest.raises(IntegrityError):
        StableDocumentURL.objects.create(path="second", label="Second", document=assigned_document)


def test_two_documents_cannot_hold_the_same_path(db, assigned_document, second_pdf_document):
    with pytest.raises(IntegrityError):
        StableDocumentURL.objects.create(path="subprocessors", label="Sub-processors", document=second_pdf_document)


def test_deleting_an_assignment_updates_stable_url_for_document(db, assigned_document):
    assert stable_url_for_document(assigned_document) == "/documents/subprocessors"
    StableDocumentURL.objects.get(path="subprocessors").delete()
    assert stable_url_for_document(assigned_document) is None


def test_a_record_is_named_by_its_label(db, assigned_document):
    assert str(assigned_document.stable_url) == "Firefox Enterprise Sub-processors Document"


def test_a_path_is_lowercased(db, pdf_document):
    record = StableDocumentURL(path="Subprocessors", label="Sub-processors", document=pdf_document)
    record.full_clean()
    assert record.path == "subprocessors"


def test_a_non_pdf_document_is_rejected(db, html_document):
    record = StableDocumentURL(path="payload", label="Payload", document=html_document)
    with pytest.raises(ValidationError) as error:
        record.full_clean()
    assert error.value.message_dict["document"] == ["Only a PDF can be given a stable URL."]


def test_a_pdf_named_file_without_pdf_content_is_rejected(db, document_not_pdf_claiming_to_be_pdf):
    record = StableDocumentURL(path="disguised", label="Disguised", document=document_not_pdf_claiming_to_be_pdf)
    with pytest.raises(ValidationError):
        record.full_clean()


def test_a_document_in_a_restricted_collection_is_rejected(db, pdf_document):
    CollectionViewRestriction.objects.create(
        collection=pdf_document.collection,
        restriction_type=CollectionViewRestriction.LOGIN,
    )
    record = StableDocumentURL(path="subprocessors", label="Sub-processors", document=pdf_document)
    with pytest.raises(ValidationError):
        record.full_clean()
