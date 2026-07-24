# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import base64
import csv
from io import StringIO
from xml.etree import ElementTree

from django.core.management import call_command
from django.core.management.base import CommandError, OutputWrapper

import pytest
import requests
from wagtail.models import Locale

from springfield.cms.fixtures.blog_fixtures import get_blog_index_page
from springfield.cms.management.commands.import_wordpress_blog_posts import Command, _text
from springfield.cms.models import BlogArticlePage
from springfield.cms.models.snippets import Author, Tag
from springfield.cms.tests.factories import LocaleFactory

pytestmark = [pytest.mark.django_db]

# A minimal valid 1x1 transparent PNG, so SpringfieldImage.save() (which generates renditions) succeeds.
PNG_BYTES = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

POST_DEFAULTS = {
    "id": "1",
    "title": "A Test Post",
    "content": "<p>Hello world.</p>",
    "date": "2020-01-01 00:00:00",
    "post_type": "post",
    "slug": "a-test-post",
    "image_url": "https://example.com/hero.jpg",
    "image_title": "Hero Image",
    "categories": "Firefox",
    "tags": "",
    "author_username": "someone@example.com",
    "author_first": "Nick",
    "author_last": "Nguyen",
}


def _post_xml(**overrides):
    values = {**POST_DEFAULTS, **overrides}
    return f"""
    <post>
        <ID>{values["id"]}</ID>
        <Title>{values["title"]}</Title>
        <Content><![CDATA[{values["content"]}]]></Content>
        <Excerpt/>
        <Date>{values["date"]}</Date>
        <PostType>{values["post_type"]}</PostType>
        <Permalink>https://blog.mozilla.org/en/firefox/{values["slug"]}/</Permalink>
        <ImageURL>{values["image_url"]}</ImageURL>
        <ImageFilename>hero.jpg</ImageFilename>
        <ImagePath>/nas/hero.jpg</ImagePath>
        <ImageID>1</ImageID>
        <ImageTitle>{values["image_title"]}</ImageTitle>
        <ImageCaption/>
        <ImageDescription/>
        <ImageAltText/>
        <ImageFeatured>{values["image_url"]}</ImageFeatured>
        <Categories>{values["categories"]}</Categories>
        <Tags>{values["tags"]}</Tags>
        <Authors/>
        <AuthorUsername>{values["author_username"]}</AuthorUsername>
        <AuthorFirstName>{values["author_first"]}</AuthorFirstName>
        <AuthorLastName>{values["author_last"]}</AuthorLastName>
        <Slug>{values["slug"]}</Slug>
    </post>
    """


def _write_xml(tmp_path, *posts, filename="posts.xml"):
    path = tmp_path / filename
    path.write_text(f"<data>{''.join(posts)}</data>")
    return path


def _parse_post(xml_string):
    """Parse a single <post> fragment (as produced by _post_xml) into an ElementTree Element."""
    return ElementTree.fromstring(f"<data>{xml_string}</data>").find("post")


def _fake_response(content=PNG_BYTES, status=200):
    resp = requests.Response()
    resp.status_code = status
    resp._content = content
    return resp


def make_command(dry_run=False):
    cmd = Command()
    cmd.stdout = OutputWrapper(StringIO())
    cmd.stderr = OutputWrapper(StringIO())
    cmd.dry_run = dry_run
    cmd._image_cache = {}
    return cmd


@pytest.fixture
def index_page(minimal_site):
    return get_blog_index_page()


# ---------------------------------------------------------------------------
# _text helper
# ---------------------------------------------------------------------------


def test_text_missing_tag_returns_empty_string():
    post = _parse_post(_post_xml())
    assert _text(post, "DoesNotExist") == ""


def test_text_present_but_empty_returns_empty_string():
    post = _parse_post(_post_xml())
    assert _text(post, "Excerpt") == ""


def test_text_strips_whitespace():
    post = ElementTree.fromstring("<post><Title>  Padded Title  </Title></post>")
    assert _text(post, "Title") == "Padded Title"


# ---------------------------------------------------------------------------
# handle(): top-level validation and control flow
# ---------------------------------------------------------------------------


def test_missing_xml_file_raises_command_error(tmp_path, index_page):
    with pytest.raises(CommandError, match="File not found"):
        call_command("import_wordpress_blog_posts", str(tmp_path / "nope.xml"))


def test_unknown_locale_raises_command_error(tmp_path, index_page):
    xml_path = _write_xml(tmp_path, _post_xml())
    with pytest.raises(CommandError, match="No Locale found"):
        call_command("import_wordpress_blog_posts", str(xml_path), locale="xx-XX")


