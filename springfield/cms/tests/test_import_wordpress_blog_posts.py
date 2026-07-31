# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import base64
import csv
import re
import zlib
from io import BytesIO, StringIO
from xml.etree import ElementTree

from django.core.management import call_command
from django.core.management.base import CommandError, OutputWrapper

import pytest
import requests
import responses
from bs4 import BeautifulSoup
from PIL import Image
from wagtail.models import Locale

from springfield.cms.fixtures.blog_fixtures import get_blog_index_page
from springfield.cms.management.commands.import_wordpress_blog_posts import (
    Command,
    IncrementalCsv,
    element_text,
    image_description,
    parse_categories,
    parse_content,
)
from springfield.cms.models import BlogArticlePage, SpringfieldImage
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
    # The real export repeats the featured image as the first ImageURL entry.
    "image_featured": "https://example.com/hero.jpg",
    "image_title": "Hero Image",
    "image_alt_text": "",
    "image_description": "",
    "image_caption": "",
    "categories": "Firefox",
    "tags": "",
    "authors": "",
    "author_username": "someone@example.com",
    "author_first": "Nick",
    "author_last": "Nguyen",
}


def post_xml(**overrides):
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
        <ImageCaption>{values["image_caption"]}</ImageCaption>
        <ImageDescription>{values["image_description"]}</ImageDescription>
        <ImageAltText>{values["image_alt_text"]}</ImageAltText>
        <ImageFeatured>{values["image_featured"]}</ImageFeatured>
        <Categories>{values["categories"]}</Categories>
        <Tags>{values["tags"]}</Tags>
        <Authors>{values["authors"]}</Authors>
        <AuthorUsername>{values["author_username"]}</AuthorUsername>
        <AuthorFirstName>{values["author_first"]}</AuthorFirstName>
        <AuthorLastName>{values["author_last"]}</AuthorLastName>
        <Slug>{values["slug"]}</Slug>
    </post>
    """


def write_xml(tmp_path, *posts, filename="posts.xml"):
    path = tmp_path / filename
    path.write_text(f"<data>{''.join(posts)}</data>")
    return path


def parse_post(xml_string):
    """Parse a single <post> fragment (as produced by post_xml) into an ElementTree Element."""
    return ElementTree.fromstring(f"<data>{xml_string}</data>").find("post")


ANY_URL = re.compile(r"https?://.+")


def png_for(url):
    """A small valid PNG whose bytes are particular to `url`."""
    checksum = zlib.crc32(url.encode())
    colour = (checksum & 0xFF, checksum >> 8 & 0xFF, checksum >> 16 & 0xFF)
    buffer = BytesIO()
    Image.new("RGB", (2, 2), colour).save(buffer, "PNG")
    return buffer.getvalue()


def mock_image_downloads(url=ANY_URL, content=None):
    """Serve a valid PNG for the image downloads the import makes, any URL by default.

    Each URL gets bytes of its own, as a real media server would. That matters because the import
    identifies an image by its contents: serving one fixed PNG everywhere would make every
    unrelated image in a test look like the same file. Pass `content` where the bytes are the
    point - two URLs standing in for one file, say.
    """

    def serve(request):
        return 200, {"Content-Type": "image/png"}, content if content is not None else png_for(request.url)

    responses.add_callback(responses.GET, url, callback=serve)


# The command tries each download three times before giving up.
DOWNLOAD_ATTEMPTS = 3


def mock_failed_downloads(url=ANY_URL, error=None):
    """Fail every download attempt for `url`, as a dead media URL would.

    One registration per attempt: responses hands out an unused match in preference to a used
    one, so with fewer a later attempt would fall through to a broader mock and succeed.
    """
    for _ in range(DOWNLOAD_ATTEMPTS):
        responses.add(responses.GET, url, body=error or requests.ConnectionError("dead"))


def make_command(dry_run=False):
    cmd = Command()
    cmd.stdout = OutputWrapper(StringIO())
    cmd.stderr = OutputWrapper(StringIO())
    cmd.dry_run = dry_run
    cmd.image_cache = {}
    return cmd


@pytest.fixture(autouse=True)
def run_in_tmp_path(tmp_path, monkeypatch):
    """Run every test from a temp directory.

    Both CSV options default to a relative path, so a test that doesn't override them would
    otherwise drop files in whatever directory pytest was started from.
    """
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def no_retry_backoff(monkeypatch):
    """Skip the 2s/4s sleeps the command waits between download retries."""
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)


@pytest.fixture
def index_page(minimal_site):
    # The command defaults to looking up the blog index by slug="blog".
    return get_blog_index_page(slug="blog")


# ---------------------------------------------------------------------------
# element_text helper
# ---------------------------------------------------------------------------


def test_text_missing_tag_returns_empty_string():
    post = parse_post(post_xml())
    assert element_text(post, "DoesNotExist") == ""


def test_text_present_but_empty_returns_empty_string():
    post = parse_post(post_xml())
    assert element_text(post, "Excerpt") == ""


def test_text_strips_whitespace():
    post = ElementTree.fromstring("<post><Title>  Padded Title  </Title></post>")
    assert element_text(post, "Title") == "Padded Title"


# ---------------------------------------------------------------------------
# parse_categories helper
# ---------------------------------------------------------------------------


def test_parse_categories_keeps_every_hierarchy_level_leaf_first():
    # Leaf is first (it becomes the topic); ancestors follow (they become tags).
    assert parse_categories("Our Work>News") == ["News", "Our Work"]


def test_parse_categories_keeps_every_level_of_a_deep_hierarchy():
    assert parse_categories("Our Work>AI>AI Tech") == ["AI Tech", "Our Work", "AI"]


def test_parse_categories_drops_bare_firefox_when_other_categories_exist():
    assert parse_categories("Firefox|Our Work>News") == ["News", "Our Work"]


def test_parse_categories_drops_firefox_as_a_hierarchy_ancestor():
    assert parse_categories("Firefox>Tips and Tricks") == ["Tips and Tricks"]


def test_parse_categories_keeps_firefox_when_it_is_the_only_category():
    assert parse_categories("Firefox") == ["Firefox"]


def test_parse_categories_keeps_firefox_prefixed_subtopics():
    # 'Firefox AI' is a real leaf; only the bare 'Firefox' ancestor is dropped.
    assert parse_categories("Firefox>Firefox AI") == ["Firefox AI"]


def test_parse_categories_decodes_html_entities():
    assert parse_categories("Firefox|Privacy &amp; Security") == ["Privacy & Security"]


def test_parse_categories_across_pipes_is_topic_first_then_tags():
    assert parse_categories("Our Work>AI>AI Tech|Firefox>Firefox AI") == ["AI Tech", "Our Work", "AI", "Firefox AI"]


def test_parse_categories_dedupes_repeated_names():
    assert parse_categories("Firefox>News|Our Work>News") == ["News", "Our Work"]


def test_parse_categories_empty_input_returns_empty_list():
    assert parse_categories("") == []


# ---------------------------------------------------------------------------
# handle(): top-level validation and control flow
# ---------------------------------------------------------------------------


def test_missing_xml_file_raises_command_error(tmp_path, index_page):
    with pytest.raises(CommandError, match="File not found"):
        call_command("import_wordpress_blog_posts", str(tmp_path / "nope.xml"))


def test_unknown_locale_raises_command_error(tmp_path, index_page):
    xml_path = write_xml(tmp_path, post_xml())
    with pytest.raises(CommandError, match="No Locale found"):
        call_command("import_wordpress_blog_posts", str(xml_path), locale="xx-XX")


def test_missing_blog_index_page_raises_command_error(tmp_path):
    # A real locale exists, but no BlogIndexPage has been created for it.
    LocaleFactory(language_code="fr")
    xml_path = write_xml(tmp_path, post_xml())
    with pytest.raises(CommandError, match="No BlogIndexPage found"):
        call_command("import_wordpress_blog_posts", str(xml_path), locale="fr")


@responses.activate
def test_unsupported_post_type_is_skipped_and_does_not_abort_other_posts(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(
        tmp_path,
        post_xml(id="1", slug="a-page", post_type="page"),
        post_xml(id="2", slug="a-test-post", post_type="post"),
    )
    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stdout=out)

    assert not BlogArticlePage.objects.filter(slug="a-page").exists()
    assert BlogArticlePage.objects.filter(slug="a-test-post").exists()
    # A non-'post' entry is an expected skip, not a failure.
    assert "skip (unsupported PostType 'page'): a-page" in out.getvalue()
    assert "Done. 1 imported, 1 skipped, 0 failed." in out.getvalue()


@responses.activate
def test_successful_import_creates_page_with_expected_fields(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(tags="Privacy|Security"))
    url_map_out = tmp_path / "url_map.csv"

    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(url_map_out), stdout=out)

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.title == "A Test Post"
    assert page.display_image is True
    assert page.topic.name == "Firefox"
    assert {t.name for t in page.tags.all()} == {"Privacy", "Security"}
    assert page.author.name == "Nick Nguyen"
    assert page.image.title == "Hero Image"
    assert [b.block_type for b in page.content] == ["text"]
    assert "Done. 1 imported, 0 skipped, 0 failed." in out.getvalue()

    with open(url_map_out, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["old_url"] == "https://blog.mozilla.org/en/firefox/a-test-post/"
    # The new URL must be absolute so the blog.mozilla.org team can redirect to it.
    assert rows[0]["new_url"] == page.full_url
    assert rows[0]["new_url"].startswith("http")


@responses.activate
def test_hero_image_comes_from_image_featured_not_image_url(tmp_path, index_page):
    """ImageURL lists every image in the post; only ImageFeatured names the hero."""
    mock_image_downloads()
    xml_path = write_xml(
        tmp_path,
        post_xml(
            image_url="https://example.com/first.png|https://example.com/second.gif",
            image_featured="https://example.com/first.png",
            image_title="First Image|Second Image",
        ),
    )

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert "first" in page.image.file.name
    # The Image* fields are parallel lists, so the hero's title is the first entry.
    assert page.image.title == "First Image"
    assert [call.request.url for call in responses.calls] == ["https://example.com/first.png"]


@responses.activate
def test_blank_image_featured_imports_the_post_without_a_hero_image(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(
        tmp_path,
        post_xml(image_url="https://example.com/body-image.png", image_featured=""),
    )

    out = StringIO()
    err = StringIO()
    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        url_map_out=str(tmp_path / "url_map.csv"),
        stdout=out,
        stderr=err,
    )

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.image is None
    assert "Done. 1 imported, 0 skipped, 0 failed." in out.getvalue()
    # A post with no featured image is expected, not a problem worth warning about.
    assert err.getvalue() == ""
    assert len(responses.calls) == 0, "the images listed in ImageURL are not the hero image"


@responses.activate
def test_captioned_image_is_imported_as_an_image_caption_block(tmp_path, index_page):
    mock_image_downloads()
    content = (
        "<p>Intro.</p>"
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt="A screenshot"/>'
        '<figcaption class="wp-element-caption">Credit: <em>Mozilla</em></figcaption></figure>'
        '<img src="https://example.com/b.png" alt="No caption here">'
    )
    xml_path = write_xml(tmp_path, post_xml(content=content))

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert [block.block_type for block in page.content] == ["text", "image_caption", "media"]

    captioned = page.content[1].value
    assert str(captioned["caption"]) == "<p>Credit: <em>Mozilla</em></p>"
    assert captioned["image"]["image"].title == "A screenshot"


@responses.activate
def test_categories_topic_is_leaf_and_other_levels_become_tags(tmp_path, index_page):
    mock_image_downloads()
    # Bare 'Firefox' is dropped; the leaf of the first remaining category is the topic;
    # every other hierarchy level (plus the <Tags> field) becomes a tag.
    xml_path = write_xml(
        tmp_path,
        post_xml(categories="Firefox|Our Work>AI>AI Tech|Firefox>Firefox AI", tags="Security"),
    )

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.topic.name == "AI Tech"
    assert {t.name for t in page.tags.all()} == {"Our Work", "AI", "Firefox AI", "Security"}


@responses.activate
def test_blank_categories_fails_the_post_instead_of_leaving_it_without_a_topic(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(categories=""))

    out = StringIO()
    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stdout=out, stderr=err)

    assert not BlogArticlePage.objects.filter(slug="a-test-post").exists()
    assert "has no Category" in err.getvalue()
    assert "Done. 0 imported, 0 skipped, 1 failed." in out.getvalue()


@responses.activate
def test_first_published_at_is_localized_to_the_default_timezone(tmp_path, index_page):
    from django.utils.timezone import get_default_timezone

    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(date="2020-01-01 09:30:00"))

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.first_published_at.tzinfo is not None
    assert page.first_published_at.astimezone(get_default_timezone()).strftime("%H:%M:%S") == "09:30:00"


@responses.activate
def test_successful_import_writes_content_warnings_to_stderr(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(content='<p>Watch:</p><iframe src="https://player.vimeo.com/video/123"></iframe>'))

    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stderr=err)

    assert "https://player.vimeo.com/video/123" in err.getvalue()


@responses.activate
def test_warnings_are_written_to_csv_against_the_post_they_came_from(tmp_path, index_page):
    mock_image_downloads()
    content = (
        '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">'
        "https://www.tiktok.com/@mozilla/video/123</div></figure>"
        '<figure class="wp-block-gallery">'
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt=""/></figure>'
        '<figure class="wp-block-image"><img src="https://example.com/b.png" alt=""/></figure>'
        "<figcaption>Gallery caption</figcaption></figure>"
    )
    xml_path = write_xml(tmp_path, post_xml(content=content))
    warnings_out = tmp_path / "warnings.csv"

    out = StringIO()
    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        url_map_out=str(tmp_path / "url_map.csv"),
        warnings_out=str(warnings_out),
        stdout=out,
    )

    page = BlogArticlePage.objects.get(slug="a-test-post")
    with open(warnings_out, newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert [(row["type"], row["warning"]) for row in rows] == [
        ("embed", "https://www.tiktok.com/@mozilla/video/123 is not a YouTube video - linked as plain text instead of a video block"),
        ("caption", "caption 'Gallery caption' describes a gallery of 2 images - dropped"),
        ("alt-text", "2 images imported without alt text - add descriptions in the image library"),
    ]
    for row in rows:
        assert row["wp_id"] == "1"
        assert row["title"] == "A Test Post"
        assert row["old_url"] == "https://blog.mozilla.org/en/firefox/a-test-post/"
        assert row["new_url"] == page.full_url
    assert f"Wrote 3 warnings to {warnings_out}" in out.getvalue()


@responses.activate
def test_failed_image_download_is_recorded_in_the_warnings_csv(tmp_path, index_page, no_retry_backoff):
    """A dead image URL only reached stderr before, which is the easiest warning of all to miss."""

    # One failure per attempt, registered ahead of the catch-all, so this URL fails outright.
    mock_failed_downloads("https://example.com/dead.png")
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(content='<p>Text</p><img src="https://example.com/dead.png" alt="Alt">'))
    warnings_out = tmp_path / "warnings.csv"

    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        url_map_out=str(tmp_path / "url_map.csv"),
        warnings_out=str(warnings_out),
    )

    with open(warnings_out, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert "could not download image https://example.com/dead.png" in rows[0]["warning"]
    assert rows[0]["new_url"] == BlogArticlePage.objects.get(slug="a-test-post").full_url


@responses.activate
def test_failed_post_records_its_warnings_and_the_failure(tmp_path, index_page):
    """A failed post has no page to inspect, so the CSV is the only trace of what happened."""
    mock_image_downloads()
    content = '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://www.tiktok.com/@mozilla/video/123</div></figure>'
    # A post with no Category fails, after its content has already raised a warning.
    xml_path = write_xml(tmp_path, post_xml(content=content, categories=""))
    warnings_out = tmp_path / "warnings.csv"

    out = StringIO()
    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        url_map_out=str(tmp_path / "url_map.csv"),
        warnings_out=str(warnings_out),
        stdout=out,
    )

    assert "Done. 0 imported, 0 skipped, 1 failed." in out.getvalue()
    with open(warnings_out, newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert [(row["type"], row["warning"]) for row in rows] == [
        ("embed", "https://www.tiktok.com/@mozilla/video/123 is not a YouTube video - linked as plain text instead of a video block"),
        ("failure", "post failed to import: post 'a-test-post' has no Category - BlogArticlePage.topic is required and cannot be blank"),
    ]
    # There is no page to link to, but the original post is still identified.
    for row in rows:
        assert row["new_url"] == ""
        assert row["old_url"] == "https://blog.mozilla.org/en/firefox/a-test-post/"


@responses.activate
def test_warnings_from_a_failed_post_do_not_leak_into_the_next_one(tmp_path, index_page):
    mock_image_downloads()
    failing_content = '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://www.tiktok.com/@mozilla/video/123</div></figure>'
    xml_path = write_xml(
        tmp_path,
        post_xml(id="1", slug="post-one", content=failing_content, categories=""),
        post_xml(id="2", slug="post-two", categories="Firefox"),
    )
    warnings_out = tmp_path / "warnings.csv"

    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        url_map_out=str(tmp_path / "url_map.csv"),
        warnings_out=str(warnings_out),
    )

    with open(warnings_out, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert {row["wp_id"] for row in rows} == {"1"}, "post-two imported cleanly and owns no warnings"


@responses.activate
def test_no_warnings_csv_is_written_when_a_post_has_no_warnings(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml())
    warnings_out = tmp_path / "warnings.csv"

    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        url_map_out=str(tmp_path / "url_map.csv"),
        warnings_out=str(warnings_out),
    )

    assert not warnings_out.exists()


@responses.activate
def test_dry_run_writes_no_warnings_csv(tmp_path, index_page):
    mock_image_downloads()
    content = '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://www.tiktok.com/@mozilla/video/123</div></figure>'
    xml_path = write_xml(tmp_path, post_xml(content=content))
    warnings_out = tmp_path / "warnings.csv"

    err = StringIO()
    call_command(
        "import_wordpress_blog_posts",
        str(xml_path),
        "--dry-run",
        url_map_out=str(tmp_path / "url_map.csv"),
        warnings_out=str(warnings_out),
        stderr=err,
    )

    # --dry-run writes nothing, but the warning still reaches the operator on stderr.
    assert not warnings_out.exists()
    assert "tiktok.com" in err.getvalue()


@responses.activate
def test_youtube_iframe_is_imported_as_a_video_block(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(content='<p>Watch:</p><iframe src="https://www.youtube.com/embed/abc123"></iframe>'))

    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stderr=err)

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert [block.block_type for block in page.content] == ["text", "media"]
    video = page.content[1].value[0]
    assert video.block_type == "video"
    assert video.value["video_url"] == "https://www.youtube.com/watch?v=abc123"
    assert video.value["alt"] == "A Test Post"
    assert video.value["poster"] is not None
    assert err.getvalue() == "", "a YouTube video no longer needs a warning"


@responses.activate
def test_dry_run_creates_nothing(tmp_path, index_page):
    xml_path = write_xml(tmp_path, post_xml())
    url_map_out = tmp_path / "url_map.csv"

    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), dry_run=True, url_map_out=str(url_map_out), stdout=out)

    assert BlogArticlePage.objects.count() == 0
    assert Tag.objects.count() == 0
    assert Author.objects.count() == 0
    assert not url_map_out.exists()
    # No responses are registered, so any request would raise rather than be recorded.
    assert len(responses.calls) == 0, "dry-run must not hit the network"
    assert "[dry-run] importing: A Test Post" in out.getvalue()
    assert "Done. 1 would be imported, 0 skipped, 0 failed." in out.getvalue()


@responses.activate
def test_links_to_other_posts_in_the_import_point_at_their_new_pages(tmp_path, index_page):
    """These posts cross-link heavily; left alone the links send the reader back to WordPress."""
    mock_image_downloads()
    linking = post_xml(
        id="1",
        slug="post-one",
        content='<p>See <a href="https://blog.mozilla.org/blog/2018/03/29/add-ons-manager/">the add-ons manager</a>.</p>',
    )
    target = post_xml(id="2", slug="add-ons-manager", title="The Add-ons Manager")
    xml_path = write_xml(tmp_path, linking, target)

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    html = str(BlogArticlePage.objects.get(slug="post-one").content[0].value)
    assert f'href="{index_page.url}add-ons-manager/"' in html
    assert "blog.mozilla.org" not in html


@responses.activate
def test_links_to_pages_outside_the_import_are_left_alone(tmp_path, index_page):
    mock_image_downloads()
    content = '<p>See <a href="https://blog.mozilla.org/firefox/some-post-we-are-not-importing/">this</a>.</p>'
    xml_path = write_xml(tmp_path, post_xml(content=content))

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    html = str(BlogArticlePage.objects.get(slug="a-test-post").content[0].value)
    assert 'href="https://blog.mozilla.org/firefox/some-post-we-are-not-importing/"' in html


def test_dry_run_reports_a_post_that_would_fail(tmp_path, index_page):
    """A dry run is a preview, so the check that fails a post has to run in it too."""
    xml_path = write_xml(tmp_path, post_xml(categories=""))
    err = StringIO()
    out = StringIO()

    call_command("import_wordpress_blog_posts", str(xml_path), dry_run=True, url_map_out=str(tmp_path / "url_map.csv"), stdout=out, stderr=err)

    assert "has no Category" in err.getvalue()
    assert BlogArticlePage.objects.count() == 0
    assert "Done. 0 would be imported, 0 skipped, 1 failed." in out.getvalue()


@responses.activate
def test_url_map_generated_on_a_local_site_says_so(tmp_path, index_page):
    """The map is for the blog.mozilla.org team's redirects, so localhost rows are no use to them."""
    mock_image_downloads()
    from wagtail.models import Site

    Site.objects.filter(is_default_site=True).update(hostname="localhost", port=8000)
    xml_path = write_xml(tmp_path, post_xml())
    out = StringIO()

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stdout=out)

    assert "localhost" in out.getvalue()
    assert "regenerate" in out.getvalue().lower()


