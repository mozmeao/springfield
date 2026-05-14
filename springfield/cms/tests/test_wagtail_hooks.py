# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

import pytest
from bs4 import BeautifulSoup
from draftjs_exporter.dom import DOM
from wagtail.documents import get_document_model
from wagtail.documents.rich_text import DocumentLinkHandler
from wagtail.documents.rich_text.contentstate import (
    DocumentLinkElementHandler,
    document_link_entity,
)
from wagtail.models import Page

from springfield.cms.rich_text import inject_link_uids
from springfield.cms.wagtail_hooks import (
    ExternalLinkHandler,
    UIDDocumentLinkElementHandler,
    UIDDocumentLinkHandler,
    UIDExternalLinkElementHandler,
    UIDPageLinkElementHandler,
    UIDPageLinkHandler,
    uid_document_link_entity,
    uid_link_entity,
)

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.fixture(autouse=True)
def init_dom():
    DOM.use(DOM.STRING)


class TestExternalLinkHandler:
    def test_with_uid(self):
        attrs = {"href": "https://example.com", "uid": "test-uid-123"}
        assert ExternalLinkHandler.expand_db_attributes(attrs) == '<a href="https://example.com" data-cta-uid="test-uid-123">'

    def test_without_uid(self):
        attrs = {"href": "https://example.com"}
        assert ExternalLinkHandler.expand_db_attributes(attrs) == '<a href="https://example.com">'

    def test_invalid_url_strips_href(self):
        attrs = {"href": "javascript:alert(1)"}
        assert ExternalLinkHandler.expand_db_attributes(attrs) == "<a>"

    def test_invalid_url_with_uid_keeps_uid(self):
        attrs = {"href": "javascript:alert(1)", "uid": "test-uid"}
        assert ExternalLinkHandler.expand_db_attributes(attrs) == '<a data-cta-uid="test-uid">'

    def test_uid_is_html_escaped(self):
        attrs = {"href": "https://example.com", "uid": "<script>xss</script>"}
        result = ExternalLinkHandler.expand_db_attributes(attrs)
        assert "<script>" not in result
        assert "&lt;script&gt;xss&lt;/script&gt;" in result


class TestUIDPageLinkHandler:
    @pytest.mark.django_db
    def test_with_uid(self, minimal_site):
        page = Page.objects.filter(depth__gt=1).last()
        results = UIDPageLinkHandler.expand_db_attributes_many([{"id": str(page.id), "uid": "test-uid-456"}])
        assert len(results) == 1
        assert 'data-cta-uid="test-uid-456"' in results[0]
        assert results[0].startswith("<a href=")

    @pytest.mark.django_db
    def test_without_uid(self, minimal_site):
        page = Page.objects.filter(depth__gt=1).last()
        results = UIDPageLinkHandler.expand_db_attributes_many([{"id": str(page.id)}])
        assert len(results) == 1
        assert "data-cta-uid" not in results[0]
        assert results[0].startswith("<a href=")

    @pytest.mark.django_db
    def test_page_not_found(self):
        results = UIDPageLinkHandler.expand_db_attributes_many([{"id": "999999", "uid": "test-uid"}])
        assert results == ["<a>"]

    @pytest.mark.django_db
    def test_multiple_attrs(self, minimal_site):
        page = Page.objects.filter(depth__gt=1).last()
        results = UIDPageLinkHandler.expand_db_attributes_many(
            [
                {"id": str(page.id), "uid": "uid-1"},
                {"id": "999999"},
            ]
        )
        assert len(results) == 2
        assert 'data-cta-uid="uid-1"' in results[0]
        assert results[1] == "<a>"


class TestUIDExternalLinkElementHandler:
    def test_uid_preserved(self):
        handler = UIDExternalLinkElementHandler("LINK")
        data = handler.get_attribute_data({"href": "https://example.com", "uid": "my-uid"})
        assert data["url"] == "https://example.com"
        assert data["uid"] == "my-uid"

    def test_uid_absent_when_not_in_attrs(self):
        handler = UIDExternalLinkElementHandler("LINK")
        data = handler.get_attribute_data({"href": "https://example.com"})
        assert data["url"] == "https://example.com"
        assert "uid" not in data