def test_missing_blog_index_page_raises_command_error(tmp_path):
    # A real locale exists, but no BlogIndexPage has been created for it.
    LocaleFactory(language_code="fr")
    xml_path = _write_xml(tmp_path, _post_xml())
    with pytest.raises(CommandError, match="No BlogIndexPage found"):
        call_command("import_wordpress_blog_posts", str(xml_path), locale="fr")


def test_unsupported_post_type_is_skipped_and_does_not_abort_other_posts(tmp_path, index_page, monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    xml_path = _write_xml(
        tmp_path,
        _post_xml(id="1", slug="a-page", post_type="page"),
        _post_xml(id="2", slug="a-test-post", post_type="post"),
    )
    out = StringIO()
    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(tmp_path / "redirects.csv"), stdout=out, stderr=err)

    assert not BlogArticlePage.objects.filter(slug="a-page").exists()
    assert BlogArticlePage.objects.filter(slug="a-test-post").exists()
    assert "unsupported PostType 'page'" in err.getvalue()
    assert "Done. 1 imported, 0 skipped, 1 failed." in out.getvalue()


@pytest.mark.parametrize("get_mock_response", [lambda url, timeout: _fake_response()])
def test_successful_import_creates_page_with_expected_fields(tmp_path, index_page, monkeypatch, get_mock_response):
    monkeypatch.setattr("requests.get", get_mock_response)
    xml_path = _write_xml(tmp_path, _post_xml(tags="Privacy|Security"))
    redirects_out = tmp_path / "redirects.csv"

    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(redirects_out), stdout=out)

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.title == "A Test Post"
    assert page.topic.name == "Firefox"
    assert {t.name for t in page.tags.all()} == {"Privacy", "Security"}
    assert page.author.name == "Nick Nguyen"
    assert page.image.title == "Hero Image"
    assert [b.block_type for b in page.content] == ["text"]
    assert "Done. 1 imported, 0 skipped, 0 failed." in out.getvalue()

    with open(redirects_out, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["old_permalink"] == "https://blog.mozilla.org/en/firefox/a-test-post/"
    assert int(rows[0]["new_page_id"]) == page.id


def test_multiple_categories_use_first_as_topic_and_rest_as_tags(tmp_path, index_page, monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    xml_path = _write_xml(tmp_path, _post_xml(categories="Firefox|Privacy", tags="Security"))

    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(tmp_path / "redirects.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.topic.name == "Firefox"
    assert {t.name for t in page.tags.all()} == {"Privacy", "Security"}


def test_blank_categories_fails_the_post_instead_of_leaving_it_without_a_topic(tmp_path, index_page, monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    xml_path = _write_xml(tmp_path, _post_xml(categories=""))

    out = StringIO()
    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(tmp_path / "redirects.csv"), stdout=out, stderr=err)

    assert not BlogArticlePage.objects.filter(slug="a-test-post").exists()
    assert "has no Category" in err.getvalue()
    assert "Done. 0 imported, 0 skipped, 1 failed." in out.getvalue()


def test_first_published_at_is_localized_to_the_default_timezone(tmp_path, index_page, monkeypatch):
    from django.utils.timezone import get_default_timezone

    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    xml_path = _write_xml(tmp_path, _post_xml(date="2020-01-01 09:30:00"))

    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(tmp_path / "redirects.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.first_published_at.tzinfo is not None
    assert page.first_published_at.astimezone(get_default_timezone()).strftime("%H:%M:%S") == "09:30:00"


def test_successful_import_writes_content_warnings_to_stderr(tmp_path, index_page, monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    xml_path = _write_xml(tmp_path, _post_xml(content='<p>Watch:</p><iframe src="https://youtube.com/embed/abc"></iframe>'))

    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(tmp_path / "redirects.csv"), stderr=err)

    assert "https://youtube.com/embed/abc" in err.getvalue()


def test_dry_run_creates_nothing(tmp_path, index_page, monkeypatch):
    calls = []
    monkeypatch.setattr("requests.get", lambda *a, **k: calls.append(1))
    xml_path = _write_xml(tmp_path, _post_xml())
    redirects_out = tmp_path / "redirects.csv"

    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), dry_run=True, redirects_out=str(redirects_out), stdout=out)

    assert BlogArticlePage.objects.count() == 0
    assert Tag.objects.count() == 0
    assert Author.objects.count() == 0
    assert not redirects_out.exists()
    assert not calls, "dry-run must not hit the network"
    assert "[dry-run] importing: A Test Post" in out.getvalue()
    assert "Done. 1 imported, 0 skipped, 0 failed." in out.getvalue()


def test_skip_already_imported_slug(tmp_path, index_page, monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    xml_path = _write_xml(tmp_path, _post_xml())
    redirects_out = tmp_path / "redirects.csv"

    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(redirects_out))
    assert BlogArticlePage.objects.count() == 1

    redirects_out.unlink()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(redirects_out), stdout=out)

    assert BlogArticlePage.objects.count() == 1
    assert "skip (already imported): a-test-post" in out.getvalue()
    assert "Done. 0 imported, 1 skipped, 0 failed." in out.getvalue()
    # Nothing new to redirect, so the CSV is not (re)written.
    assert not redirects_out.exists()


def test_one_post_failure_does_not_affect_others_or_leave_partial_state(tmp_path, index_page, monkeypatch):
    """A post whose image download raises an unexpected error rolls back cleanly
    (no orphaned Tag/Author/page) without preventing later posts from importing."""

    def flaky_get(url, timeout=60):
        if url == "https://example.com/broken.jpg":
            raise ValueError("boom")
        return _fake_response()

    monkeypatch.setattr("requests.get", flaky_get)

    xml_path = _write_xml(
        tmp_path,
        _post_xml(id="1", slug="post-one", title="Post One", image_url="https://example.com/broken.jpg", categories="Broken Topic"),
        _post_xml(id="2", slug="post-two", title="Post Two", categories="Firefox"),
    )
    out = StringIO()
    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), redirects_out=str(tmp_path / "redirects.csv"), stdout=out, stderr=err)

    assert not BlogArticlePage.objects.filter(slug="post-one").exists()
    assert BlogArticlePage.objects.filter(slug="post-two").exists()
    # The failed post's topic snippet must not have been left behind by the rolled-back transaction.
    assert not Tag.objects.filter(slug="broken-topic").exists()
    assert Tag.objects.filter(slug="firefox").exists()
    assert "failed to import 'post-one'" in err.getvalue()
    assert "Done. 1 imported, 0 skipped, 1 failed." in out.getvalue()