@responses.activate
def test_skip_already_imported_slug(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml())
    url_map_out = tmp_path / "url_map.csv"

    out = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(url_map_out))
    assert BlogArticlePage.objects.count() == 1

    url_map_out.unlink()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(url_map_out), stdout=out)

    assert BlogArticlePage.objects.count() == 1
    assert "skip (already imported): a-test-post" in out.getvalue()
    assert "Done. 0 imported, 1 skipped, 0 failed." in out.getvalue()
    # Nothing new to redirect, so the CSV is not (re)written.
    assert not url_map_out.exists()


@responses.activate
def test_one_post_failure_does_not_affect_others_or_leave_partial_state(tmp_path, index_page):
    """A post whose image download raises an unexpected error rolls back cleanly
    (no orphaned Tag/Author/page) without preventing later posts from importing."""

    # A ValueError is not a RequestException, so it is not retried and not swallowed.
    mock_failed_downloads("https://example.com/broken.jpg", error=ValueError("boom"))
    mock_image_downloads()

    xml_path = write_xml(
        tmp_path,
        post_xml(id="1", slug="post-one", title="Post One", image_featured="https://example.com/broken.jpg", categories="Broken Topic"),
        post_xml(id="2", slug="post-two", title="Post Two", categories="Firefox"),
    )
    out = StringIO()
    err = StringIO()
    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stdout=out, stderr=err)

    assert not BlogArticlePage.objects.filter(slug="post-one").exists()
    assert BlogArticlePage.objects.filter(slug="post-two").exists()
    # The failed post's topic snippet must not have been left behind by the rolled-back transaction.
    assert not Tag.objects.filter(slug="broken-topic").exists()
    assert Tag.objects.filter(slug="firefox").exists()
    assert "failed to import 'post-one'" in err.getvalue()
    assert "Done. 1 imported, 0 skipped, 1 failed." in out.getvalue()