class TestUIDPageLinkElementHandler:
    @pytest.mark.django_db
    def test_uid_preserved(self, minimal_site):
        page = Page.objects.filter(depth__gt=1).last()
        handler = UIDPageLinkElementHandler("LINK")
        data = handler.get_attribute_data({"id": str(page.id), "uid": "page-uid-789"})
        assert data["id"] == page.id
        assert data["uid"] == "page-uid-789"

    @pytest.mark.django_db
    def test_uid_absent_when_not_in_attrs(self, minimal_site):
        page = Page.objects.filter(depth__gt=1).last()
        handler = UIDPageLinkElementHandler("LINK")
        data = handler.get_attribute_data({"id": str(page.id)})
        assert data["id"] == page.id
        assert "uid" not in data

    @pytest.mark.django_db
    def test_broken_link_returns_id_and_no_uid(self):
        handler = UIDPageLinkElementHandler("LINK")
        data = handler.get_attribute_data({"id": "999999"})
        assert data["id"] == 999999
        assert data["url"] is None
        assert "uid" not in data


class TestUIDLinkEntity:
    def test_external_link_with_uid(self):
        element = uid_link_entity({"url": "https://example.com", "uid": "ext-uid", "children": None})
        assert element.type == "a"
        assert element.attr["href"] == "https://example.com"
        assert element.attr["uid"] == "ext-uid"
        assert "linktype" not in element.attr
        assert "id" not in element.attr

    def test_external_link_without_uid_generates_uuid(self):
        element = uid_link_entity({"url": "https://example.com", "children": None})
        assert element.type == "a"
        assert element.attr["href"] == "https://example.com"
        assert _UUID_RE.match(element.attr["uid"])

    def test_external_link_uid_is_stable_when_provided(self):
        element1 = uid_link_entity({"url": "https://example.com", "uid": "fixed-uid", "children": None})
        element2 = uid_link_entity({"url": "https://example.com", "uid": "fixed-uid", "children": None})
        assert element1.attr["uid"] == element2.attr["uid"] == "fixed-uid"

    def test_external_link_uid_is_unique_when_generated(self):
        element1 = uid_link_entity({"url": "https://example.com", "children": None})
        element2 = uid_link_entity({"url": "https://example.com", "children": None})
        assert element1.attr["uid"] != element2.attr["uid"]

    def test_page_link_with_uid(self):
        element = uid_link_entity({"id": 42, "uid": "page-uid", "children": None})
        assert element.type == "a"
        assert element.attr["linktype"] == "page"
        assert element.attr["id"] == "42"
        assert element.attr["uid"] == "page-uid"
        assert "href" not in element.attr

    def test_page_link_without_uid_generates_uuid(self):
        element = uid_link_entity({"id": 42, "children": None})
        assert element.attr["linktype"] == "page"
        assert _UUID_RE.match(element.attr["uid"])

    def test_invalid_external_url_sets_no_href(self):
        element = uid_link_entity({"url": "javascript:alert(1)", "uid": "uid-xss", "children": None})
        assert "href" not in element.attr
        assert element.attr["uid"] == "uid-xss"


class TestInjectLinkUIDs:
    def test_adds_uid_to_link_without_uid(self):
        html = '<p>See <a href="https://example.com">this</a>.</p>'
        result = inject_link_uids(html)
        uid = BeautifulSoup(result, "html.parser").find("a")["uid"]
        assert _UUID_RE.match(uid)

    def test_does_not_overwrite_existing_uid(self):
        html = '<p><a href="https://example.com" uid="existing-uid">link</a></p>'
        result = inject_link_uids(html)
        assert BeautifulSoup(result, "html.parser").find("a")["uid"] == "existing-uid"

    def test_each_link_gets_unique_uid(self):
        html = '<p><a href="https://a.com">A</a> and <a href="https://b.com">B</a></p>'
        result = inject_link_uids(html)
        uids = [tag["uid"] for tag in BeautifulSoup(result, "html.parser").find_all("a")]
        assert len(uids) == 2
        assert uids[0] != uids[1]
        assert all(_UUID_RE.match(uid) for uid in uids)

    def test_mixed_links_only_fills_missing_uids(self):
        html = '<p><a href="https://a.com" uid="keep-this">A</a> <a href="https://b.com">B</a></p>'
        result = inject_link_uids(html)
        tags = BeautifulSoup(result, "html.parser").find_all("a")
        assert tags[0]["uid"] == "keep-this"
        assert _UUID_RE.match(tags[1]["uid"])

    def test_returns_original_string_when_no_changes(self):
        html = '<p><a href="https://example.com" uid="already-set">link</a></p>'
        result = inject_link_uids(html)
        assert result is html

    def test_returns_input_unchanged_when_empty(self):
        assert inject_link_uids("") == ""
        assert inject_link_uids(None) is None

    def test_no_links_returns_original_string(self):
        html = "<p>No links here.</p>"
        result = inject_link_uids(html)
        assert result is html