# ---------------------------------------------------------------------------
# _get_or_create_snippet / _get_or_create_author
# ---------------------------------------------------------------------------


def test_get_or_create_snippet_blank_name_returns_none():
    cmd = make_command()
    assert cmd._get_or_create_snippet(Tag, "   ", Locale.get_default()) is None


def test_get_or_create_snippet_reuses_existing_by_slug():
    cmd = make_command()
    locale = Locale.get_default()
    first = cmd._get_or_create_snippet(Tag, "Privacy", locale)
    second = cmd._get_or_create_snippet(Tag, "Privacy", locale)
    assert first.pk == second.pk
    assert Tag.objects.count() == 1


def test_get_or_create_author_uses_first_and_last_name():
    cmd = make_command()
    post = _parse_post(_post_xml(author_first="Nick", author_last="Nguyen", author_username="someone@example.com"))
    author = cmd._get_or_create_author(post, Locale.get_default())
    assert author.name == "Nick Nguyen"


def test_get_or_create_author_falls_back_to_username():
    cmd = make_command()
    post = _parse_post(_post_xml(author_first="", author_last="", author_username="someone@example.com"))
    author = cmd._get_or_create_author(post, Locale.get_default())
    assert author.name == "someone@example.com"


def test_get_or_create_author_returns_none_when_all_blank():
    cmd = make_command()
    post = _parse_post(_post_xml(author_first="", author_last="", author_username=""))
    assert cmd._get_or_create_author(post, Locale.get_default()) is None


# ---------------------------------------------------------------------------
# _get_or_create_image
# ---------------------------------------------------------------------------


def test_get_or_create_image_blank_url_returns_none():
    cmd = make_command()
    assert cmd._get_or_create_image("  ", "Some Title") is None


def test_get_or_create_image_reuses_same_filename_within_a_run_without_network_call(monkeypatch):
    calls = []
    monkeypatch.setattr("requests.get", lambda *a, **k: calls.append(1) or _fake_response())
    cmd = make_command()

    first = cmd._get_or_create_image("https://example.com/whatever.png", "First Title")
    second = cmd._get_or_create_image("https://example.com/whatever.png", "A Different Title")

    assert second.pk == first.pk
    assert len(calls) == 1, "the second call for the same filename must not hit the network"


def test_get_or_create_image_does_not_reuse_unrelated_image_with_same_title(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    cmd = make_command()

    first = cmd._get_or_create_image("https://example.com/unrelated.png", "Screenshot")
    second = cmd._get_or_create_image("https://example.com/new-screenshot.png", "Screenshot")

    assert second.pk != first.pk
    assert "new-screenshot" in second.file.name


def test_get_or_create_image_downloads_and_creates(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    cmd = make_command()
    image = cmd._get_or_create_image("https://example.com/path/hero.jpg", "Hero")
    assert image.title == "Hero"
    assert "hero" in image.file.name


def test_get_or_create_image_blank_title_falls_back_to_filename(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    cmd = make_command()
    image = cmd._get_or_create_image("https://example.com/path/my-photo.jpg", "  ")
    assert image.title == "my-photo.jpg"


def test_get_or_create_image_retries_and_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] < 2:
            raise requests.ConnectionError("temporary")
        return _fake_response()

    monkeypatch.setattr("requests.get", flaky)
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)
    cmd = make_command()
    image = cmd._get_or_create_image("https://example.com/hero.jpg", "Hero")
    assert image is not None
    assert calls["n"] == 2


def test_get_or_create_image_gives_up_after_three_attempts(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("dead")))
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)
    cmd = make_command()
    image = cmd._get_or_create_image("https://example.com/hero.jpg", "Hero")
    assert image is None
    assert "could not download image" in cmd.stderr._out.getvalue()