# ---------------------------------------------------------------------------
# get_or_create_snippet / get_or_create_author
# ---------------------------------------------------------------------------


def test_get_or_create_snippet_blank_name_returns_none():
    cmd = make_command()
    assert cmd.get_or_create_snippet(Tag, "   ", Locale.get_default()) is None


def test_get_or_create_snippet_reuses_existing_by_slug():
    cmd = make_command()
    locale = Locale.get_default()
    first = cmd.get_or_create_snippet(Tag, "Privacy", locale)
    second = cmd.get_or_create_snippet(Tag, "Privacy", locale)
    assert first.pk == second.pk
    assert Tag.objects.count() == 1


def test_get_or_create_author_uses_first_and_last_name():
    cmd = make_command()
    post = parse_post(post_xml(author_first="Nick", author_last="Nguyen", author_username="someone@example.com"))
    author = cmd.get_or_create_author(post, Locale.get_default())
    assert author.name == "Nick Nguyen"


def test_get_or_create_author_falls_back_to_username():
    cmd = make_command()
    post = parse_post(post_xml(author_first="", author_last="", author_username="someone@example.com"))
    author = cmd.get_or_create_author(post, Locale.get_default())
    assert author.name == "someone@example.com"


def test_get_or_create_author_returns_none_when_all_blank():
    cmd = make_command()
    post = parse_post(post_xml(author_first="", author_last="", author_username=""))
    assert cmd.get_or_create_author(post, Locale.get_default()) is None


