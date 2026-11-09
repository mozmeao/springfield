# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.urls import reverse

from wagtail.contrib.redirects.models import Redirect
from wagtail.documents.models import Document
from wagtail.models import Collection, CollectionViewRestriction, ModelLogEntry

from springfield.cms.models import StableDocumentURL

SNIPPET_URL_NAMESPACE = "wagtailsnippets_cms_stabledocumenturl"
# The path every test starts from, and the one the rename tests move it to.
ORIGINAL_STABLE_URL = "/documents/subprocessors"
RENAMED_STABLE_URL = "/documents/sub-processors"


def form_data(document, **fields):
    return {
        "path": "subprocessors",
        "label": "Firefox Enterprise Sub-processors Document",
        "document": document.pk,
        **fields,
    }


def replace_file(document, content):
    """Upload new bytes over a document's file, as the document edit form does."""
    document.file.save("subprocessors.pdf", ContentFile(content), save=False)
    # The form does this itself whenever the file changes, and the file's new
    # hash is how a save that replaced the file is told apart from one that did not.
    document._set_document_file_metadata()
    document.save()


def restrict(collection):
    """Make a collection private, the way the admin's privacy modal does."""
    CollectionViewRestriction.objects.create(collection=collection, restriction_type=CollectionViewRestriction.LOGIN)


def test_an_editor_can_create_a_stable_url(admin_client, pdf_document):
    assert StableDocumentURL.objects.filter(path="subprocessors").exists() is False

    response = admin_client.post(reverse(f"{SNIPPET_URL_NAMESPACE}:add"), form_data(pdf_document))

    assert response.status_code == 302
    record = StableDocumentURL.objects.get(path="subprocessors")
    assert record.document == pdf_document
    assert record.url == ORIGINAL_STABLE_URL


def test_repointing_a_record_changes_what_the_stable_url_serves(admin_client, assigned_document, second_pdf_document):
    record = StableDocumentURL.objects.get(path="subprocessors")

    response = admin_client.post(reverse(f"{SNIPPET_URL_NAMESPACE}:edit", args=[record.pk]), form_data(second_pdf_document))

    assert response.status_code == 302
    served = admin_client.get(ORIGINAL_STABLE_URL)
    # Read through a fresh handle: document.file shares its handle with the view
    # under test, so a response missing the bytes already consumed from it would
    # still compare equal.
    with second_pdf_document.file.storage.open(second_pdf_document.file.name) as stored_file:
        assert b"".join(served.streaming_content) == stored_file.read()


def test_a_non_pdf_document_is_rejected_by_the_admin_form(admin_client, html_document):
    response = admin_client.post(reverse(f"{SNIPPET_URL_NAMESPACE}:add"), form_data(html_document, path="payload", label="Payload"))

    assert response.status_code == 200
    assert response.context["form"].errors["document"] == ["Only a PDF can be given a stable URL."]
    assert not StableDocumentURL.objects.exists()


def test_renaming_a_path_leaves_a_redirect_from_the_old_url(db, assigned_document):
    record = StableDocumentURL.objects.get(path="subprocessors")

    # Currently, no redirect exists.
    assert Redirect.objects.exists() is False

    record.path = "sub-processors"
    record.save()

    redirect = Redirect.objects.get(old_path=ORIGINAL_STABLE_URL)
    assert redirect.redirect_link == RENAMED_STABLE_URL
    assert redirect.automatically_created


def test_the_redirect_left_by_a_rename_is_not_permanent(db, assigned_document):
    record = StableDocumentURL.objects.get(path="subprocessors")

    record.path = "sub-processors"
    record.save()

    assert Redirect.objects.get(old_path=ORIGINAL_STABLE_URL).is_permanent is False


def test_saving_a_record_without_renaming_it_creates_no_redirect(db, assigned_document, second_pdf_document):
    record = StableDocumentURL.objects.get(path="subprocessors")

    record.label = "Sub-processors list"
    record.document = second_pdf_document
    record.save()

    assert not Redirect.objects.exists()


def test_renaming_a_path_back_to_a_previous_one_repoints_the_existing_redirect(db, assigned_document):
    # Renaming away, back, and away again asks for a second redirect at the
    # original path. Two rows with the same old_path and no site insert cleanly,
    # and then break the old URL outright rather than redirecting it.
    record = StableDocumentURL.objects.get(path="subprocessors")

    for new_path in ["sub-processors", "subprocessors", "sub-processors"]:
        record.path = new_path
        record.save()

    redirects_from_the_original_path = Redirect.objects.filter(old_path=ORIGINAL_STABLE_URL)
    assert redirects_from_the_original_path.count() == 1
    assert redirects_from_the_original_path.get().redirect_link == RENAMED_STABLE_URL


