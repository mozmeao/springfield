# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import json
from io import BytesIO, StringIO
from urllib.parse import parse_qs, urlparse

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError

import pytest
import requests
import responses
from PIL import Image
from wagtail.models import Locale
from wagtail.utils.file import hash_filelike

from springfield.blog.fixtures.blog_fixtures import get_blog_index_page
from springfield.blog.management.commands.fix_imported_blog_posts import crop_to_widescreen
from springfield.blog.models import BlogArticleAuthor, BlogArticlePage, BlogAuthor, BlogTopic, HeroStyle
from springfield.cms.models import SpringfieldImage

pytestmark = [pytest.mark.django_db]

WIDESCREEN = (1280, 720)
SD = (640, 480)
HQ = (480, 360)


def jpeg(size, colour=(200, 30, 30)):
    buffer = BytesIO()
    Image.new("RGB", size, colour).save(buffer, "JPEG")
    return buffer.getvalue()


def mock_youtube(videos):
    """Answer YouTube's oEmbed and thumbnail URLs for `videos`.

    `videos` maps a video id to a dict with its `title`, its player `ratio` ("16:9" or "4:3") and
    the `thumbnails` YouTube has for it, as {name: bytes}. Anything else is a 404, as on YouTube.
    """

    def oembed(request):
        video_id = parse_qs(urlparse(parse_qs(urlparse(request.url).query)["url"][0]).query)["v"][0]
        video = videos.get(video_id)
        if video is None:
            return 404, {}, "Not Found"
        width, height = (200, 150) if video.get("ratio") == "4:3" else (200, 113)
        return 200, {"Content-Type": "application/json"}, json.dumps({"title": video["title"], "width": width, "height": height})

    def thumbnail(request):
        _, _, video_id, name = urlparse(request.url).path.split("/")
        content = videos.get(video_id, {}).get("thumbnails", {}).get(name.removesuffix(".jpg"))
        if content is None:
            return 404, {}, ""
        return 200, {"Content-Type": "image/jpeg"}, content

    responses.add_callback(responses.GET, "https://www.youtube.com/oembed", callback=oembed)
    responses.add_callback(responses.GET, responses.matchers.re.compile(r"https://img\.youtube\.com/vi/.+"), callback=thumbnail)


def widescreen_video(title="A video", colour=(200, 30, 30)):
    return {"title": title, "thumbnails": {"maxresdefault": jpeg(WIDESCREEN, colour), "hqdefault": jpeg(HQ, colour)}}


def hqdefault_poster(video_id):
    """A poster as the importer made it: YouTube's 4:3 thumbnail, named after it."""
    content = jpeg(HQ, (10, 10, 10))
    return SpringfieldImage.objects.create(
        title="Post title",
        description="Post title",
        file=ContentFile(content, name=f"{video_id}-hqdefault.jpg"),
        file_hash=hash_filelike(BytesIO(content)),
    )


def video_block(video_id, poster, url=None):
    return ("media", [("video", {"video_url": url or f"https://www.youtube.com/watch?v={video_id}", "alt": "Post title", "poster": poster})])


@pytest.fixture
def index_page(minimal_site):
    return get_blog_index_page(slug="blog")


@pytest.fixture
def topic():
    return BlogTopic.objects.create(name="News", slug="news", locale=Locale.get_default())


@pytest.fixture
def mozilla():
    return BlogAuthor.objects.create(name="Mozilla", slug="mozilla", locale=Locale.get_default())


@pytest.fixture
def make_post(index_page, topic):
    def make(slug, content=(), authors=(), live=False):
        page = BlogArticlePage(title=slug, slug=slug, topic=topic, hero_style=HeroStyle.TEXT_ONLY, content=list(content), live=live)
        page.article_authors = [BlogArticleAuthor(author=author, sort_order=order) for order, author in enumerate(authors)]
        index_page.add_child(instance=page)
        revision = page.save_revision()
        if live:
            revision.publish()
        else:
            # The imported posts were published, then unpublished.
            page.refresh_from_db()
        return page

    return make


def run(tmp_path, *fixes, **options):
    stdout, stderr = StringIO(), StringIO()
    report = tmp_path / "report.csv"
    args = [arg for fix in fixes for arg in ("--fix", fix)]
    call_command("fix_imported_blog_posts", *args, report_out=str(report), stdout=stdout, stderr=stderr, **options)
    with open(report, newline="") as report_file:
        rows = list(csv.DictReader(report_file))
    return stdout.getvalue(), stderr.getvalue(), rows