# ---------------------------------------------------------------------------
# get_or_create_image
# ---------------------------------------------------------------------------


def test_get_or_create_image_blank_url_returns_none():
    cmd = make_command()
    assert cmd.get_or_create_image("  ", "Some Title") is None


@responses.activate
def test_get_or_create_image_reuses_the_same_url_within_a_run_without_network_call():
    mock_image_downloads()
    cmd = make_command()

    first = cmd.get_or_create_image("https://example.com/whatever.png", "First Title")
    second = cmd.get_or_create_image("https://example.com/whatever.png", "A Different Title")

    assert second.pk == first.pk
    assert len(responses.calls) == 1, "the second call for the same URL must not hit the network"


@responses.activate
def test_get_or_create_image_does_not_reuse_a_different_url_with_the_same_filename():
    """WordPress names files per upload month, so unrelated posts routinely share a basename."""
    mock_image_downloads()
    cmd = make_command()

    first = cmd.get_or_create_image("https://blog.mozilla.org/files/2024/11/image.png", "First")
    second = cmd.get_or_create_image("https://blog.mozilla.org/files/2025/10/image.png", "Second")

    assert first is not None
    assert second is not None
    assert second.pk != first.pk, "two different files that happen to share a name must not collapse into one image"


@responses.activate
def test_get_or_create_image_does_not_reuse_unrelated_image_with_same_title():
    mock_image_downloads()
    cmd = make_command()

    first = cmd.get_or_create_image("https://example.com/unrelated.png", "Screenshot")
    second = cmd.get_or_create_image("https://example.com/new-screenshot.png", "Screenshot")

    assert second.pk != first.pk
    assert "new-screenshot" in second.file.name


@responses.activate
def test_get_or_create_image_reuses_an_image_whose_contents_already_arrived_in_an_earlier_run():
    """Resuming an import must not add a second copy of a file already in the library.

    The stored name is no guide: Django's storage appends a random suffix when the name is
    taken, so the same source file can end up as 'hero.jpg' one run and 'hero_A1b2c3.jpg' the
    next. The file contents are what identify it.
    """
    # One file served from two URLs, so its contents are what the two calls have in common.
    mock_image_downloads(content=PNG_BYTES)
    first = make_command().get_or_create_image("https://example.com/2024/11/hero.jpg", "Hero")

    second = make_command().get_or_create_image("https://example.com/2025/10/hero.jpg", "Hero Again")

    assert second.pk == first.pk
    assert SpringfieldImage.objects.count() == 1


@responses.activate
def test_get_or_create_image_stores_a_youtube_poster_under_its_video_id():
    """Every YouTube thumbnail URL ends in the same 'hqdefault.jpg', so the id has to go in the name."""
    mock_image_downloads()
    cmd = make_command()

    image = cmd.get_or_create_image("https://img.youtube.com/vi/qxrVsN9kkog/hqdefault.jpg", "A video")

    assert "qxrVsN9kkog" in image.file.name


@responses.activate
def test_get_or_create_image_downloads_and_creates():
    mock_image_downloads()
    cmd = make_command()
    image = cmd.get_or_create_image("https://example.com/path/hero.jpg", "Hero")
    assert image.title == "Hero"
    assert "hero" in image.file.name


@responses.activate
def test_get_or_create_image_blank_title_falls_back_to_filename():
    mock_image_downloads()
    cmd = make_command()
    image = cmd.get_or_create_image("https://example.com/path/my-photo.jpg", "  ")
    assert image.title == "my-photo.jpg"


@responses.activate
def test_get_or_create_image_retries_and_succeeds(no_retry_backoff):
    url = "https://example.com/hero.jpg"
    # Registrations are consumed in order: the first attempt fails, the second succeeds.
    responses.add(responses.GET, url, body=requests.ConnectionError("temporary"))
    responses.add(responses.GET, url, body=PNG_BYTES, content_type="image/png")
    cmd = make_command()
    image = cmd.get_or_create_image(url, "Hero")
    assert image is not None
    assert len(responses.calls) == 2


@responses.activate
def test_get_or_create_image_gives_up_after_three_attempts(no_retry_backoff):
    mock_failed_downloads()
    cmd = make_command()
    image = cmd.get_or_create_image("https://example.com/hero.jpg", "Hero")
    assert image is None
    assert len(responses.calls) == DOWNLOAD_ATTEMPTS
    assert "could not download image" in cmd.stderr._out.getvalue()


# ---------------------------------------------------------------------------
# parse_content (pure HTML -> block specs; no network, no dry-run)
# ---------------------------------------------------------------------------


def test_parse_content_plain_text_becomes_single_text_spec():
    specs, warnings = parse_content("<p>Hello</p><p>World</p>")
    assert warnings == []
    assert len(specs) == 1
    assert specs[0][0] == "text"
    assert "Hello" in specs[0][1] and "World" in specs[0][1]


def test_parse_content_promotes_an_image_alone_in_a_paragraph_to_a_block():
    """WordPress renders such a paragraph as a block-level image, and a block survives editing."""
    specs, warnings = parse_content('<p>Before.</p><p><img src="https://example.com/a.png" alt="A screenshot"></p><p>After.</p>')
    assert warnings == []
    assert specs == [
        ("text", "<p>Before.</p>"),
        ("image", {"src": "https://example.com/a.png", "alt": "A screenshot", "caption": ""}),
        ("text", "<p>After.</p>"),
    ]


def test_parse_content_drops_a_link_that_only_points_at_the_images_own_file():
    """WordPress's 'link to media file' lightbox link goes nowhere useful once the image is ours."""
    html = (
        '<p><a href="https://blog.mozilla.org/wp-content/uploads/2015/11/welcome-en.jpg">'
        '<img src="https://blog.mozilla.org/wp-content/uploads/2015/11/welcome-en.jpg" alt="A screenshot"></a></p>'
    )
    specs, warnings = parse_content(html)
    assert warnings == []
    assert specs == [("image", {"src": "https://blog.mozilla.org/wp-content/uploads/2015/11/welcome-en.jpg", "alt": "A screenshot", "caption": ""})]


def test_parse_content_keeps_an_image_linked_to_a_real_destination_and_warns():
    """A linked banner is a CTA, so the link stays - but the editor will pull the image out of it."""
    html = '<p><a href="https://www.mozilla.org/firefox/new/"><img src="https://example.com/banner.png" alt="Get Firefox"></a></p>'
    specs, warnings = parse_content(html)
    assert [kind for kind, _ in warnings] == ["inline-image"]
    assert 'href="https://www.mozilla.org/firefox/new/"' in specs[0][1]
    assert [kind for kind, _ in specs] == ["text"]


def test_parse_content_keeps_an_image_inside_a_list_item_and_warns():
    """Promoting it would break the list, so it stays put and the operator is told."""
    specs, warnings = parse_content('<div><ul><li>Step one <img src="https://example.com/step.png" alt="Step"></li></ul></div>')
    assert [kind for kind, _ in warnings] == ["inline-image"]
    assert "https://example.com/step.png" in warnings[0][1]
    # The list item is what keeps the image inline, not the layout <div> wrapped around it.
    assert "<li>" in warnings[0][1]
    assert [kind for kind, _ in specs] == ["text"]