def test_saving_a_record_fills_the_documents_file_hash(db, pdf_document):
    # Blanked first because the fixture arrives with a hash already set.
    Document.objects.filter(pk=pdf_document.pk).update(file_hash="")
    pdf_document.refresh_from_db()

    StableDocumentURL.objects.create(path="subprocessors", label="Sub-processors", document=pdf_document)

    pdf_document.refresh_from_db()
    assert pdf_document.file_hash


def test_restricting_a_collection_deletes_the_records_in_it(db, assigned_document):
    assert StableDocumentURL.objects.filter(document=assigned_document).exists()

    restrict(assigned_document.collection)

    assert not StableDocumentURL.objects.exists()


def test_restricting_a_parent_collection_deletes_records_in_a_child_collection(db, assigned_document, stable_documents_collection):
    # A restriction applies to every collection below the one it names, so a
    # record one level down is as unservable as one in the named collection.
    assigned_document.collection = stable_documents_collection.add_child(name="Contracts")
    assigned_document.save()

    restrict(stable_documents_collection)

    assert not StableDocumentURL.objects.exists()


def test_moving_a_collection_under_a_restricted_one_deletes_the_records_in_it(
    admin_client, assigned_document, stable_documents_collection, django_capture_on_commit_callbacks
):
    # Driven through the admin because the move is only visible once the request's
    # transaction commits, and nothing is created or restricted by the move itself.
    private_collection = Collection.get_first_root_node().add_child(name="Private")
    restrict(private_collection)

    assert StableDocumentURL.objects.filter(document=assigned_document).exists()

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(
            reverse("wagtailadmin_collections:edit", args=[stable_documents_collection.pk]),
            {"name": stable_documents_collection.name, "parent": private_collection.pk},
        )

    assert response.status_code == 302
    assert not StableDocumentURL.objects.exists()


def test_editing_a_document_into_a_restricted_collection_deletes_its_record(admin_client, assigned_document):
    private_collection = Collection.get_first_root_node().add_child(name="Private")
    restrict(private_collection)

    assert StableDocumentURL.objects.filter(document=assigned_document).exists()

    response = admin_client.post(
        reverse("wagtaildocs:edit", args=[assigned_document.pk]),
        {"title": assigned_document.title, "collection": private_collection.pk},
    )

    assert response.status_code == 302
    assert not StableDocumentURL.objects.exists()


def test_moving_a_held_document_into_a_restricted_collection_in_bulk_deletes_the_record(admin_client, assigned_document):
    private_collection = Collection.get_first_root_node().add_child(name="Private")
    restrict(private_collection)

    assert StableDocumentURL.objects.filter(document=assigned_document).exists()

    response = admin_client.post(
        f"{reverse('wagtail_bulk_action', args=['wagtaildocs', 'document', 'add_to_collection'])}?id={assigned_document.pk}",
        {"collection": private_collection.pk},
    )

    assert response.status_code == 302
    assert not StableDocumentURL.objects.exists()


def test_replacing_a_held_documents_file_with_a_non_pdf_deletes_its_record(db, assigned_document):
    assert StableDocumentURL.objects.filter(document=assigned_document).exists()

    replace_file(assigned_document, b"<p>hi</p>")

    assert not StableDocumentURL.objects.exists()


def test_replacing_a_held_documents_file_with_another_pdf_keeps_the_record(db, assigned_document):
    assert StableDocumentURL.objects.filter(document=assigned_document).exists()

    replace_file(assigned_document, b"%PDF-1.4\nsecond edition")

    assert StableDocumentURL.objects.get().document == assigned_document


def test_an_automatic_deletion_is_recorded_in_the_log_with_the_path(db, assigned_document):
    restrict(assigned_document.collection)

    entry = ModelLogEntry.objects.filter(action="wagtail.delete").latest("timestamp")
    assert "subprocessors" in entry.label
    assert entry.data["path"] == "subprocessors"


def test_an_editor_is_told_when_their_own_change_deleted_a_record(admin_client, assigned_document):
    private_collection = Collection.get_first_root_node().add_child(name="Private")
    restrict(private_collection)

    response = admin_client.post(
        reverse("wagtaildocs:edit", args=[assigned_document.pk]),
        {"title": assigned_document.title, "collection": private_collection.pk},
        follow=True,
    )

    warnings = [str(message) for message in get_messages(response.wsgi_request) if message.level == messages.WARNING]
    assert any(ORIGINAL_STABLE_URL in warning for warning in warnings), warnings