def latest(page):
    return BlogArticlePage.objects.get(pk=page.pk).get_latest_revision_as_object()


def poster_of(page, index=0):
    videos = [child.value for block in page.content if block.block_type == "media" for child in block.value if child.block_type == "video"]
    return videos[index]["poster"]


# -------------------------------------------------------------------------
# youtube-posters
# -------------------------------------------------------------------------


@responses.activate
def test_youtube_poster_swapped_for_the_widescreen_thumbnail_as_a_draft(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video("A video | #AskFirefox")})
    old = hqdefault_poster("abc")
    post = make_post("post", content=[video_block("abc", old)])
    revisions_before = post.revisions.count()

    _, _, rows = run(tmp_path, "youtube-posters")

    poster = poster_of(latest(post))
    assert poster.pk != old.pk
    assert (poster.width, poster.height) == WIDESCREEN
    assert poster.file.name.endswith(".jpg") and "abc-maxresdefault" in poster.file.name
    # The pipe YouTube uses before a series name reads badly as alt text.
    assert poster.title == poster.description == "A video: #AskFirefox"
    assert post.revisions.count() == revisions_before + 1
    post.refresh_from_db()
    assert not post.live
    assert [(row["fix"], row["slug"], row["action"]) for row in rows] == [("youtube-posters", "post", "changed")]
    assert rows[0]["revision_id"] == str(post.latest_revision_id)


