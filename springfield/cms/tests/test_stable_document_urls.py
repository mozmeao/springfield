# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.fields.files import FieldFile
from django.test import Client

import pytest
from wagtail.models import CollectionViewRestriction

from springfield.cms.models import StableDocumentURL, stable_url_for_document
from springfield.cms.tests.factories import SimpleRichTextPageFactory

STABLE_URL_SUBPROCESSORS_DOCUMENT = "/documents/subprocessors"


def stored_bytes(document):
    """
    The document's file as storage holds it, read through a fresh handle.

    Reading ``document.file`` instead would share a handle with the code under
    test, so a response missing the bytes already consumed from it would still
    compare equal.
    """
    with document.file.storage.open(document.file.name) as stored_file:
        return stored_file.read()


# Each of the next three fixtures assigns a stable URL that the edit form would
# have refused, by going through objects.create(), which skips clean(). The
# record has to exist: without it the path 404s for want of a record, which is
# the wrong reason and passes even with no refusal in the serving view at all.


@pytest.fixture
def assigned_html_document(html_document):
    StableDocumentURL.objects.create(path="payload", label="Payload", document=html_document)
    return html_document


@pytest.fixture
def assigned_document_claiming_to_be_pdf(document_not_pdf_claiming_to_be_pdf):
    StableDocumentURL.objects.create(path="disguised", label="Disguised", document=document_not_pdf_claiming_to_be_pdf)
    return document_not_pdf_claiming_to_be_pdf


@pytest.fixture
def assigned_document_in_a_restricted_collection(pdf_document):
    CollectionViewRestriction.objects.create(
        collection=pdf_document.collection,
        restriction_type=CollectionViewRestriction.LOGIN,
    )
    StableDocumentURL.objects.create(path="restricted", label="Sub-processors", document=pdf_document)
    return pdf_document


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


def test_the_stable_url_serves_the_assigned_document(client, assigned_document):
    response = client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT)

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == stored_bytes(assigned_document)
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == "inline"
    assert response["Content-Length"] == str(assigned_document.file.size)
    assert response["Cache-Control"] == "max-age=600, public"
    assert response["Content-Security-Policy"] == "default-src 'none'"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["ETag"].strip('"') == assigned_document.file_hash
    # Accept-Language in Vary would split the edge cache by browser language on a
    # response whose body is the same file for everyone.
    assert "Accept-Language" not in response.get("Vary", "")


def test_the_stable_url_serves_the_new_document_after_a_reassignment(client, assigned_document, second_pdf_document):
    record = StableDocumentURL.objects.get(path="subprocessors")
    record.document = second_pdf_document
    record.save()

    response = client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT)

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == stored_bytes(second_pdf_document)
    assert response["ETag"].strip('"') == second_pdf_document.file_hash


def test_a_path_no_record_holds_is_not_found(client, db):
    assert client.get("/documents/nothing-here").status_code == 404


def test_a_non_pdf_document_is_not_found(client, assigned_html_document):
    url = assigned_html_document.stable_url.url
    assert client.get(url).status_code == 404


def test_a_pdf_named_file_without_pdf_content_is_not_found(client, assigned_document_claiming_to_be_pdf):
    url = assigned_document_claiming_to_be_pdf.stable_url.url
    assert client.get(url).status_code == 404


def test_a_document_in_a_restricted_collection_is_not_found(client, assigned_document_in_a_restricted_collection):
    url = assigned_document_in_a_restricted_collection.stable_url.url
    assert client.get(url).status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "/documents/nothing-here",
        "/documents/",
        "/documents",
        "/documents/nested/path",
        # Not a slug: the serving route's converter accepts only letters, digits,
        # hyphens and underscores.
        "/documents/not~a~slug",
    ],
)
def test_a_not_found_response_is_not_cacheable(client, db, url):
    response = client.get(url)

    assert response.status_code == 404
    assert response["Cache-Control"] == "no-store"
    assert "Expires" not in response


def test_the_trailing_slash_form_redirects_to_the_canonical_url(client, assigned_document):
    response = client.get(f"{STABLE_URL_SUBPROCESSORS_DOCUMENT}/")

    # Deliberately not a permanent redirect.
    assert response.status_code == 302
    assert response["Location"] == STABLE_URL_SUBPROCESSORS_DOCUMENT


def test_the_canonical_url_is_not_redirected(client, assigned_document):
    assert client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT).status_code == 200


@pytest.mark.parametrize("url", ["/documents/Subprocessors", "/documents/SUBPROCESSORS", "/documents/SubProcessors"])
def test_an_uppercase_path_redirects_to_the_canonical_lowercase_url(client, assigned_document, url):
    # Paths are stored lowercased, but Django's slug converter accepts uppercase,
    # so these reach the view. Serving them directly would publish one document
    # at several URLs.
    response = client.get(url)

    assert response.status_code == 302
    assert response["Location"] == STABLE_URL_SUBPROCESSORS_DOCUMENT


def test_a_held_path_does_not_serve_outside_the_documents_prefix(client, assigned_document):
    # The prefix is fixed in code and only the slug after it is editor-supplied,
    # so holding "subprocessors" must not also mint /subprocessors.
    response = client.get("/subprocessors", follow=True)

    assert response.status_code == 404


def test_a_head_request_returns_the_headers(client, assigned_document):
    response = client.head(STABLE_URL_SUBPROCESSORS_DOCUMENT)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Length"] == str(assigned_document.file.size)


def test_a_matching_etag_returns_not_modified(client, assigned_document):
    served = client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT)

    response = client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT, HTTP_IF_NONE_MATCH=served["ETag"])

    assert response.status_code == 304
    # A 304's headers update the stored response, so no-store here would tell
    # every cache to drop the PDF it just revalidated.
    assert "no-store" not in response.get("Cache-Control", "")


def test_a_storage_read_failure_is_not_disguised_as_a_missing_document(db, assigned_document):
    # A 404 would read as a record someone retired on purpose. An unreadable blob
    # has to reach Sentry instead.
    unforgiving_client = Client(raise_request_exception=False)

    with mock.patch.object(FieldFile, "open", side_effect=OSError("the blob is gone")):
        response = unforgiving_client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT)

    assert response.status_code == 500


def test_an_unassigned_stable_path_is_not_rewritten_to_a_cms_page(db, client, minimal_site):
    page = SimpleRichTextPageFactory(slug="subprocessors", title="Sub-processors", parent=minimal_site.root_page, live=True)

    response = client.get(STABLE_URL_SUBPROCESSORS_DOCUMENT)

    assert response.status_code == 404
    assert "Location" not in response
    assert page.url != STABLE_URL_SUBPROCESSORS_DOCUMENT


def test_the_bare_prefix_is_not_rewritten_to_a_cms_page(db, client, minimal_site):
    response = client.get("/documents/")

    assert response.status_code == 404
    assert "Location" not in response