# ---------------------------------------------------------------------------
# _build_content
# ---------------------------------------------------------------------------


def test_build_content_plain_text_becomes_single_text_block():
    cmd = make_command()
    blocks, warnings = cmd._build_content("<p>Hello</p><p>World</p>")
    assert warnings == []
    assert len(blocks) == 1
    assert blocks[0][0] == "text"
    assert "Hello" in blocks[0][1] and "World" in blocks[0][1]


def test_build_content_strips_html_comments():
    cmd = make_command()
    blocks, _ = cmd._build_content("<p>Before</p><!--more--><p>After</p>")
    joined = blocks[0][1]
    assert "more" not in joined
    assert "Before" in joined and "After" in joined


def test_build_content_empty_input_produces_no_blocks():
    cmd = make_command()
    blocks, warnings = cmd._build_content("")
    assert blocks == []
    assert warnings == []


def test_build_content_inline_image_downloaded_becomes_media_block(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    cmd = make_command(dry_run=False)
    blocks, _ = cmd._build_content('<p>Text</p><img src="https://example.com/a.png" alt="Alt">')
    assert [b[0] for b in blocks] == ["text", "media"]
    assert blocks[1][1][0][0] == "image"


def test_build_content_inline_image_in_dry_run_uses_placeholder(monkeypatch):
    called = []
    monkeypatch.setattr("requests.get", lambda *a, **k: called.append(1))
    cmd = make_command(dry_run=True)
    blocks, _ = cmd._build_content('<img src="https://example.com/a.png">')
    assert blocks == [("media", "[dry-run image]")]
    assert not called


def test_build_content_inline_image_download_failure_produces_no_media_block(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("dead")))
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)
    cmd = make_command(dry_run=False)
    blocks, _ = cmd._build_content('<p>Before</p><img src="https://example.com/a.png"><p>After</p>')
    assert [b[0] for b in blocks] == ["text", "text"]


def test_build_content_iframe_becomes_link_with_warning():
    cmd = make_command()
    blocks, warnings = cmd._build_content('<p>Watch:</p><iframe src="https://youtube.com/embed/abc"></iframe>')
    assert len(warnings) == 1
    assert "https://youtube.com/embed/abc" in warnings[0]
    assert [b[0] for b in blocks] == ["text", "text"]
    assert "https://youtube.com/embed/abc" in blocks[1][1]


def test_build_content_caption_shortcode_keeps_only_img(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _fake_response())
    cmd = make_command(dry_run=False)
    html = '[caption id="1"]<img src="https://example.com/a.png" alt="Alt"> A caption describing the image[/caption]'
    blocks, _ = cmd._build_content(html)
    assert [b[0] for b in blocks] == ["media"]


def test_build_content_caption_shortcode_without_img_is_dropped():
    cmd = make_command()
    html = '[caption id="1"]just some text, no image[/caption]<p>Rest</p>'
    blocks, _ = cmd._build_content(html)
    assert len(blocks) == 1
    assert "just some text" not in blocks[0][1]
    assert "Rest" in blocks[0][1]


def test_build_content_pre_tag_becomes_code_block():
    cmd = make_command()
    blocks, _ = cmd._build_content("<p>Before</p><pre>print('hi')</pre><p>After</p>")
    assert [b[0] for b in blocks] == ["text", "code", "text"]
    assert blocks[1][1] == {"code": "print('hi')"}


# ---------------------------------------------------------------------------
# _write_redirects_csv
# ---------------------------------------------------------------------------


def test_write_redirects_csv_writes_header_and_rows(tmp_path):
    cmd = make_command()
    path = tmp_path / "out.csv"
    cmd._write_redirects_csv(str(path), [("1", "https://old.example.com/a/", 42, "https://new.example.com/a/")])

    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["wp_id", "old_permalink", "new_page_id", "new_page_path"]
    assert rows[1] == ["1", "https://old.example.com/a/", "42", "https://new.example.com/a/"]
    assert "Wrote 1 redirect mappings to" in cmd.stdout._out.getvalue()