def test_parse_content_keeps_an_image_that_shares_its_paragraph_with_text():
    specs, warnings = parse_content('<p>See <img src="https://example.com/icon.png" alt="the icon"> in the toolbar.</p>')
    assert [kind for kind, _ in warnings] == ["inline-image"]
    assert [kind for kind, _ in specs] == ["text"]


def test_parse_content_demotes_h1_section_headings_to_h2():
    """The page title is the page's h1, and Draftail drops an h1 in the body to plain text."""
    specs, _ = parse_content("<h1>For the cozy gamer</h1><p>Body copy.</p>")
    assert specs == [("text", "<h2>For the cozy gamer</h2><p>Body copy.</p>")]


def test_parse_content_leaves_other_heading_levels_where_they_are():
    """Only h1 moves: demoting the whole tree would push real sections down for no reason."""
    specs, _ = parse_content("<h2>Section</h2><h3>Subsection</h3><h4>Detail</h4>")
    assert specs == [("text", "<h2>Section</h2><h3>Subsection</h3><h4>Detail</h4>")]


def test_parse_content_does_not_rewrite_headings_inside_a_code_block():
    specs, _ = parse_content("<pre>document.querySelector('h1')</pre>")
    assert specs == [("code", {"code": "document.querySelector('h1')"})]


def test_parse_content_embed_shortcode_becomes_a_video_spec():
    """The older posts wrap a video URL in [embed] rather than a Gutenberg embed figure."""
    specs, warnings = parse_content("<p>Watch:</p>\n\n[embed]https://www.youtube.com/watch?v=oKprr3tEBew[/embed]\n\n<p>After.</p>")
    assert warnings == []
    assert [spec[0] for spec in specs] == ["text", "video", "text"]
    assert specs[1][1] == {"url": "https://www.youtube.com/watch?v=oKprr3tEBew", "alt": ""}
    assert "[embed]" not in specs[0][1] and "[embed]" not in specs[2][1]


def test_parse_content_embed_shortcode_for_another_provider_becomes_a_link_with_a_warning():
    specs, warnings = parse_content("[embed]https://player.vimeo.com/video/123[/embed]")
    assert [kind for kind, _ in warnings] == ["embed"]
    assert specs == [("text", '<p><a href="https://player.vimeo.com/video/123">Watch video</a></p>')]


def test_parse_content_bare_text_separated_by_blank_lines_becomes_paragraphs():
    """Classic posts hold no <p> at all - WordPress adds them at render time, so the import must."""
    specs, _ = parse_content("First paragraph.\n\nSecond paragraph.\n\nThird.")
    assert specs == [("text", "<p>First paragraph.</p><p>Second paragraph.</p><p>Third.</p>")]


def test_parse_content_wraps_a_single_run_of_bare_text_in_a_paragraph():
    specs, _ = parse_content("Just the one paragraph.")
    assert specs == [("text", "<p>Just the one paragraph.</p>")]


def test_parse_content_gives_a_bolded_pseudo_heading_its_own_paragraph():
    """These posts mark their section headings with <strong> on a line of its own."""
    specs, _ = parse_content("<strong>Private Browsing</strong>\n\nWe first added Private Browsing.")
    assert specs == [("text", "<p><strong>Private Browsing</strong></p><p>We first added Private Browsing.</p>")]


def test_parse_content_wraps_bare_text_that_runs_into_a_list():
    specs, _ = parse_content("<b>More information:</b>\n<ul><li>Release notes</li></ul>")
    assert specs == [("text", "<p><b>More information:</b></p><ul><li>Release notes</li></ul>")]


def test_parse_content_keeps_inline_markup_inside_the_paragraph_it_belongs_to():
    specs, _ = parse_content('Read the <a href="https://example.com">release notes</a> for more.\n\nNext.')
    assert specs == [("text", '<p>Read the <a href="https://example.com">release notes</a> for more.</p><p>Next.</p>')]


def test_parse_content_leaves_existing_block_markup_alone():
    """Gutenberg posts already carry their own markup, which must not be wrapped a second time."""
    specs, _ = parse_content("<p>One</p>\n\n<ul><li>Two</li></ul>\n\n<h2>Three</h2>")
    assert specs == [("text", "<p>One</p><ul><li>Two</li></ul><h2>Three</h2>")]


def test_parse_content_strips_html_comments():
    specs, _ = parse_content("<p>Before</p><!--more--><p>After</p>")
    joined = specs[0][1]
    assert "more" not in joined
    assert "Before" in joined and "After" in joined


def test_parse_content_empty_input_produces_no_specs():
    specs, warnings = parse_content("")
    assert specs == []
    assert warnings == []


@responses.activate
def test_parse_content_inline_image_becomes_image_spec_without_downloading():
    specs, _ = parse_content('<p>Text</p><img src="https://example.com/a.png" alt="Alt">')
    assert specs == [("text", "<p>Text</p>"), ("image", {"src": "https://example.com/a.png", "alt": "Alt", "caption": ""})]
    assert len(responses.calls) == 0, "parsing must not hit the network"


def test_parse_content_youtube_iframe_becomes_video_spec():
    specs, warnings = parse_content('<p>Watch:</p><iframe src="https://www.youtube.com/embed/abc123?rel=0"></iframe>')
    assert warnings == []
    assert [spec[0] for spec in specs] == ["text", "video"]
    # /embed/ URLs are rewritten to the watch form, which is what oEmbed and the video block expect.
    assert specs[1][1]["url"] == "https://www.youtube.com/watch?v=abc123"
    assert specs[1][1]["alt"] == ""


def test_parse_content_non_youtube_iframe_becomes_link_with_warning():
    specs, warnings = parse_content('<p>Watch:</p><iframe src="https://player.vimeo.com/video/123"></iframe>')
    assert len(warnings) == 1
    assert "https://player.vimeo.com/video/123" in warnings[0][1]
    assert [spec[0] for spec in specs] == ["text", "text"]
    assert specs[1][1] == '<p><a href="https://player.vimeo.com/video/123">Watch video</a></p>'


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://youtu.be/kT86zqVzqOo", "https://www.youtube.com/watch?v=kT86zqVzqOo"),
        ("https://youtu.be/2CT-zB6AO6k?list=PLFlAJDI87Jg", "https://www.youtube.com/watch?v=2CT-zB6AO6k"),
        ("https://www.youtube.com/watch?v=eILW72MxJmU", "https://www.youtube.com/watch?v=eILW72MxJmU"),
        ("https://www.youtube.com/embed/8VoheBpsLoY", "https://www.youtube.com/watch?v=8VoheBpsLoY"),
    ],
)
def test_parse_content_youtube_embed_block_becomes_video_spec(url, expected):
    html = f'<figure class="wp-block-embed is-type-video"><div class="wp-block-embed__wrapper">{url}</div></figure>'
    specs, warnings = parse_content(html)
    assert warnings == []
    assert [spec[0] for spec in specs] == ["video"]
    assert specs[0][1]["url"] == expected


def test_parse_content_youtube_embed_block_caption_becomes_alt_text():
    html = (
        '<figure class="wp-block-embed is-type-video"><div class="wp-block-embed__wrapper">https://youtu.be/kT86zqVzqOo</div>'
        "<figcaption>Introducing new Colorways for Firefox 94</figcaption></figure>"
    )
    specs, warnings = parse_content(html)
    assert warnings == [], "the caption is kept as the video's alt text, so nothing is dropped"
    assert [spec[0] for spec in specs] == ["video"]
    assert specs[0][1]["alt"] == "Introducing new Colorways for Firefox 94"


def test_parse_content_non_youtube_embed_block_becomes_a_link_with_warning():
    """A rich text <embed> is no use for a provider outside Wagtail's oEmbed list: it resolves
    to nothing and leaves an empty paragraph on the page, so these become plain links."""
    html = (
        '<figure class="wp-block-embed is-type-video"><div class="wp-block-embed__wrapper">'
        "https://www.tiktok.com/@mozilla/video/6966371868643298566</div></figure>"
    )
    specs, warnings = parse_content(html)
    assert [spec[0] for spec in specs] == ["text"]
    assert "embedtype" not in specs[0][1]
    assert specs[0][1] == '<p><a href="https://www.tiktok.com/@mozilla/video/6966371868643298566">Watch video</a></p>'
    assert len(warnings) == 1
    assert "tiktok.com" in warnings[0][1]