class TestUIDDocumentLinkHandler:
    @pytest.mark.django_db
    def test_with_uid(self):
        Document = get_document_model()
        doc = Document.objects.create(title="Test Doc")
        results = UIDDocumentLinkHandler.expand_db_attributes_many([{"id": str(doc.id), "uid": "doc-uid-123"}])
        original = DocumentLinkHandler.expand_db_attributes_many([{"id": str(doc.id)}])
        assert len(results) == 1
        assert 'data-cta-uid="doc-uid-123"' in results[0]
        assert results[0] == original[0].replace(">", ' data-cta-uid="doc-uid-123">')

    @pytest.mark.django_db
    def test_without_uid(self):
        Document = get_document_model()
        doc = Document.objects.create(title="Test Doc")
        attrs_list = [{"id": str(doc.id)}]
        results = UIDDocumentLinkHandler.expand_db_attributes_many(attrs_list)
        assert len(results) == 1
        assert "data-cta-uid" not in results[0]
        assert results[0] == DocumentLinkHandler.expand_db_attributes_many(attrs_list)[0]

    @pytest.mark.django_db
    def test_document_not_found(self):
        results = UIDDocumentLinkHandler.expand_db_attributes_many([{"id": "999999", "uid": "doc-uid"}])
        assert results == ["<a>"]

    @pytest.mark.django_db
    def test_multiple_attrs(self):
        Document = get_document_model()
        doc = Document.objects.create(title="Test Doc")
        results = UIDDocumentLinkHandler.expand_db_attributes_many(
            [
                {"id": str(doc.id), "uid": "uid-1"},
                {"id": "999999"},
            ]
        )
        assert len(results) == 2
        assert 'data-cta-uid="uid-1"' in results[0]
        assert results[1] == "<a>"


class TestUIDDocumentLinkElementHandler:
    @pytest.mark.django_db
    def test_uid_preserved(self):
        Document = get_document_model()
        doc = Document.objects.create(title="Test Doc")
        attrs = {"id": str(doc.id), "uid": "doc-uid-456"}
        data = UIDDocumentLinkElementHandler("DOCUMENT").get_attribute_data(attrs)
        original_data = DocumentLinkElementHandler("DOCUMENT").get_attribute_data({"id": str(doc.id)})
        assert data["id"] == doc.id
        assert data["uid"] == "doc-uid-456"
        assert {k: v for k, v in data.items() if k != "uid"} == original_data

    @pytest.mark.django_db
    def test_uid_absent_when_not_in_attrs(self):
        Document = get_document_model()
        doc = Document.objects.create(title="Test Doc")
        attrs = {"id": str(doc.id)}
        data = UIDDocumentLinkElementHandler("DOCUMENT").get_attribute_data(attrs)
        assert data["id"] == doc.id
        assert "uid" not in data
        assert data == DocumentLinkElementHandler("DOCUMENT").get_attribute_data(attrs)

    @pytest.mark.django_db
    def test_broken_link_returns_id_and_no_uid(self):
        handler = UIDDocumentLinkElementHandler("DOCUMENT")
        data = handler.get_attribute_data({"id": "999999"})
        assert data["id"] == 999999
        assert "uid" not in data


class TestUIDDocumentLinkEntity:
    def test_with_uid(self):
        element = uid_document_link_entity({"id": 7, "uid": "doc-uid", "children": None})
        original = document_link_entity({"id": 7, "children": None})
        assert element.type == "a"
        assert element.attr["linktype"] == "document"
        assert element.attr["id"] == "7"
        assert element.attr["uid"] == "doc-uid"
        assert {k: v for k, v in element.attr.items() if k != "uid"} == original.attr

    def test_without_uid_generates_uuid(self):
        element = uid_document_link_entity({"id": 7, "children": None})
        original = document_link_entity({"id": 7, "children": None})
        assert element.attr["linktype"] == "document"
        assert _UUID_RE.match(element.attr["uid"])
        assert {k: v for k, v in element.attr.items() if k != "uid"} == original.attr

    def test_uid_is_unique_when_generated(self):
        element1 = uid_document_link_entity({"id": 7, "children": None})
        element2 = uid_document_link_entity({"id": 7, "children": None})
        assert element1.attr["uid"] != element2.attr["uid"]