@responses.activate
def test_youtube_posters_dry_run_writes_nothing(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    old = hqdefault_poster("abc")
    post = make_post("post", content=[video_block("abc", old)])
    revisions_before = post.revisions.count()

    stdout, _, rows = run(tmp_path, "youtube-posters", dry_run=True)

    assert poster_of(latest(post)).pk == old.pk
    assert post.revisions.count() == revisions_before
    assert SpringfieldImage.objects.count() == 1
    assert [row["action"] for row in rows] == ["would change"]
    assert "new image abc-maxresdefault.jpg (1280x720" in rows[0]["new"]
    assert "[dry-run]" in stdout


@responses.activate
def test_youtube_posters_second_run_finds_nothing_to_do(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    post = make_post("post", content=[video_block("abc", hqdefault_poster("abc"))])
    run(tmp_path, "youtube-posters")
    revisions, images = post.revisions.count(), SpringfieldImage.objects.count()

    stdout, _, rows = run(tmp_path, "youtube-posters")

    assert rows == []
    assert (post.revisions.count(), SpringfieldImage.objects.count()) == (revisions, images)
    assert "nothing to do" in stdout


@responses.activate
def test_youtube_poster_of_a_4_3_video_is_kept(tmp_path, make_post):
    mock_youtube({"old": {"title": "Old clip", "ratio": "4:3", "thumbnails": {"hqdefault": jpeg(HQ)}}})
    old = hqdefault_poster("old")
    post = make_post("post", content=[video_block("old", old)])

    _, _, rows = run(tmp_path, "youtube-posters")

    assert poster_of(latest(post)).pk == old.pk
    assert [(row["action"], row["detail"]) for row in rows] == [("skipped", "old: 4:3 video, kept the current poster")]


@responses.activate
def test_youtube_poster_of_an_unknown_video_is_kept(tmp_path, make_post):
    mock_youtube({})
    old = hqdefault_poster("gone")
    post = make_post("post", content=[video_block("gone", old)])

    _, _, rows = run(tmp_path, "youtube-posters")

    assert poster_of(latest(post)).pk == old.pk
    assert rows[0]["action"] == "skipped"
    assert "deleted or private" in rows[0]["detail"]


@pytest.mark.parametrize(
    "thumbnails, expected_size, source",
    [
        ({"sddefault": jpeg(SD), "hqdefault": jpeg(HQ)}, (640, 360), "sddefault"),
        ({"hqdefault": jpeg(HQ)}, (480, 270), "hqdefault"),
    ],
)
@responses.activate
def test_youtube_poster_without_a_widescreen_thumbnail_is_a_16_9_crop(tmp_path, make_post, thumbnails, expected_size, source):
    mock_youtube({"abc": {"title": "A video", "thumbnails": thumbnails}})
    post = make_post("post", content=[video_block("abc", hqdefault_poster("abc"))])

    _, _, rows = run(tmp_path, "youtube-posters")

    poster = poster_of(latest(post))
    assert (poster.width, poster.height) == expected_size
    assert f"abc-{source}-16x9" in poster.file.name
    assert rows[0]["detail"] == f"abc: no widescreen thumbnail, 16:9 crop of {source}"

    # The crop's name still contains "hqdefault", but a second run must leave it alone.
    _, _, second_rows = run(tmp_path, "youtube-posters")
    assert second_rows == []


def test_crop_to_widescreen_keeps_the_letterboxed_picture():
    image = Image.new("RGB", SD, (0, 0, 0))
    image.paste((255, 255, 255), (0, 60, 640, 420))
    buffer = BytesIO()
    image.save(buffer, "PNG")

    content, size = crop_to_widescreen(buffer.getvalue())

    assert size == (640, 360)
    with Image.open(BytesIO(content)) as cropped:
        # No black bar is left at the top or bottom edge.
        assert min(cropped.getpixel((320, 0))) > 200
        assert min(cropped.getpixel((320, 359))) > 200


@responses.activate
def test_youtube_poster_reuses_an_image_already_in_the_library(tmp_path, make_post):
    video = widescreen_video()
    content = video["thumbnails"]["maxresdefault"]
    uploaded = SpringfieldImage.objects.create(
        title="Uploaded by hand", description="Alt", file=ContentFile(content, name="upload.jpg"), file_hash=hash_filelike(BytesIO(content))
    )
    mock_youtube({"abc": video})
    post = make_post("post", content=[video_block("abc", hqdefault_poster("abc"))])

    _, _, rows = run(tmp_path, "youtube-posters")

    assert poster_of(latest(post)).pk == uploaded.pk
    assert "already in the library" in rows[0]["detail"]


@responses.activate
def test_youtube_poster_shared_by_two_posts_is_created_once(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    old = hqdefault_poster("abc")
    first = make_post("first", content=[video_block("abc", old)])
    second = make_post("second", content=[video_block("abc", old)])

    run(tmp_path, "youtube-posters")

    assert poster_of(latest(first)).pk == poster_of(latest(second)).pk
    assert SpringfieldImage.objects.count() == 2


@responses.activate
def test_youtube_posters_leave_other_videos_alone(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    widescreen = SpringfieldImage.objects.create(title="Frame", description="Frame", file=ContentFile(jpeg(WIDESCREEN), name="frame1.png"))
    hosted = hqdefault_poster("hosted")
    post = make_post(
        "post",
        content=[
            video_block("abc", widescreen),
            video_block("hosted", hosted, url="https://assets.mozilla.net/fxblog/webm/hosted-hqdefault.webm"),
        ],
    )

    _, _, rows = run(tmp_path, "youtube-posters")

    assert rows == []
    assert [poster_of(latest(post), index).pk for index in (0, 1)] == [widescreen.pk, hosted.pk]


@responses.activate
def test_youtube_poster_builds_on_the_latest_draft(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    post = make_post("post", content=[video_block("abc", hqdefault_poster("abc"))])
    draft = post.get_latest_revision_as_object()
    draft.title = "Edited in the CMS"
    draft.save_revision()

    run(tmp_path, "youtube-posters")

    assert latest(post).title == "Edited in the CMS"


@responses.activate
def test_live_post_is_skipped_unless_asked(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    old = hqdefault_poster("abc")
    post = make_post("post", content=[video_block("abc", old)], live=True)

    _, _, rows = run(tmp_path, "youtube-posters")

    assert poster_of(latest(post)).pk == old.pk
    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"].startswith("live page")
    # No poster image is made for a revision that won't be saved.
    assert SpringfieldImage.objects.count() == 1


@responses.activate
def test_live_post_gets_only_a_draft_with_include_live(tmp_path, make_post):
    mock_youtube({"abc": widescreen_video()})
    old = hqdefault_poster("abc")
    post = make_post("post", content=[video_block("abc", old)], live=True)

    run(tmp_path, "youtube-posters", include_live=True)

    post.refresh_from_db()
    assert post.live and post.has_unpublished_changes
    assert poster_of(post).pk == old.pk
    assert poster_of(latest(post)).pk != old.pk


# -------------------------------------------------------------------------
# mozilla-byline
# -------------------------------------------------------------------------


def author_slugs(page):
    return [placement.author.slug for placement in latest(page).article_authors.all()]


def test_mozilla_byline_removed_when_mozilla_is_the_only_author(tmp_path, make_post, mozilla):
    person = BlogAuthor.objects.create(name="Ada", slug="ada", locale=Locale.get_default())
    only_mozilla = make_post("only-mozilla", authors=[mozilla])
    with_person = make_post("with-person", authors=[mozilla, person])
    no_mozilla = make_post("no-mozilla", authors=[person])

    _, _, rows = run(tmp_path, "mozilla-byline")

    assert author_slugs(only_mozilla) == []
    assert author_slugs(with_person) == ["mozilla", "ada"]
    assert author_slugs(no_mozilla) == ["ada"]
    assert [(row["slug"], row["action"], row["old"]) for row in rows] == [("only-mozilla", "changed", "Mozilla")]
    # The snippet itself stays, for any post that still credits it.
    assert BlogAuthor.objects.filter(slug="mozilla").exists()


def test_mozilla_byline_dry_run_and_second_run(tmp_path, make_post, mozilla):
    post = make_post("post", authors=[mozilla])

    _, _, dry_rows = run(tmp_path, "mozilla-byline", dry_run=True)
    assert author_slugs(post) == ["mozilla"]
    assert [row["action"] for row in dry_rows] == ["would change"]

    run(tmp_path, "mozilla-byline")
    _, _, second_rows = run(tmp_path, "mozilla-byline")
    assert author_slugs(post) == []
    assert second_rows == []


@responses.activate
def test_fixes_on_one_post_share_one_revision(tmp_path, make_post, mozilla):
    mock_youtube({"abc": widescreen_video()})
    post = make_post("post", content=[video_block("abc", hqdefault_poster("abc"))], authors=[mozilla])
    revisions_before = post.revisions.count()

    _, _, rows = run(tmp_path, "youtube-posters", "mozilla-byline")

    assert post.revisions.count() == revisions_before + 1
    assert {row["revision_id"] for row in rows} == {str(post.revisions.latest("created_at").pk)}
    assert author_slugs(post) == []
    assert "maxresdefault" in poster_of(latest(post)).file.name


def test_slug_limits_the_run(tmp_path, make_post, mozilla):
    one = make_post("one", authors=[mozilla])
    two = make_post("two", authors=[mozilla])

    run(tmp_path, "mozilla-byline", slugs=["one"])

    assert (author_slugs(one), author_slugs(two)) == ([], ["mozilla"])


def test_unknown_slug_is_an_error(tmp_path, make_post):
    with pytest.raises(CommandError, match="nope"):
        run(tmp_path, "mozilla-byline", slugs=["nope"])


# -------------------------------------------------------------------------
# author-names
# -------------------------------------------------------------------------


def names_csv(tmp_path, *rows):
    path = tmp_path / "names.csv"
    path.write_text("slug,name\n" + "".join(f"{slug},{name}\n" for slug, name in rows))
    return str(path)


def test_author_renamed_and_published_keeping_its_slug(tmp_path, index_page):
    author = BlogAuthor.objects.create(name="bryan-johns", slug="bryan-johns", locale=Locale.get_default())

    _, _, rows = run(tmp_path, "author-names", author_names=names_csv(tmp_path, ("bryan-johns", "Bryan Johns")))

    author.refresh_from_db()
    assert (author.name, author.slug, author.live, author.has_unpublished_changes) == ("Bryan Johns", "bryan-johns", True, False)
    assert author.live_revision_id is not None
    assert [(row["action"], row["old"], row["new"]) for row in rows] == [("changed", "bryan-johns", "Bryan Johns")]


def test_author_names_dry_run_and_second_run(tmp_path, index_page):
    author = BlogAuthor.objects.create(name="bryan-johns", slug="bryan-johns", locale=Locale.get_default())
    names = names_csv(tmp_path, ("bryan-johns", "Bryan Johns"))

    _, _, dry_rows = run(tmp_path, "author-names", author_names=names, dry_run=True)
    author.refresh_from_db()
    assert author.name == "bryan-johns"
    assert [row["action"] for row in dry_rows] == ["would change"]

    run(tmp_path, "author-names", author_names=names)
    _, _, second_rows = run(tmp_path, "author-names", author_names=names)
    assert second_rows == []


def test_author_names_skips_unknown_slugs_and_unpublished_drafts(tmp_path, index_page):
    drafted = BlogAuthor.objects.create(name="amy-bebbington", slug="amy-bebbington", locale=Locale.get_default())
    drafted.job_title = "Unfinished edit"
    drafted.save_revision()

    _, _, rows = run(tmp_path, "author-names", author_names=names_csv(tmp_path, ("nobody", "No One"), ("amy-bebbington", "Amy Bebbington")))

    drafted.refresh_from_db()
    assert drafted.name == "amy-bebbington"
    assert [(row["slug"], row["action"]) for row in rows] == [("nobody", "skipped"), ("amy-bebbington", "skipped")]


def test_author_names_needs_a_csv(tmp_path, index_page):
    with pytest.raises(CommandError, match="--author-names"):
        run(tmp_path, "author-names")


def test_author_names_csv_rows_need_a_name(tmp_path, index_page):
    with pytest.raises(CommandError, match="line 2"):
        run(tmp_path, "author-names", author_names=names_csv(tmp_path, ("bryan-johns", "")))


# -------------------------------------------------------------------------
# image-text, video-alt, inline-alt
# -------------------------------------------------------------------------


def decisions_json(tmp_path, images=(), videos=()):
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps({"images": list(images), "videos": list(videos)}))
    return str(path)


def library_image(title="image.png", description="", colour=(1, 2, 3)):
    content = jpeg((40, 30), colour)
    return SpringfieldImage.objects.create(
        title=title, description=description, file=ContentFile(content, name="image.png"), file_hash=hash_filelike(BytesIO(content))
    )


def test_image_text_sets_title_and_description_by_file_hash(tmp_path, index_page):
    image = library_image()
    decisions = decisions_json(tmp_path, images=[{"hash": image.file_hash, "title": "Team photo, 2004", "description": "About 20 people in a room"}])

    _, _, rows = run(tmp_path, "image-text", decisions=decisions)

    image.refresh_from_db()
    assert (image.title, image.description, image.is_decorative) == ("Team photo, 2004", "About 20 people in a room", False)
    assert [(row["fix"], row["action"]) for row in rows] == [("image-text", "changed")]


def test_image_text_marks_decorative_with_an_empty_description(tmp_path, index_page):
    image = library_image(description="Old text")
    decisions = decisions_json(tmp_path, images=[{"hash": image.file_hash, "title": "Sparkles", "description": "ignored", "decorative": True}])

    run(tmp_path, "image-text", decisions=decisions)

    image.refresh_from_db()
    assert (image.description, image.is_decorative) == ("", True)


def test_image_text_dry_run_and_second_run(tmp_path, index_page):
    image = library_image()
    decisions = decisions_json(tmp_path, images=[{"hash": image.file_hash, "title": "Chart", "description": "Bar chart"}])

    _, _, dry_rows = run(tmp_path, "image-text", decisions=decisions, dry_run=True)
    image.refresh_from_db()
    assert image.title == "image.png"
    assert [row["action"] for row in dry_rows] == ["would change"]

    run(tmp_path, "image-text", decisions=decisions)
    _, _, second_rows = run(tmp_path, "image-text", decisions=decisions)
    assert second_rows == []


def test_image_text_reports_a_hash_it_cannot_find(tmp_path, index_page):
    _, _, rows = run(tmp_path, "image-text", decisions=decisions_json(tmp_path, images=[{"hash": "abc", "title": "T", "description": "D"}]))

    assert rows[0]["action"] == "skipped"
    assert "youtube-posters" in rows[0]["detail"]


@pytest.mark.parametrize(
    "entry, message",
    [
        ({"hash": "abc", "title": "", "description": "D"}, "needs a hash, a title"),
        ({"hash": "abc", "title": "T" * 256, "description": "D"}, "longer than 255"),
    ],
)
def test_image_text_rejects_bad_entries(tmp_path, index_page, entry, message):
    with pytest.raises(CommandError, match=message):
        run(tmp_path, "image-text", decisions=decisions_json(tmp_path, images=[entry]))


def test_decision_fixes_need_a_decisions_file(tmp_path, index_page):
    with pytest.raises(CommandError, match="--decisions"):
        run(tmp_path, "video-alt")


def test_video_alt_set_on_the_matching_video_as_a_draft(tmp_path, make_post):
    poster = library_image()
    url = "https://www.youtube.com/watch?v=abc"
    post = make_post("post", content=[video_block("abc", poster), video_block("other", poster)])
    decisions = decisions_json(tmp_path, videos=[{"slug": "post", "video_url": url, "alt": "Ben Kingsley in the movie Sneakers"}])

    _, _, rows = run(tmp_path, "video-alt", decisions=decisions)
    _, _, second_rows = run(tmp_path, "video-alt", decisions=decisions)

    videos = [child.value for block in latest(post).content for child in block.value]
    assert [video["alt"] for video in videos] == ["Ben Kingsley in the movie Sneakers", "Post title"]
    assert [(row["action"], row["old"]) for row in rows] == [("changed", "Post title")]
    assert second_rows == []
    post.refresh_from_db()
    assert not post.live


def test_inline_alt_copies_the_description_into_the_embed(tmp_path, make_post):
    image = library_image()
    other = library_image(colour=(9, 9, 9))
    text = (
        f'<p>Before <embed alt="" embedtype="image" format="fullwidth" id="{image.pk}"/></p>'
        f'<p><embed alt="Keep me" embedtype="image" format="left" id="{other.pk}"/></p>'
    )
    post = make_post("post", content=[("text", text)])
    decisions = decisions_json(tmp_path, images=[{"hash": image.file_hash, "title": "Banner", "description": 'You keep your "peace" of mind'}])

    _, _, rows = run(tmp_path, "inline-alt", decisions=decisions)
    _, _, second_rows = run(tmp_path, "inline-alt", decisions=decisions)

    source = latest(post).content[0].value.source
    assert 'alt="You keep your &quot;peace&quot; of mind"' in source
    assert 'alt="Keep me"' in source
    assert "<p>Before " in source
    assert [(row["fix"], row["action"], row["new"]) for row in rows] == [("inline-alt", "changed", 'You keep your "peace" of mind')]
    assert second_rows == []


@responses.activate
def test_youtube_poster_kept_when_the_thumbnail_is_blank(tmp_path, make_post):
    mock_youtube({"live": {"title": "Red Panda Cam", "thumbnails": {"maxresdefault": jpeg(WIDESCREEN, (5, 5, 5))}}})
    old = hqdefault_poster("live")
    post = make_post("post", content=[video_block("live", old)])

    _, _, rows = run(tmp_path, "youtube-posters")

    assert poster_of(latest(post)).pk == old.pk
    assert rows[0]["action"] == "skipped"
    assert "blank" in rows[0]["detail"]


def test_seo_text_sets_title_tag_and_meta_description_as_a_draft(tmp_path, make_post):
    post = make_post("post")
    other = make_post("other")
    pages = [
        {"slug": "post", "seo_title": "Firefox Tab Groups: get organized", "search_description": "How to group, name and color tabs in Firefox."}
    ]
    decisions = str(tmp_path / "d.json")
    (tmp_path / "d.json").write_text(json.dumps({"pages": pages}))

    _, _, rows = run(tmp_path, "seo-text", decisions=decisions)
    _, _, second_rows = run(tmp_path, "seo-text", decisions=decisions)

    draft = latest(post)
    assert (draft.seo_title, draft.search_description) == ("Firefox Tab Groups: get organized", "How to group, name and color tabs in Firefox.")
    assert [row["detail"] for row in rows] == ["Title tag", "Meta description"]
    assert second_rows == []
    assert (latest(other).seo_title, latest(other).search_description) == ("", "")
    post.refresh_from_db()
    assert not post.live


def test_seo_text_needs_a_description(tmp_path, index_page):
    (tmp_path / "d.json").write_text(json.dumps({"pages": [{"slug": "post", "seo_title": "T", "search_description": ""}]}))
    with pytest.raises(CommandError, match="search_description"):
        run(tmp_path, "seo-text", decisions=str(tmp_path / "d.json"))


@responses.activate
def test_youtube_unreachable_skips_the_poster_but_keeps_the_other_fixes(tmp_path, make_post, mozilla, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)
    for _ in range(3):
        responses.add(responses.GET, "https://www.youtube.com/oembed", body=requests.ConnectionError("down"))
    old = hqdefault_poster("abc")
    post = make_post("post", content=[video_block("abc", old)], authors=[mozilla])

    _, _, rows = run(tmp_path, "youtube-posters", "mozilla-byline")

    assert poster_of(latest(post)).pk == old.pk
    assert author_slugs(post) == []
    assert {(row["fix"], row["action"]) for row in rows} == {("youtube-posters", "skipped"), ("mozilla-byline", "changed")}
    assert "rerun later" in next(row["detail"] for row in rows if row["fix"] == "youtube-posters")


def test_link_fixes_replace_and_unlink_in_text_and_captions(tmp_path, make_post):
    image = library_image()
    text = (
        '<p>See <a href="https://www.mozilla.org/firefox/new/?utm_source=blog.mozilla.org&amp;x=1">Firefox</a> and '
        '<a href="http://erickolb.me/gone">this post</a> and <a href="https://example.com/keep">this one</a>.</p>'
    )
    caption = '<p>Photo: <a href="https://old.example/cam">the cam</a></p>'
    post = make_post("post", content=[("text", text), ("image_caption", {"image": {"image": image, "settings": {}}, "caption": caption})])
    links = [
        {
            "slug": "post",
            "url": "https://www.mozilla.org/firefox/new/?utm_source=blog.mozilla.org&x=1",
            "action": "replace",
            "new_url": "https://www.firefox.com/en-US/?x=1&y=2",
        },
        {"slug": "post", "url": "http://erickolb.me/gone", "action": "unlink"},
        {"slug": "post", "url": "https://old.example/cam", "action": "replace", "new_url": "https://new.example/"},
    ]
    (tmp_path / "d.json").write_text(json.dumps({"links": links}))

    _, _, rows = run(tmp_path, "link-fixes", decisions=str(tmp_path / "d.json"))
    _, _, second_rows = run(tmp_path, "link-fixes", decisions=str(tmp_path / "d.json"))

    draft = latest(post)
    source = draft.content[0].value.source
    assert 'href="https://www.firefox.com/en-US/?x=1&amp;y=2"' in source
    assert "mozilla.org" not in source
    assert "and this post and" in source
    assert 'href="https://example.com/keep"' in source
    assert 'href="https://new.example/"' in draft.content[1].value["caption"].source
    assert sorted(row["detail"] for row in rows) == ["new address", "new address", "removed the link, kept its text"]
    assert second_rows == []


def test_link_fixes_need_a_new_url_to_replace(tmp_path, index_page):
    (tmp_path / "d.json").write_text(json.dumps({"links": [{"slug": "post", "url": "https://a.example/", "action": "replace", "new_url": ""}]}))
    with pytest.raises(CommandError, match="links entry 1"):
        run(tmp_path, "link-fixes", decisions=str(tmp_path / "d.json"))


@responses.activate
def test_youtube_block_keeps_its_poster_when_youtube_refuses(tmp_path, make_post):
    # A 403 from a blocked or rate-limited server is not the same as a missing thumbnail.
    # Registered first, because the first matching mock answers.
    responses.add(responses.GET, "https://img.youtube.com/vi/abc/maxresdefault.jpg", status=403)
    mock_youtube({"abc": widescreen_video()})
    old = hqdefault_poster("abc")
    post = make_post("post", content=[video_block("abc", old)])

    _, _, rows = run(tmp_path, "youtube-posters")

    assert poster_of(latest(post)).pk == old.pk
    assert rows[0]["action"] == "skipped"
    assert "rerun later" in rows[0]["detail"]


def test_inline_alt_keeps_backslashes(tmp_path, make_post):
    image = library_image()
    post = make_post("post", content=[("text", f'<p><embed alt="" embedtype="image" format="left" id="{image.pk}"/></p>')])
    decisions = decisions_json(tmp_path, images=[{"hash": image.file_hash, "title": "Path", "description": r"Settings saved in C:\Users\me"}])

    run(tmp_path, "inline-alt", decisions=decisions)

    assert r'alt="Settings saved in C:\Users\me"' in latest(post).content[0].value.source


def test_one_failing_author_does_not_stop_the_others(tmp_path, index_page, monkeypatch):
    BlogAuthor.objects.create(name="ada", slug="ada", locale=Locale.get_default())
    BlogAuthor.objects.create(name="grace", slug="grace", locale=Locale.get_default())
    real_save_revision = BlogAuthor.save_revision

    def save_revision(self, *args, **kwargs):
        if self.slug == "ada":
            raise RuntimeError("database said no")
        return real_save_revision(self, *args, **kwargs)

    monkeypatch.setattr(BlogAuthor, "save_revision", save_revision)

    _, _, rows = run(tmp_path, "author-names", author_names=names_csv(tmp_path, ("ada", "Ada"), ("grace", "Grace")))

    assert [(row["slug"], row["action"]) for row in rows] == [("ada", "failed"), ("grace", "changed")]
    assert BlogAuthor.objects.get(slug="grace").name == "Grace"