def test_parse_content_embed_fallback_link_drops_tracking_parameters():
    """WordPress captured these from share links, so the query is tracking, not addressing."""
    html = (
        '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">'
        "https://www.tiktok.com/@mozilla/video/123?_d=abc&amp;checksum=def&amp;timestamp=1633557299#frag</div></figure>"
    )
    specs, _ = parse_content(html)
    assert specs[0][1] == '<p><a href="https://www.tiktok.com/@mozilla/video/123">Watch video</a></p>'


def test_parse_content_embed_fallback_link_is_escaped():
    html = '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://example.com/a&amp;b/video</div></figure>'
    specs, _ = parse_content(html)
    assert specs[0][1] == '<p><a href="https://example.com/a&amp;b/video">Watch video</a></p>'


def test_parse_content_caption_shortcode_captures_caption():
    html = '[caption id="1"]<img src="https://example.com/a.png" alt="Alt"> A caption describing the image[/caption]'
    specs, _ = parse_content(html)
    assert [spec[0] for spec in specs] == ["image"]
    assert specs[0][1]["src"] == "https://example.com/a.png"
    assert specs[0][1]["caption"] == "<p>A caption describing the image</p>"


def test_parse_content_caption_shortcode_without_caption_text_has_no_caption():
    specs, _ = parse_content('[caption id="1"]<img src="https://example.com/a.png" alt="Alt">[/caption]')
    assert [spec[0] for spec in specs] == ["image"]
    assert specs[0][1]["caption"] == ""


def test_parse_content_figure_figcaption_captures_caption_with_inline_markup():
    html = (
        '<figure class="wp-block-image size-large">'
        '<img src="https://example.com/a.png" alt="Alt" class="wp-image-1"/>'
        '<figcaption class="wp-element-caption">Recent work. <em>Courtesy: <a href="https://example.com/x">source</a></em></figcaption>'
        "</figure>"
    )
    specs, warnings = parse_content(html)
    assert warnings == []
    assert [spec[0] for spec in specs] == ["image"]
    assert specs[0][1]["src"] == "https://example.com/a.png"
    assert specs[0][1]["alt"] == "Alt"
    assert specs[0][1]["caption"] == '<p>Recent work. <em>Courtesy: <a href="https://example.com/x">source</a></em></p>'


def test_parse_content_figure_with_linked_image_still_captures_caption():
    html = (
        '<figure class="wp-block-image">'
        '<a href="https://example.com/full.png"><img src="https://example.com/a.png" alt=""/></a>'
        "<figcaption>Click to enlarge</figcaption>"
        "</figure>"
    )
    specs, _ = parse_content(html)
    assert [spec[0] for spec in specs] == ["image"]
    assert specs[0][1]["src"] == "https://example.com/a.png"
    assert specs[0][1]["caption"] == "<p>Click to enlarge</p>"


def test_parse_content_figure_without_figcaption_becomes_image_without_caption():
    """A figure-wrapped image still becomes an image spec, so the file is downloaded
    into Wagtail rather than left hotlinked inside a text block."""
    html = '<figure class="wp-block-image"><img src="https://example.com/a.png" alt="Alt"/></figure>'
    specs, warnings = parse_content(html)
    assert warnings == []
    assert specs == [("image", {"src": "https://example.com/a.png", "alt": "Alt", "caption": ""})]


def test_parse_content_gallery_images_each_become_their_own_image_spec():
    html = (
        '<figure class="wp-block-gallery">'
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt="First"/></figure>'
        '<figure class="wp-block-image"><img src="https://example.com/b.png" alt="Second"/>'
        "<figcaption>Second caption</figcaption></figure>"
        "</figure>"
    )
    specs, warnings = parse_content(html)
    assert warnings == []
    assert [spec[0] for spec in specs] == ["image", "image"]
    assert [spec[1]["src"] for spec in specs] == ["https://example.com/a.png", "https://example.com/b.png"]
    # A caption on a nested figure belongs to that image.
    assert specs[0][1]["caption"] == ""
    assert specs[1][1]["caption"] == "<p>Second caption</p>"


def test_parse_content_multi_image_gallery_caption_is_dropped_with_a_warning():
    """A caption on a gallery of several images describes the set, not any one image."""
    html = (
        '<figure class="wp-block-gallery">'
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt=""/></figure>'
        '<figure class="wp-block-image"><img src="https://example.com/b.png" alt=""/></figure>'
        '<figcaption class="blocks-gallery-caption">Gallery caption</figcaption>'
        "</figure>"
    )
    specs, warnings = parse_content(html)
    assert [spec[0] for spec in specs] == ["image", "image"]
    assert len(warnings) == 1
    assert warnings[0][0] == "caption"
    assert "Gallery caption" in warnings[0][1] and "gallery of 2 images" in warnings[0][1]


def test_parse_content_single_image_gallery_keeps_its_caption():
    """WordPress galleries of one image are common, and the caption clearly describes it."""
    html = (
        '<figure class="wp-block-gallery">'
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt="Only"/></figure>'
        '<figcaption class="blocks-gallery-caption">The only image</figcaption>'
        "</figure>"
    )
    specs, warnings = parse_content(html)
    assert warnings == []
    assert [spec[0] for spec in specs] == ["image"]
    assert specs[0][1]["caption"] == "<p>The only image</p>"


def test_parse_content_single_image_gallery_does_not_overwrite_the_images_own_caption():
    html = (
        '<figure class="wp-block-gallery">'
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt=""/>'
        "<figcaption>The image's own caption</figcaption></figure>"
        '<figcaption class="blocks-gallery-caption">Gallery caption</figcaption>'
        "</figure>"
    )
    specs, warnings = parse_content(html)
    assert specs[0][1]["caption"] == "<p>The image's own caption</p>"
    assert len(warnings) == 1
    assert "Gallery caption" in warnings[0][1]


def test_parse_content_figure_inside_a_container_is_imported_not_left_inline():
    """A figure wrapped in a layout div was previously left hotlinked in a text block."""
    html = (
        '<div class="wp-block-group"><p>Before</p>'
        '<figure class="wp-block-image"><img src="https://example.com/a.png" alt="Alt"/>'
        "<figcaption>Nested caption</figcaption></figure>"
        "<p>After</p></div>"
    )
    specs, warnings = parse_content(html)
    assert warnings == [], "the caption now has an image to attach to"
    assert [spec[0] for spec in specs] == ["text", "image", "text"]
    assert "Before" in specs[0][1]
    assert specs[1][1] == {"src": "https://example.com/a.png", "alt": "Alt", "caption": "<p>Nested caption</p>"}
    assert "After" in specs[2][1]


def test_parse_content_media_and_text_layout_image_is_imported():
    html = (
        '<div class="wp-block-media-text">'
        '<figure class="wp-block-media-text__media"><img src="https://example.com/a.png" alt="Side"/></figure>'
        '<div class="wp-block-media-text__content"><p>Beside the image</p></div>'
        "</div>"
    )
    specs, _ = parse_content(html)
    assert [spec[0] for spec in specs] == ["image", "text"]
    assert specs[0][1]["src"] == "https://example.com/a.png"
    assert "Beside the image" in specs[1][1]


def test_parse_content_container_without_a_figure_is_left_as_text():
    """Only containers holding a figure are stepped into, so ordinary markup is untouched."""
    html = '<div class="wp-block-group"><p>Just text</p><ul><li>An item</li></ul></div>'
    specs, _ = parse_content(html)
    assert [spec[0] for spec in specs] == ["text"]
    assert 'class="wp-block-group"' in specs[0][1]


def test_parse_content_inline_image_in_a_list_stays_in_the_text():
    """Pulling an inline image out of prose would break the flow, so it is left in place.

    materialize_content turns it into a Wagtail image embed rather than a block.
    """
    html = "<ul><li>Step one <img src=\"https://example.com/icon.png\" alt=''/></li></ul>"
    specs, _ = parse_content(html)
    assert [spec[0] for spec in specs] == ["text"]
    assert "https://example.com/icon.png" in specs[0][1]


def test_parse_content_self_hosted_video_warns_and_stays_in_the_text():
    html = (
        '<figure class="wp-block-video"><video controls="" src="https://blog.mozilla.org/files/tab-groups.mp4"></video>'
        "<figcaption>Firefox tab groups now available</figcaption></figure>"
    )
    specs, warnings = parse_content(html)
    assert [spec[0] for spec in specs] == ["text"]
    assert "tab-groups.mp4" in specs[0][1]
    # One warning for the video, not a second one for its caption, which travels with it.
    assert len(warnings) == 1
    assert warnings[0][0] == "video"
    assert "self-hosted video https://blog.mozilla.org/files/tab-groups.mp4" in warnings[0][1]
    # The <video> is not a rich text feature, so it does not merely stay hotlinked: the editor
    # drops it entirely on the first save, leaving the caption behind. Say so.
    assert "editing the page will drop it" in warnings[0][1]


def test_parse_content_bare_video_element_warns():
    specs, warnings = parse_content('<p>Watch:</p><video src="https://blog.mozilla.org/files/clip.mp4"></video>')
    assert [spec[0] for spec in specs] == ["text"]
    assert len(warnings) == 1
    assert "clip.mp4" in warnings[0][1]


def test_parse_content_captioned_figure_without_an_image_warns():
    html = "<figure><table><tr><td>A table, not an image</td></tr></table><figcaption>Table caption</figcaption></figure>"
    specs, warnings = parse_content(html)
    assert [spec[0] for spec in specs] == ["text"]
    assert len(warnings) == 1
    assert "Table caption" in warnings[0][1]


def test_parse_content_caption_shortcode_without_img_is_dropped():
    specs, _ = parse_content('[caption id="1"]just some text, no image[/caption]<p>Rest</p>')
    assert len(specs) == 1
    assert "just some text" not in specs[0][1]
    assert "Rest" in specs[0][1]


def test_parse_content_pre_tag_becomes_code_spec():
    specs, _ = parse_content("<p>Before</p><pre>print('hi')</pre><p>After</p>")
    assert [spec[0] for spec in specs] == ["text", "code", "text"]
    assert specs[1][1] == {"code": "print('hi')"}


# ---------------------------------------------------------------------------
# materialize_content (block specs -> StreamField blocks; downloads images)
# ---------------------------------------------------------------------------


@responses.activate
def test_materialize_content_downloads_image_spec_into_media_block():
    mock_image_downloads()
    cmd = make_command()
    blocks = cmd.materialize_content([("text", "<p>Text</p>"), ("image", {"src": "https://example.com/a.png", "alt": "Alt"})], "A Test Post")
    assert [block[0] for block in blocks] == ["text", "media"]
    assert blocks[1][1][0][0] == "image"


@responses.activate
def test_materialize_content_image_with_caption_becomes_image_caption_block():
    mock_image_downloads()
    cmd = make_command()
    spec = ("image", {"src": "https://example.com/a.png", "alt": "Alt", "caption": "<p>A caption</p>"})
    blocks = cmd.materialize_content([spec], "A Test Post")
    assert [block[0] for block in blocks] == ["image_caption"]
    value = blocks[0][1]
    assert value["caption"] == "<p>A caption</p>"
    assert value["image"]["image"].title == "Alt"


@responses.activate
def test_materialize_content_video_spec_downloads_youtube_thumbnail_as_poster():
    mock_image_downloads()
    cmd = make_command()
    blocks = cmd.materialize_content([("video", {"url": "https://www.youtube.com/watch?v=abc123", "alt": "A video"})], "A Test Post")

    assert [block[0] for block in blocks] == ["media"]
    video_type, video_value = blocks[0][1][0]
    assert video_type == "video"
    assert video_value["video_url"] == "https://www.youtube.com/watch?v=abc123"
    assert video_value["alt"] == "A video"
    assert video_value["poster"].title == "A video"
    assert [call.request.url for call in responses.calls] == ["https://img.youtube.com/vi/abc123/hqdefault.jpg"]


@responses.activate
def test_materialize_content_gives_each_video_its_own_poster():
    """Two videos in one run must not share a thumbnail just because both URLs end in hqdefault.jpg."""
    mock_image_downloads()
    cmd = make_command()

    blocks = cmd.materialize_content(
        [
            ("video", {"url": "https://www.youtube.com/watch?v=abc123", "alt": "First video"}),
            ("video", {"url": "https://www.youtube.com/watch?v=xyz789", "alt": "Second video"}),
        ],
        "A Test Post",
    )

    first_poster = blocks[0][1][0][1]["poster"]
    second_poster = blocks[1][1][0][1]["poster"]
    assert first_poster.pk != second_poster.pk


@responses.activate
def test_materialize_content_video_without_caption_falls_back_to_post_title_for_alt():
    mock_image_downloads()
    cmd = make_command()
    blocks = cmd.materialize_content([("video", {"url": "https://www.youtube.com/watch?v=abc123", "alt": ""})], "A Test Post")
    assert blocks[0][1][0][1]["alt"] == "A Test Post"


@responses.activate
def test_materialize_content_links_a_video_whose_poster_download_fails(no_retry_backoff):
    """The block requires a poster, but the video shouldn't vanish for want of a thumbnail.

    YouTube serves no thumbnail at all for a video that has since been deleted, which is the case
    for one of the videos in this export.
    """
    mock_failed_downloads()
    cmd = make_command()
    blocks = cmd.materialize_content([("video", {"url": "https://www.youtube.com/watch?v=abc123", "alt": "A video"})], "A Test Post")
    # The link keeps its query string here: a YouTube watch URL carries the video id in it.
    assert blocks == [("text", '<p><a href="https://www.youtube.com/watch?v=abc123">Watch video</a></p>')]


@responses.activate
def test_materialize_content_drops_captioned_image_whose_download_fails(no_retry_backoff):
    mock_failed_downloads()
    cmd = make_command()
    spec = ("image", {"src": "https://example.com/a.png", "alt": "", "caption": "<p>A caption</p>"})
    assert cmd.materialize_content([spec], "A Test Post") == []


@responses.activate
def test_materialize_content_drops_image_whose_download_fails(no_retry_backoff):
    mock_failed_downloads()
    cmd = make_command()
    specs = [("text", "<p>Before</p>"), ("image", {"src": "https://example.com/a.png", "alt": ""}), ("text", "<p>After</p>")]
    blocks = cmd.materialize_content(specs, "A Test Post")
    assert [block[0] for block in blocks] == ["text", "text"]


@responses.activate
def test_materialize_content_turns_inline_images_into_wagtail_embeds():
    mock_image_downloads()
    cmd = make_command()
    spec = ("text", '<ul><li>Step one <img src="https://example.com/icon.png" alt="A menu button"/></li></ul>')
    blocks = cmd.materialize_content([spec], "A Test Post")

    html = blocks[0][1]
    image = SpringfieldImage.objects.get(title="A menu button")
    embed = BeautifulSoup(html, "html.parser").find("embed")
    assert embed.attrs == {"embedtype": "image", "id": str(image.pk), "alt": "A menu button", "format": "fullwidth"}
    # The image is imported without disturbing the prose around it.
    assert "<li>Step one " in html
    assert "https://example.com/icon.png" not in html


@responses.activate
def test_materialize_content_inline_image_alt_falls_back_to_the_post_title():
    mock_image_downloads()
    cmd = make_command()
    blocks = cmd.materialize_content([("text", '<p><img src="https://example.com/a.png" alt=""/></p>')], "A Test Post")
    assert SpringfieldImage.objects.filter(title="A Test Post").exists()
    assert 'alt=""' in blocks[0][1]


@responses.activate
def test_materialize_content_inline_image_keeps_its_link_wrapper():
    mock_image_downloads()
    cmd = make_command()
    spec = ("text", '<a href="https://example.com/full.png"><img src="https://example.com/small.png" alt="Screenshot"/></a>')
    html = cmd.materialize_content([spec], "A Test Post")[0][1]
    assert '<a href="https://example.com/full.png">' in html
    assert BeautifulSoup(html, "html.parser").find("embed") is not None


@responses.activate
def test_materialize_content_keeps_the_original_tag_when_an_inline_image_fails(no_retry_backoff):
    mock_failed_downloads()
    cmd = make_command()
    spec = ("text", '<p>Before <img src="https://example.com/dead.png" alt="Alt"/> after</p>')
    html = cmd.materialize_content([spec], "A Test Post")[0][1]

    # Nothing to embed, so the hotlink stays rather than the image vanishing from the prose.
    assert 'src="https://example.com/dead.png"' in html
    assert "embedtype" not in html
    assert "could not download image" in cmd.stderr._out.getvalue()


@responses.activate
def test_materialize_content_text_without_images_is_untouched():
    cmd = make_command()
    blocks = cmd.materialize_content([("text", "<p>Just prose</p>")], "A Test Post")
    assert blocks == [("text", "<p>Just prose</p>")]
    assert len(responses.calls) == 0


@pytest.mark.parametrize(
    "text",
    [
        "fx_blog_header_extensions_writing",  # underscores
        "Monitor-1000x542.jpg",  # image extension
        "Disconnect-Study-Blog-Post-Graph-01-1-300x150",  # trailing pixel dimensions
        "crossistebloggraphic",  # a single run-together token
        "index",
        "   ",
        "",
    ],
)
def test_image_description_blanks_text_that_names_a_file(text):
    assert image_description(text) == ""


@pytest.mark.parametrize(
    "text",
    [
        "Firefox Focus Erase Button",
        "Stylized graphic showing network nodes and locks",
        "Click the Multi-Account Containers icon to use or manage the feature",
        "Disconnect Header",
    ],
)
def test_image_description_keeps_real_descriptions(text):
    assert image_description(text) == text


def test_image_description_strips_surrounding_whitespace():
    assert image_description("  A menu button in Firefox  ") == "A menu button in Firefox"


@responses.activate
def test_wordpress_bookkeeping_tags_are_not_imported(tmp_path, index_page):
    """'export' is the export tool's own marker and 'homepage' a placement flag - neither is a subject."""
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(tags="export|homepage|Uncategorized|Privacy"))

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert [tag.name for tag in page.tags.all()] == ["Privacy"]
    assert not Tag.objects.filter(slug="export").exists(), "the marker must not even reach the Tag snippets"


@responses.activate
def test_a_post_with_several_bylines_warns_because_only_one_author_can_be_kept(tmp_path, index_page):
    """The Author* fields hold the post's owner, who is not always one of the bylines, and
    BlogArticlePage.author is a single FK - so these need checking by hand."""
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(authors="kim-bryant|jamie-teh|anna-yeddi", author_first="Kristina", author_last="Bravo"))
    err = StringIO()

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stderr=err)

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.author.name == "Kristina Bravo"
    assert "kim-bryant|jamie-teh|anna-yeddi" in err.getvalue()
    assert "[author]" in err.getvalue()


@responses.activate
def test_a_single_byline_needs_no_author_warning(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(authors="dkessler@mozilla.com"))
    err = StringIO()

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stderr=err)

    assert "[author]" not in err.getvalue()


@responses.activate
def test_hero_alt_text_falls_back_to_the_export_image_description(tmp_path, index_page):
    """ImageDescription describes the image by definition, so it beats the file-name-ish title."""
    mock_image_downloads()
    xml_path = write_xml(
        tmp_path,
        post_xml(image_alt_text="", image_title="mozilla_blog-post_visuals_grayscale", image_description="A brain in grayscale"),
    )

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    assert BlogArticlePage.objects.get(slug="a-test-post").image.description == "A brain in grayscale"


@responses.activate
def test_hero_image_caption_is_reported_because_the_page_has_nowhere_to_show_it(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(image_caption="Image source: imdb.com"))
    err = StringIO()

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"), stderr=err)

    assert "Image source: imdb.com" in err.getvalue()
    assert "[caption]" in err.getvalue()


@responses.activate
def test_image_alt_text_comes_from_the_export_when_it_describes_the_image(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(image_alt_text="A laptop showing the Firefox home page"))

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.image.description == "A laptop showing the Firefox home page"
    # Wagtail renders the description as the image's alt text.
    assert page.image.default_alt_text == "A laptop showing the Firefox home page"


@responses.activate
def test_image_alt_text_is_left_blank_when_the_export_only_names_the_file(tmp_path, index_page):
    mock_image_downloads()
    xml_path = write_xml(tmp_path, post_xml(image_alt_text="", image_title="SP_FX_Monitor_blogheader_01"))

    call_command("import_wordpress_blog_posts", str(xml_path), url_map_out=str(tmp_path / "url_map.csv"))

    page = BlogArticlePage.objects.get(slug="a-test-post")
    assert page.image.description == ""
    # The file name is still useful as a library label, just not as alt text.
    assert page.image.title == "SP_FX_Monitor_blogheader_01"


@responses.activate
def test_inline_image_embed_drops_alt_that_names_a_file():
    mock_image_downloads()
    cmd = make_command()
    spec = ("text", '<p><img src="https://example.com/a.png" alt="fx_blog_header_writing"/></p>')
    html = cmd.materialize_content([spec], "A Test Post")[0][1]

    embed = BeautifulSoup(html, "html.parser").find("embed")
    assert embed["alt"] == ""
    assert SpringfieldImage.objects.get(pk=embed["id"]).description == ""


@responses.activate
def test_content_image_description_comes_from_its_alt_attribute():
    mock_image_downloads()
    cmd = make_command()
    spec = ("image", {"src": "https://example.com/a.png", "alt": "The erase button in Firefox Focus", "caption": ""})
    cmd.materialize_content([spec], "A Test Post")
    assert SpringfieldImage.objects.get(title="The erase button in Firefox Focus").description == "The erase button in Firefox Focus"


@responses.activate
def test_get_or_create_image_unprocessable_file_warns_instead_of_raising(monkeypatch):
    """A file ImageMagick cannot handle must not take the whole post down with it."""
    mock_image_downloads()
    monkeypatch.setattr(
        "springfield.cms.management.commands.import_wordpress_blog_posts.SpringfieldImage.objects.create",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("cache resources exhausted")),
    )
    cmd = make_command()

    assert cmd.get_or_create_image("https://example.com/huge.gif", "Huge") is None
    assert "could not process image https://example.com/huge.gif" in cmd.stderr._out.getvalue()
    assert "cache resources exhausted" in cmd.stderr._out.getvalue()


@responses.activate
def test_materialize_content_passes_through_non_image_specs():
    cmd = make_command()
    blocks = cmd.materialize_content([("text", "<p>Hi</p>"), ("code", {"code": "print('hi')"})], "A Test Post")
    assert blocks == [("text", "<p>Hi</p>"), ("code", {"code": "print('hi')"})]
    assert len(responses.calls) == 0, "non-image specs must not hit the network"


# ---------------------------------------------------------------------------
# IncrementalCsv
# ---------------------------------------------------------------------------


def test_incremental_csv_writes_header_and_rows(tmp_path):
    path = tmp_path / "out.csv"
    writer = IncrementalCsv(str(path), ["wp_id", "old_url", "new_url"])
    writer.write(("1", "https://blog.mozilla.org/en/firefox/a/", "https://www.firefox.com/en-US/blog/a/"))
    writer.close()

    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["wp_id", "old_url", "new_url"]
    assert rows[1] == ["1", "https://blog.mozilla.org/en/firefox/a/", "https://www.firefox.com/en-US/blog/a/"]
    assert writer.count == 1


def test_incremental_csv_creates_no_file_until_a_row_is_written(tmp_path):
    path = tmp_path / "out.csv"
    writer = IncrementalCsv(str(path), ["a", "b"])
    assert not path.exists(), "a run with nothing to report leaves no empty CSV behind"
    writer.close()
    assert not path.exists()


def test_incremental_csv_rows_survive_without_close(tmp_path):
    """Each row is flushed as it is written, so a crash keeps the rows already recorded."""
    path = tmp_path / "out.csv"
    writer = IncrementalCsv(str(path), ["a", "b"])
    writer.write(("1", "one"))
    writer.write(("2", "two"))
    # Deliberately no close(), standing in for a process that dies mid-import.

    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows == [["a", "b"], ["1", "one"], ["2", "two"]]
