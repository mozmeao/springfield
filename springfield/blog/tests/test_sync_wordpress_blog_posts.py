# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import csv
import json
import os
from io import BytesIO, StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

import pytest
import responses
from PIL import Image
from responses import matchers
from wagtail.models import Locale, Page, Revision, Site
from wagtail.utils.file import hash_filelike

from springfield.blog.management.commands import fix_imported_blog_posts, import_wordpress_blog_posts, import_wordpress_blog_translations
from springfield.blog.management.commands.fix_imported_blog_posts import TAGS, TOPICS
from springfield.blog.models import BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTag, BlogTopic
from springfield.cms.models import SpringfieldImage

pytestmark = [pytest.mark.django_db]

WORDPRESS = "https://blog.mozilla.org"
UPLOADS = f"{WORDPRESS}/wp-content/uploads/2026/10"
ASSETS = "https://assets.mozilla.net/blog"
PLACEHOLDER = {"webm_url": f"{ASSETS}/placeholder.webm", "poster_url": f"{ASSETS}/placeholder.jpg"}


def png(colour):
    buffer = BytesIO()
    Image.new("RGB", (40, 20), colour).save(buffer, "PNG")
    return buffer.getvalue()


def file_hash(content):
    return hash_filelike(BytesIO(content))


HERO = png((200, 0, 0))
BODY = png((0, 200, 0))
OTHER = png((0, 0, 200))
POSTER = png((90, 90, 90))
GERMAN_HERO = png((200, 200, 0))


def serve(url, content):
    responses.add(responses.GET, url, body=content, content_type="image/png")


def export_post(wp_id=101, slug="first-post", title="First post", content=None, date="2026-10-21 09:00:00", hero_url=f"{UPLOADS}/hero.png"):
    content = content if content is not None else f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><p>Hello world.</p>'
    return f"""
    <post>
        <ID>{wp_id}</ID>
        <Title>{title}</Title>
        <Content><![CDATA[{content}]]></Content>
        <Date>{date}</Date>
        <PostType>post</PostType>
        <Permalink>{WORDPRESS}/en/products/firefox/{slug}/</Permalink>
        <ImageURL>{hero_url}</ImageURL>
        <ImageFeatured>{hero_url}</ImageFeatured>
        <Categories>Firefox Features</Categories>
        <Tags>browser</Tags>
        <Authors>someone</Authors>
        <AuthorFirstName>Some</AuthorFirstName>
        <AuthorLastName>One</AuthorLastName>
        <Slug>{slug}</Slug>
    </post>
    """


def sync_post(wp_id=101, slug="first-post", **overrides):
    return {
        "import": True,
        "wp_id": wp_id,
        "wp_slug": slug,
        "slug": slug,
        "topic": "ai",
        "tags": ["switching", "campaigns"],
        "seo_title": "First post | Firefox",
        "search_description": "Everything about the first post.",
        "authors": [],
        "hero": {"image": "featured", "hash": file_hash(HERO), "alt": "A red hero", "style": "standard_image"},
        "image_alt": [],
        "videos": [],
        "media": [],
        "links": [],
        "exclude_from_rss": False,
        "translations": [],
        **overrides,
    }


def sync_data(*posts, images=None, **extra):
    images = images or [
        {"hash": file_hash(HERO), "title": "Hero", "description": "A red rectangle"},
        {"hash": file_hash(BODY), "title": "Body", "description": "A green rectangle"},
    ]
    return {
        "format": 1,
        "sync": "2026-11-03",
        "wordpress_url": WORDPRESS,
        "placeholder": PLACEHOLDER,
        "posts": list(posts),
        "images": images,
        **extra,
    }


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    for module in (import_wordpress_blog_posts, fix_imported_blog_posts, import_wordpress_blog_translations):
        monkeypatch.setattr(module.time, "sleep", lambda seconds: None)


def publish(model, **fields):
    snippet = model(live=False, **fields)
    snippet.save()
    snippet.save_revision().publish()
    return snippet


@pytest.fixture
def blog(minimal_site):
    Locale.objects.get_or_create(language_code="de")
    english = Locale.get_default()
    for term in TOPICS:
        publish(BlogTopic, name=term.name, slug=term.slug, locale=english)
    for term in TAGS:
        publish(BlogTag, name=term.name, slug=term.slug, locale=english)
    index = BlogIndexPage(title="Blog", slug="blog", locale=english)
    Site.objects.get(is_default_site=True).root_page.add_child(instance=index)
    index.save_revision().publish()
    return index


class Run:
    def __init__(self, out, stdout, stderr):
        self.out, self.stdout, self.stderr = out, stdout, stderr

    def rows(self, name="report.csv"):
        with open(self.out / name, newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    def actions(self):
        return [(row["slug"], row["locale"], row["action"]) for row in self.rows()]

    def text(self, name):
        return (self.out / name).read_text()


def run_sync(tmp_path, data, *posts, export=True, **options):
    tmp_path.mkdir(parents=True, exist_ok=True)
    sync_path = tmp_path / "sync.json"
    sync_path.write_text(json.dumps(data))
    out = tmp_path / "out"
    stdout, stderr = StringIO(), StringIO()
    if export:
        export_path = tmp_path / "export.xml"
        export_path.write_text(f"<data>{''.join(posts)}</data>")
        options["export"] = str(export_path)
    call_command("sync_wordpress_blog_posts", str(sync_path), out=str(out), stdout=stdout, stderr=stderr, skip_checks=False, **options)
    return Run(out, stdout.getvalue(), stderr.getvalue())


def failing_run(tmp_path, data, *posts, **options):
    with pytest.raises(CommandError) as raised:
        run_sync(tmp_path, data, *posts, **options)
    return Run(tmp_path / "out", "", ""), str(raised.value)


def serve_post_images():
    serve(f"{UPLOADS}/hero.png", HERO)
    serve(f"{UPLOADS}/body.png", BODY)
    serve(PLACEHOLDER["webm_url"], b"webm")
    serve(PLACEHOLDER["poster_url"], POSTER)


def created_page(slug="first-post"):
    return BlogArticlePage.objects.get(locale=Locale.get_default(), slug=slug)


def body_values(page, block_type):
    values = []
    for block in page.content.raw_data:
        if block["type"] == "media":
            values += [child["value"] for child in block["value"] if child["type"] == block_type]
    return values


# -------------------------------------------------------------------------
# Nothing is written unless every post checks out
# -------------------------------------------------------------------------


@responses.activate
def test_a_topic_that_isnt_published_stops_the_run_and_every_file_is_written(tmp_path, blog):
    BlogTopic.objects.filter(slug="ai").update(live=False)
    serve_post_images()

    run, error = failing_run(tmp_path, sync_data(sync_post()), export_post())

    assert "topic 'ai' isn't published" in error
    assert not BlogArticlePage.objects.filter(slug="first-post").exists()
    assert sorted(path.name for path in run.out.iterdir()) == [
        "check.csv",
        "hand-steps.md",
        "redirects.csv",
        "report.csv",
        "summary.md",
        "warnings.csv",
    ]
    assert "topic 'ai' isn't published" in run.text("summary.md")


@responses.activate
def test_output_files_are_overwritten(tmp_path, blog):
    serve_post_images()
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "warnings.csv").write_text("stale\n")

    run = run_sync(tmp_path, sync_data(sync_post()), export_post())

    assert "stale" not in run.text("warnings.csv")


@responses.activate
def test_a_post_not_imported_is_listed_with_its_note(tmp_path, blog):
    serve_post_images()
    data = sync_data(sync_post(), {"import": False, "wp_id": 200, "wp_slug": "a-mozilla-post", "note": "Mozilla, not Firefox"})

    run = run_sync(tmp_path, data, export_post())

    assert ("a-mozilla-post", "", "not imported") in run.actions()
    assert "not imported: Mozilla, not Firefox" in run.text("report.csv")


@responses.activate
def test_a_post_missing_from_the_export_stops_the_run(tmp_path, blog):
    serve_post_images()

    _, error = failing_run(tmp_path, sync_data(sync_post(), sync_post(wp_id=102, slug="second-post")), export_post())

    assert "post second-post (wp_id 102) is not in the export" in error
    assert not BlogArticlePage.objects.filter(slug="first-post").exists()


@responses.activate
def test_a_post_in_the_export_but_not_the_sync_file_is_ignored(tmp_path, blog):
    serve_post_images()

    run = run_sync(tmp_path, sync_data(sync_post()), export_post(), export_post(wp_id=55, slug="an-old-post"))

    assert [slug for slug, _, _ in run.actions()] == ["first-post"]


@responses.activate
def test_an_export_naming_the_id_element_in_lowercase_is_read(tmp_path, blog):
    serve_post_images()

    run_sync(tmp_path, sync_data(sync_post()), export_post().replace("<ID>101</ID>", "<id>101</id>"))

    assert created_page().live


@responses.activate
def test_an_image_changed_since_review_stops_the_run(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", OTHER)
    serve(f"{UPLOADS}/body.png", BODY)

    _, error = failing_run(tmp_path, sync_data(sync_post()), export_post())

    assert f"post first-post: hero image changed: expected hash {file_hash(HERO)}, found {file_hash(OTHER)}" in error
    assert not SpringfieldImage.objects.exists()


@responses.activate
def test_a_body_image_with_no_decision_stops_the_run(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", HERO)
    serve(f"{UPLOADS}/body.png", OTHER)

    _, error = failing_run(tmp_path, sync_data(sync_post()), export_post())

    assert f"image {UPLOADS}/body.png (position 1) has hash {file_hash(OTHER)}, which the sync file has no images entry for" in error


@responses.activate
def test_a_body_image_that_wont_download_stops_the_run(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", HERO)
    responses.add(responses.GET, f"{UPLOADS}/body.png", status=404)

    _, error = failing_run(tmp_path, sync_data(sync_post()), export_post())

    assert f"post first-post: could not download image {UPLOADS}/body.png (position 1)" in error


@responses.activate
def test_an_alt_position_holding_another_image_stops_the_run(tmp_path, blog):
    serve_post_images()
    post = sync_post(image_alt=[{"position": 1, "hash": file_hash(HERO), "alt": "Not this one"}])

    _, error = failing_run(tmp_path, sync_data(post), export_post())

    assert "image_alt position 1 expects hash" in error


@responses.activate
def test_drop_body_duplicate_on_a_post_whose_first_image_isnt_the_hero_stops_the_run(tmp_path, blog):
    serve_post_images()
    post = sync_post()
    post["hero"]["drop_body_duplicate"] = True

    _, error = failing_run(tmp_path, sync_data(post), export_post())

    assert "drop_body_duplicate is set, but the first image block isn't the hero" in error


# -------------------------------------------------------------------------
# Each English page built complete
# -------------------------------------------------------------------------


@responses.activate
def test_a_page_gets_exactly_the_reviewed_topic_and_tags_and_creates_no_snippets(tmp_path, blog):
    serve_post_images()
    topics, tags = BlogTopic.objects.count(), BlogTag.objects.count()

    run_sync(tmp_path, sync_data(sync_post()), export_post())

    page = created_page()
    assert page.topic.slug == "ai"
    assert sorted(tag.slug for tag in page.tags.all()) == ["campaigns", "switching"]
    assert (BlogTopic.objects.count(), BlogTag.objects.count()) == (topics, tags)


@responses.activate
def test_the_only_revision_has_the_reviewed_fields_and_not_the_exports_byline(tmp_path, blog):
    serve_post_images()
    author = publish(BlogAuthor, name="Bobby Holley", slug="bobby-holley", locale=Locale.get_default())
    post = sync_post(authors=[{"slug": "bobby-holley"}, {"new": "New Person"}])

    run_sync(tmp_path, sync_data(post), export_post())

    page = created_page()
    assert page.revisions.count() == 1
    assert page.live and not page.has_unpublished_changes
    assert (page.seo_title, page.search_description) == ("First post | Firefox", "Everything about the first post.")
    assert [placement.author for placement in page.article_authors.all()] == [author, BlogAuthor.objects.get(slug="new-person")]
    assert BlogAuthor.objects.get(slug="new-person").live
    assert not BlogAuthor.objects.filter(slug__in=["someone", "some-one"]).exists()
    assert page.image.file_hash == file_hash(HERO)
    assert page.image_alt == "A red hero"
    assert page.first_published_at.isoformat() == "2026-10-21T16:00:00+00:00"


@responses.activate
def test_a_page_that_fails_leaves_no_page_or_images_and_the_others_are_created(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", HERO)
    serve(f"{UPLOADS}/body.png", BODY)
    serve(f"{UPLOADS}/broken.png", b"\x89PNG not really")
    data = sync_data(
        sync_post(hero={"image": "featured", "hash": file_hash(b"\x89PNG not really"), "alt": "Broken"}),
        sync_post(wp_id=102, slug="second-post"),
        images=[
            {"hash": file_hash(HERO), "title": "Hero", "description": "A red rectangle"},
            {"hash": file_hash(BODY), "title": "Body", "description": "A green rectangle"},
            {"hash": file_hash(b"\x89PNG not really"), "title": "Broken", "description": "Broken"},
        ],
    )

    run, error = failing_run(tmp_path, data, export_post(hero_url=f"{UPLOADS}/broken.png"), export_post(wp_id=102, slug="second-post"))

    assert "1 failed" in error
    assert ("first-post", "en-US", "failed") in run.actions()
    assert not BlogArticlePage.objects.filter(slug="first-post").exists()
    assert created_page("second-post").live
    assert SpringfieldImage.objects.filter(file_hash=file_hash(BODY)).count() == 1


@responses.activate
@pytest.mark.parametrize(
    "content",
    [
        f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><p>Hello.</p>',
        f'<ul><li>Inline <img src="{UPLOADS}/body.png" alt=""></li></ul>',
    ],
    ids=["block", "inline"],
)
def test_a_body_image_that_cant_be_saved_fails_the_post(tmp_path, blog, content):
    serve(f"{UPLOADS}/hero.png", HERO)
    serve(f"{UPLOADS}/body.png", b"\x89PNG not really")
    images = [
        {"hash": file_hash(HERO), "title": "Hero", "description": "A red rectangle"},
        {"hash": file_hash(b"\x89PNG not really"), "title": "Broken", "description": "Broken"},
    ]

    run, error = failing_run(tmp_path, sync_data(sync_post(), images=images), export_post(content=content))

    assert "1 failed" in error
    assert f"could not import the image {UPLOADS}/body.png" in run.rows()[0]["detail"]
    assert not BlogArticlePage.objects.filter(slug="first-post").exists()


@responses.activate
def test_a_decorative_hero_is_published_with_empty_alt(tmp_path, blog):
    serve_post_images()
    images = [
        {"hash": file_hash(HERO), "title": "Hero", "decorative": True},
        {"hash": file_hash(BODY), "title": "Body", "description": "A green rectangle"},
    ]
    post = sync_post(hero={"image": "featured", "hash": file_hash(HERO), "alt": "", "style": "standard_image"})

    run_sync(tmp_path, sync_data(post, images=images), export_post())

    page = created_page()
    assert page.live
    assert page.image_alt == ""
    assert page.image.is_decorative


@responses.activate
def test_links_point_at_migrated_posts_and_this_runs_posts(tmp_path, blog, make_article):
    serve_post_images()
    publish_migrated = BlogArticlePage(title="Old", slug="an-old-post", topic=BlogTopic.objects.get(slug="ai"), hero_style="text_only", content=[])
    blog.add_child(instance=publish_migrated)
    links = (
        f'<p><a href="{WORDPRESS}/en/firefox/an-old-post/">old</a> <a href="{WORDPRESS}/en/firefox/second-wp/">same run</a> '
        f'<a href="{WORDPRESS}/en/mozilla/netpolicy/">stays</a> <a href="https://example.com/gone">gone</a></p>'
    )
    data = sync_data(
        sync_post(links=[{"url": "https://example.com/gone", "action": "unlink"}]),
        sync_post(wp_id=102, slug="second-post", wp_slug="second-wp"),
    )

    run_sync(tmp_path, data, export_post(content=links), export_post(wp_id=102, slug="second-wp", content="<p>Two.</p>"))

    html = created_page().content.raw_data[0]["value"]
    assert 'href="/en-US/blog/an-old-post/"' in html
    assert 'href="/en-US/blog/second-post/"' in html
    assert f'href="{WORDPRESS}/en/mozilla/netpolicy/"' in html
    assert "example.com/gone" not in html and "gone" in html


@responses.activate
def test_a_link_decision_on_a_migrated_post_wins_over_the_automatic_relink(tmp_path, blog):
    serve_post_images()
    old = BlogArticlePage(title="Old", slug="an-old-post", topic=BlogTopic.objects.get(slug="ai"), hero_style="text_only", content=[])
    blog.add_child(instance=old)
    url = f"{WORDPRESS}/en/firefox/an-old-post/"
    post = sync_post(links=[{"url": url, "action": "unlink"}])

    run_sync(tmp_path, sync_data(post), export_post(content=f'<p><a href="{url}">old</a> stays</p>'))

    html = created_page().content.raw_data[0]["value"]
    assert "<a" not in html
    assert "old stays" in html


@responses.activate
def test_a_caption_link_to_a_post_in_this_run_points_at_its_new_page_and_is_checked(tmp_path, blog):
    serve_post_images()
    content = (
        f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt="">'
        f'<figcaption><a href="{WORDPRESS}/en/firefox/second-wp/">More</a></figcaption></figure><p>Hello.</p>'
    )
    data = sync_data(sync_post(), sync_post(wp_id=102, slug="second-post", wp_slug="second-wp"))

    run = run_sync(tmp_path, data, export_post(content=content), export_post(wp_id=102, slug="second-wp", content="<p>Two.</p>"))

    [caption] = [block["value"]["caption"] for block in created_page().content.raw_data if block["type"] == "image_caption"]
    assert 'href="/en-US/blog/second-post/"' in caption
    [links] = [row for row in run.rows("check.csv") if (row["slug"], row["check"]) == ("first-post", "links")]
    assert links["result"] == "pass"


@responses.activate
def test_each_use_of_an_image_gets_its_own_alt_and_the_library_text_is_the_reviewed_one(tmp_path, blog):
    serve_post_images()
    data = sync_data(
        sync_post(image_alt=[{"position": 1, "hash": file_hash(BODY), "alt": "Green, in the first post"}]),
        sync_post(wp_id=102, slug="second-post", image_alt=[{"position": 1, "hash": file_hash(BODY), "alt": "Green, in the second post"}]),
        sync_post(wp_id=103, slug="third-post"),
    )

    run_sync(tmp_path, data, export_post(), export_post(wp_id=102, slug="second-post"), export_post(wp_id=103, slug="third-post"))

    alts = [body_values(created_page(slug), "image")[0]["image_alt"] for slug in ("first-post", "second-post", "third-post")]
    assert alts == ["Green, in the first post", "Green, in the second post", "A green rectangle"]
    image = SpringfieldImage.objects.get(file_hash=file_hash(BODY))
    assert (image.title, image.description) == ("Body", "A green rectangle")


@responses.activate
def test_an_inline_image_gets_its_reviewed_alt(tmp_path, blog):
    serve_post_images()
    content = f'<ul><li>A list item <img src="{UPLOADS}/body.png" alt="body.png"></li></ul>'
    post = sync_post(image_alt=[{"position": 1, "hash": file_hash(BODY), "alt": "A green box, inline"}])

    run_sync(tmp_path, sync_data(post), export_post(content=content))

    assert 'alt="A green box, inline"' in created_page().content.raw_data[0]["value"]


@responses.activate
def test_a_hero_repeated_as_the_first_image_is_dropped_when_asked(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", HERO)
    post = sync_post()
    post["hero"]["drop_body_duplicate"] = True
    content = f'<figure class="wp-block-image"><img src="{UPLOADS}/hero.png" alt=""></figure><p>Hello world.</p>'

    run_sync(tmp_path, sync_data(post), export_post(content=content))

    page = created_page()
    assert body_values(page, "image") == []
    assert page.image.file_hash == file_hash(HERO)


@responses.activate
def test_a_video_hero_moves_the_first_youtube_video_into_the_header_with_its_reviewed_alt(tmp_path, blog):
    serve_post_images()
    thumbnail = BytesIO()
    Image.new("RGB", (64, 36), (200, 30, 30)).save(thumbnail, "JPEG")
    responses.add(responses.GET, "https://www.youtube.com/oembed", json={"title": "Launch film", "width": 200, "height": 113})
    responses.add(responses.GET, "https://img.youtube.com/vi/abc123/maxresdefault.jpg", body=thumbnail.getvalue(), content_type="image/jpeg")
    content = (
        '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://www.youtube.com/watch?v=abc123</div></figure><p>Hello world.</p>'
    )
    post = sync_post(videos=[{"video_url": "https://www.youtube.com/watch?v=abc123", "alt": "The launch film"}])
    post["hero"]["style"] = "video"

    run_sync(tmp_path, sync_data(post), export_post(content=content))

    page = created_page()
    video = page.hero_video.raw_data[0]["value"]
    assert (page.hero_style, video["video_url"], video["alt"]) == ("video", "https://www.youtube.com/watch?v=abc123", "The launch film")
    assert SpringfieldImage.objects.get(pk=video["poster"]).title == "Launch film"
    assert body_values(page, "video") == []
    assert page.image.file_hash == file_hash(HERO)


@responses.activate
@pytest.mark.parametrize("dry_run", [True, False], ids=["dry run", "real run"])
def test_a_youtube_video_with_no_poster_stops_the_run(tmp_path, blog, dry_run):
    serve_post_images()
    responses.add(responses.GET, "https://www.youtube.com/oembed", status=404)
    responses.add(responses.GET, responses.matchers.re.compile(r"https://img\.youtube\.com/vi/.+"), status=404)
    content = '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://www.youtube.com/watch?v=abc123</div></figure>'

    _, error = failing_run(tmp_path, sync_data(sync_post()), export_post(content=content), dry_run=dry_run)

    assert "post first-post: no poster from YouTube for video abc123" in error
    assert not BlogArticlePage.objects.filter(slug="first-post").exists()


# -------------------------------------------------------------------------
# Self-hosted video and GIFs
# -------------------------------------------------------------------------


@responses.activate
def test_a_self_hosted_video_becomes_a_placeholder_animation_with_a_hand_step(tmp_path, blog):
    serve_post_images()
    serve(PLACEHOLDER["poster_url"], POSTER)
    clip = f"{UPLOADS}/sounds.mp4"
    content = f'<h2>Listen</h2><figure class="wp-block-video"><video controls src="{clip}"></video></figure><p>After.</p>'
    post = sync_post(media=[{"src": clip, "kind": "video", "alt": "Firefox sounds playing"}])

    run = run_sync(tmp_path, sync_data(post), export_post(content=content))

    animation = body_values(created_page(), "animation")[0]
    assert (animation["video_url"], animation["alt"]) == (PLACEHOLDER["webm_url"], "Firefox sounds playing")
    assert f"## first-post\n\n- [ ] Block 2 (“Listen”): replace the placeholder animation with a webm of [sounds.mp4]({clip})" in run.text(
        "hand-steps.md"
    )


@responses.activate
def test_a_gif_needing_a_webm_is_never_downloaded_and_shares_the_placeholder_poster(tmp_path, blog):
    serve_post_images()
    serve(PLACEHOLDER["poster_url"], POSTER)
    gif = f"{UPLOADS}/huge.gif"
    clip = f"{UPLOADS}/clip.mp4"
    content = f'<figure class="wp-block-image"><img src="{gif}" alt=""></figure><video src="{clip}"></video>'
    post = sync_post(media=[{"src": gif, "kind": "gif", "alt": "A big animation"}, {"src": clip, "kind": "video", "alt": "A clip"}])

    run_sync(tmp_path, sync_data(post), export_post(content=content))

    page = created_page()
    animations = body_values(page, "animation")
    assert [animation["alt"] for animation in animations] == ["A big animation", "A clip"]
    assert animations[0]["poster"] == animations[1]["poster"]
    assert not any(call.request.url == gif for call in responses.calls)
    page.full_clean()
    assert "placeholder.webm" in str(page.content)


@responses.activate
def test_a_placeholder_poster_can_be_an_image_file_beside_the_sync_file(tmp_path, blog):
    serve_post_images()
    (tmp_path / "placeholder-poster.png").write_bytes(POSTER)
    clips = [f"{UPLOADS}/one.mp4", f"{UPLOADS}/two.mp4"]
    post = sync_post(media=[{"src": clip, "kind": "video", "alt": "A clip"} for clip in clips])
    data = sync_data(post, placeholder={**PLACEHOLDER, "poster_url": "placeholder-poster.png"})

    run_sync(tmp_path, data, export_post(content="".join(f'<video src="{clip}"></video>' for clip in clips)))

    posters = [animation["poster"] for animation in body_values(created_page(), "animation")]
    assert len(set(posters)) == 1
    assert SpringfieldImage.objects.get(pk=posters[0]).file_hash == file_hash(POSTER)


def test_a_placeholder_poster_file_missing_beside_the_sync_file_stops_the_run(tmp_path, blog):
    data = sync_data(
        sync_post(media=[{"src": f"{UPLOADS}/one.mp4", "kind": "video", "alt": "A clip"}]), placeholder={**PLACEHOLDER, "poster_url": "missing.png"}
    )

    _, error = failing_run(tmp_path, data, export_post())

    assert "placeholder: poster file not found" in error
    assert not BlogArticlePage.objects.exists()


@responses.activate
def test_a_placeholder_webm_that_isnt_online_stops_the_run(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", HERO)
    serve(f"{UPLOADS}/body.png", BODY)
    serve(PLACEHOLDER["poster_url"], POSTER)
    responses.add(responses.GET, PLACEHOLDER["webm_url"], status=404)
    data = sync_data(sync_post(media=[{"src": f"{UPLOADS}/one.mp4", "kind": "video", "alt": "A clip"}]))

    _, error = failing_run(tmp_path, data, export_post(content=f'<video src="{UPLOADS}/one.mp4"></video>'))

    assert f"placeholder: {PLACEHOLDER['webm_url']} isn't online (404)" in error
    assert not BlogArticlePage.objects.exists()


@responses.activate
def test_media_with_its_own_webm_becomes_an_animation_with_no_hand_step(tmp_path, blog):
    serve_post_images()
    serve(f"{ASSETS}/clip.jpg", POSTER)
    clip = f"{UPLOADS}/clip.mp4"
    post = sync_post(media=[{"src": clip, "kind": "video", "alt": "A clip", "webm_url": f"{ASSETS}/clip.webm", "poster_url": f"{ASSETS}/clip.jpg"}])

    run = run_sync(tmp_path, sync_data(post), export_post(content=f'<video src="{clip}"></video>'))

    assert body_values(created_page(), "animation")[0]["video_url"] == f"{ASSETS}/clip.webm"
    assert "placeholder" not in run.text("hand-steps.md")


# -------------------------------------------------------------------------
# Translations, and fixing existing translation heroes
# -------------------------------------------------------------------------


def mock_translation(slug="first-post", language="de", wp_id=201, status=200, hero=GERMAN_HERO, english_body=None, translated_body=None):
    english_link = f"{WORDPRESS}/en/products/firefox/{slug}/"
    translated_slug = f"{slug}-{language}"
    english = {"id": 101, "slug": slug, "date": "2026-10-21T09:00:00", "link": english_link, "title": {"rendered": "First post"}}
    translated = {
        "id": wp_id,
        "slug": translated_slug,
        "date": "2026-10-22T09:00:00",
        "link": f"{WORDPRESS}/{language}/products/firefox/{translated_slug}/",
        "title": {"rendered": "Erster Beitrag"},
    }
    image = f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure>'
    english_body = english_body or f"{image}<p>Hello world.</p>"
    translated_body = translated_body or f"{image}<p>Hallo Welt.</p>"
    for post, content in ((english, english_body), (translated, translated_body)):
        post.update(excerpt={"rendered": ""}, content={"rendered": content}, yoast_head_json={})
    responses.add(
        responses.GET,
        f"{WORDPRESS}/en/wp-json/wp/v2/posts",
        json=[english],
        match=[matchers.query_param_matcher({"slug": slug}, strict_match=False)],
    )
    for _ in range(3 if status != 200 else 0):
        responses.add(
            responses.GET,
            f"{WORDPRESS}/{language}/wp-json/wp/v2/posts",
            status=status,
            match=[matchers.query_param_matcher({"slug": translated_slug}, strict_match=False)],
        )
    responses.add(
        responses.GET,
        f"{WORDPRESS}/{language}/wp-json/wp/v2/posts",
        json=[translated],
        match=[matchers.query_param_matcher({"slug": translated_slug}, strict_match=False)],
    )
    responses.add(responses.GET, english_link, body=f'<link rel="alternate" hreflang="{language}" href="{translated["link"]}">')
    mock_featured_image(language, wp_id, content=hero, body=translated_body, link=translated["link"])
    return translated


def mock_featured_image(language, wp_id, content=GERMAN_HERO, body=None, link=None):
    body = body or f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><p>Hallo Welt.</p>'
    post = {"featured_media": 77, "content": {"rendered": body}, "link": link or f"{WORDPRESS}/{language}/products/firefox/first-post-{language}/"}
    responses.add(responses.GET, f"{WORDPRESS}/{language}/wp-json/wp/v2/posts/{wp_id}", json=post)
    responses.add(responses.GET, f"{WORDPRESS}/{language}/wp-json/wp/v2/media/77", json={"source_url": f"{UPLOADS}/{language}-hero-{wp_id}.png"})
    serve(f"{UPLOADS}/{language}-hero-{wp_id}.png", content)


def translated_post(language="de", wp_id=201):
    return {
        "locale": language,
        "import": True,
        "wp_id": wp_id,
        "wp_slug": f"first-post-{language}",
        "hero": {"hash": file_hash(GERMAN_HERO), "alt": "Ein gelbes Bild"},
    }


def translation_of(page, language="de"):
    return BlogArticlePage.objects.get(locale__language_code=language, translation_key=page.translation_key)


@responses.activate
def test_a_translation_is_published_with_its_wordpress_hero(tmp_path, blog):
    serve_post_images()
    mock_translation()

    run = run_sync(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post())

    german = translation_of(created_page())
    assert german.live and not german.has_unpublished_changes
    assert (german.image.file_hash, german.image_alt) == (file_hash(GERMAN_HERO), "Ein gelbes Bild")
    assert german.live_revision.as_object().image_id == german.image_id
    assert ("first-post", "de", "created") in run.actions()


@responses.activate
def test_a_translation_whose_wordpress_hero_changed_stops_the_run(tmp_path, blog):
    serve_post_images()
    mock_featured_image("de", 201, content=OTHER)

    _, error = failing_run(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post())

    assert "post first-post de: hero image changed" in error


@responses.activate
def test_a_translation_with_no_reviewed_hero_whose_wordpress_hero_differs_stops_the_run(tmp_path, blog):
    serve_post_images()
    mock_featured_image("de", 201)
    translation = {**translated_post(), "hero": {}}

    run, error = failing_run(tmp_path, sync_data(sync_post(translations=[translation])), export_post())

    assert f"post first-post de: the WordPress hero ({file_hash(GERMAN_HERO)}) differs from the English one" in error
    assert not BlogArticlePage.objects.exists()


@responses.activate
def test_a_translation_missing_from_wordpress_stops_the_run(tmp_path, blog):
    serve_post_images()
    responses.add(responses.GET, f"{WORDPRESS}/de/wp-json/wp/v2/posts/201", status=404)

    _, error = failing_run(tmp_path, sync_data(sync_post(translations=[{**translated_post(), "hero": {}}])), export_post())

    assert "post first-post de: could not read the translation from WordPress" in error
    assert not BlogArticlePage.objects.exists()


@responses.activate
def test_a_translation_with_no_wordpress_hero_keeps_the_english_one(tmp_path, blog):
    serve_post_images()
    mock_translation()
    body = f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><p>Hallo Welt.</p>'
    responses.replace(responses.GET, f"{WORDPRESS}/de/wp-json/wp/v2/posts/201", json={"featured_media": 0, "content": {"rendered": body}})

    run = run_sync(tmp_path, sync_data(sync_post(translations=[{**translated_post(), "hero": {}}])), export_post())

    assert translation_of(created_page()).image.file_hash == file_hash(HERO)
    assert {row["check"]: row["result"] for row in run.rows("check.csv") if row["locale"] == "de"} == {
        "translation": "pass",
        "translation hero": "pass",
        "translation body images": "pass",
        "translation youtube": "pass",
    }


@responses.activate
def test_a_translation_missing_its_youtube_video_gets_a_step_to_add_it(tmp_path, blog):
    serve_post_images()
    mock_translation()
    video = '<iframe src="https://www.youtube.com/embed/E2AoYIKwJqM"></iframe>'
    body = f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure>{video}<p>Hallo Welt.</p>'
    responses.replace(responses.GET, f"{WORDPRESS}/de/wp-json/wp/v2/posts/201", json={"featured_media": 77, "content": {"rendered": body}})

    run = run_sync(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post())

    assert check_results(run)[("de", "translation youtube")]["result"] == "fail"
    assert "- [ ] de: Add the YouTube video [E2AoYIKwJqM](https://www.youtube.com/watch?v=E2AoYIKwJqM)" in run.text("hand-steps.md")


@responses.activate
def test_a_translation_gets_its_own_youtube_video_when_the_review_gives_no_image_pairs(tmp_path, blog):
    serve_post_images()
    thumbnail = BytesIO()
    Image.new("RGB", (64, 36), (200, 30, 30)).save(thumbnail, "JPEG")
    responses.add(responses.GET, "https://www.youtube.com/oembed", json={"title": "Film", "width": 200, "height": 113})
    responses.add(responses.GET, matchers.re.compile(r"https://img\.youtube\.com/vi/.+"), body=thumbnail.getvalue(), content_type="image/jpeg")

    def iframe(video):
        return f'<iframe src="https://www.youtube.com/embed/{video}?feature=oembed"></iframe>'

    mock_translation(english_body=f"{iframe('englishvid1')}<p>Hello world.</p>", translated_body=f"{iframe('germanvid01')}<p>Hallo Welt.</p>")
    export_body = '<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">https://www.youtube.com/watch?v=englishvid1</div></figure>'
    post = sync_post(videos=[{"video_url": "https://www.youtube.com/watch?v=englishvid1", "alt": "The film"}], translations=[translated_post()])

    run = run_sync(tmp_path, sync_data(post), export_post(content=f"{export_body}<p>Hello world.</p>"))

    [video] = body_values(translation_of(created_page()), "video")
    assert video["video_url"] == "https://www.youtube.com/watch?v=germanvid01"
    assert check_results(run)[("de", "translation youtube")]["result"] == "pass"


@responses.activate
def test_an_image_the_translation_shares_with_the_english_post_passes_its_check(tmp_path, blog):
    serve_post_images()
    serve(f"{UPLOADS}/shared-1024x576.png", BODY)
    serve(f"{UPLOADS}/shared.png", OTHER)
    figure = f'<figure class="wp-block-image"><img src="{UPLOADS}/shared-1024x576.png" alt=""></figure>'
    mock_translation(english_body=f"{figure}<p>Hello world.</p>", translated_body=f"{figure}<p>Hallo Welt.</p>")

    run = run_sync(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post(content=f"{figure}<p>Hello world.</p>"))

    assert check_results(run)[("de", "translation body images")]["result"] == "pass"


@responses.activate
def test_a_shared_image_with_translated_alt_gets_the_full_size_copy_and_passes_its_check(tmp_path, blog):
    serve_post_images()
    serve(f"{UPLOADS}/shared-1024x576.png", BODY)
    serve(f"{UPLOADS}/shared.png", OTHER)

    def figure(alt):
        return f'<figure class="wp-block-image"><img src="{UPLOADS}/shared-1024x576.png" alt="{alt}"></figure>'

    mock_translation(english_body=f"{figure('')}<p>Hello world.</p>", translated_body=f"{figure('Ein grünes Rechteck')}<p>Hallo Welt.</p>")

    run = run_sync(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post(content=f"{figure('')}<p>Hello world.</p>"))

    [image] = body_values(translation_of(created_page()), "image")
    assert SpringfieldImage.objects.get(pk=image["image"]).file_hash == file_hash(OTHER)
    assert check_results(run)[("de", "translation body images")]["result"] == "pass"


@responses.activate
def test_an_empty_image_pairs_entry_keeps_the_english_images(tmp_path, blog):
    serve_post_images()
    serve(f"{UPLOADS}/other.png", OTHER)
    other = f'<figure class="wp-block-image"><img src="{UPLOADS}/other.png" alt=""></figure>'
    mock_translation(translated_body=f"{other}<p>Hallo Welt.</p>")

    run = run_sync(tmp_path, sync_data(sync_post(translations=[{**translated_post(), "image_pairs": []}])), export_post())

    [image] = body_values(translation_of(created_page()), "image")
    assert SpringfieldImage.objects.get(pk=image["image"]).file_hash == file_hash(BODY)
    assert check_results(run)[("de", "translation body images")]["result"] == "pass"


@responses.activate
def test_a_translated_image_that_wont_download_stops_the_run(tmp_path, blog):
    serve_post_images()
    responses.add(responses.GET, f"{UPLOADS}/other.png", status=404)
    other = f'<figure class="wp-block-image"><img src="{UPLOADS}/other.png" alt=""></figure>'
    mock_translation(translated_body=f"{other}<p>Hallo Welt.</p>")

    _, error = failing_run(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post())

    assert f"post first-post de: could not download the translated image {UPLOADS}/other.png" in error
    assert not BlogArticlePage.objects.exists()


@responses.activate
def test_a_translation_with_uncertain_text_gets_one_step_to_compare_it(tmp_path, blog):
    serve_post_images()
    image = f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure>'
    english = f"{image}<p>Hello world.</p><p>A second paragraph about Firefox.</p>"
    mock_translation(english_body=english, translated_body=f"{image}<p>Hallo Welt.</p>")

    run = run_sync(tmp_path, sync_data(sync_post(translations=[translated_post()])), export_post(content=english))

    link = f"{WORDPRESS}/de/products/firefox/first-post-de/"
    step = f"- [ ] de: compare the translation with [WordPress]({link}): 1 doubtful text match, listed in `report.csv`"
    assert step in run.text("hand-steps.md")


def make_translation(tmp_path, english_slug="first-post"):
    """A translation that kept the English hero, before WordPress gave it its own."""
    serve_post_images()
    mock_translation(slug=english_slug, hero=HERO)
    untouched_hero = {key: value for key, value in translated_post().items() if key != "hero"}
    post = sync_post(slug=english_slug, translations=[untouched_hero])
    run_sync(tmp_path / "setup", sync_data(post), export_post(slug=english_slug))
    responses.replace(responses.GET, f"{UPLOADS}/de-hero-201.png", body=GERMAN_HERO, content_type="image/png")
    return translation_of(created_page(english_slug))


def hero_fix(**overrides):
    return {"en_slug": "first-post", "locale": "de", "wp_id": 201, "hash": file_hash(GERMAN_HERO), "alt": "Ein gelbes Bild", **overrides}


@responses.activate
def test_fix_translation_heroes_publishes_the_localized_hero_in_one_revision(tmp_path, blog):
    german = make_translation(tmp_path)
    assert german.image.file_hash == file_hash(HERO)
    revisions = german.revisions.count()

    run = run_sync(tmp_path / "first", sync_data(hero_fixes=[hero_fix()]), export=False, fix_translation_heroes=True)
    second = run_sync(tmp_path / "second", sync_data(hero_fixes=[hero_fix()]), export=False, fix_translation_heroes=True)

    german.refresh_from_db()
    assert (german.image.file_hash, german.image_alt) == (file_hash(GERMAN_HERO), "Ein gelbes Bild")
    assert german.revisions.count() == revisions + 1
    assert german.live and not german.has_unpublished_changes
    assert run.actions() == [("first-post", "de", "changed")]
    assert second.rows()[0]["detail"] == "already has the hero"


@responses.activate
def test_fix_translation_heroes_skips_a_translation_with_a_pending_draft(tmp_path, blog):
    german = make_translation(tmp_path)
    german.title = "Draft edit"
    german.save_revision()

    run = run_sync(tmp_path, sync_data(hero_fixes=[hero_fix()]), export=False, fix_translation_heroes=True)

    assert run.rows()[0]["action"] == "skipped"
    assert "publish or revert it, then rerun" in run.rows()[0]["detail"]


# -------------------------------------------------------------------------
# Reruns, failures and redirects
# -------------------------------------------------------------------------


@responses.activate
def test_a_new_author_is_shared_by_posts_and_reused_on_the_rerun(tmp_path, blog):
    serve_post_images()
    serve(f"{UPLOADS}/hero-2.png", HERO)
    data = sync_data(
        sync_post(authors=[{"new": "New Person"}]),
        sync_post(wp_id=102, slug="second-post", authors=[{"new": "New Person"}]),
    )
    posts = (export_post(), export_post(wp_id=102, slug="second-post", hero_url=f"{UPLOADS}/hero-2.png"))
    run_sync(tmp_path, data, *posts)

    rerun = run_sync(tmp_path, data, *posts)

    author = BlogAuthor.objects.get(slug="new-person")
    assert [placement.author for placement in created_page("second-post").article_authors.all()] == [author]
    assert [action for _, _, action in rerun.actions()] == ["skipped", "skipped"]


@responses.activate
def test_a_new_author_renamed_by_an_editor_in_case_only_doesnt_block_the_rerun(tmp_path, blog):
    serve_post_images()
    data = sync_data(sync_post(authors=[{"new": "new person"}]))
    run_sync(tmp_path, data, export_post())
    author = BlogAuthor.objects.get(slug="new-person")
    author.name = "New Person"
    author.save_revision().publish()

    rerun = run_sync(tmp_path, data, export_post())

    assert rerun.actions() == [("first-post", "en-US", "skipped")]


def test_a_new_author_taking_another_authors_slug_stops_the_run(tmp_path, blog):
    publish(BlogAuthor, name="New-Person", slug="new-person", locale=Locale.get_default())

    run, error = failing_run(tmp_path, sync_data(sync_post(authors=[{"new": "New Person"}])), export_post())

    assert "'New Person' would take the slug of 'New-Person'" in error
    assert not BlogArticlePage.objects.exists()


@responses.activate
def test_a_rerun_creates_nothing(tmp_path, blog):
    serve_post_images()
    mock_translation()
    data = sync_data(sync_post(translations=[translated_post()]))
    run = run_sync(tmp_path / "run", data, export_post())
    counts = (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count())

    rerun = run_sync(tmp_path / "rerun", data, export_post())

    assert (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count()) == counts
    assert rerun.actions() == [("first-post", "en-US", "skipped"), ("first-post", "de", "skipped")]
    assert rerun.rows("redirects.csv") == run.rows("redirects.csv")
    assert [row["locale"] for row in rerun.rows("redirects.csv")] == ["en", "de"]


@responses.activate
def test_a_translation_that_failed_is_created_on_the_rerun(tmp_path, blog):
    serve_post_images()
    mock_translation(status=500)
    data = sync_data(sync_post(translations=[translated_post()]))

    run, error = failing_run(tmp_path, data, export_post())
    assert ("first-post", "de", "failed") in run.actions()

    rerun = run_sync(tmp_path, data, export_post())

    assert rerun.actions() == [("first-post", "en-US", "skipped"), ("first-post", "de", "created")]
    assert [(row["locale"], row["old_url"]) for row in rerun.rows("redirects.csv")] == [
        ("en", f"{WORDPRESS}/en/products/firefox/first-post/"),
        ("de", f"{WORDPRESS}/de/products/firefox/first-post-de/"),
    ]


@responses.activate
def test_a_different_page_with_the_slug_is_a_clash_and_left_alone(tmp_path, blog):
    serve_post_images()
    other = BlogArticlePage(title="Another post", slug="first-post", topic=BlogTopic.objects.get(slug="ai"), hero_style="text_only", content=[])
    blog.add_child(instance=other)

    run, error = failing_run(tmp_path, sync_data(sync_post()), export_post())

    assert run.rows()[0]["action"] == "failed"
    assert "a different page has this slug" in run.rows()[0]["detail"]
    assert created_page().title == "Another post"


@responses.activate
def test_redirects_list_every_created_page_on_www_firefox_com_even_from_a_local_site(tmp_path, blog):
    serve_post_images()
    mock_translation()
    mock_translation(language="fr", wp_id=202)
    data = sync_data(sync_post(translations=[translated_post(), translated_post(language="fr", wp_id=202)]))

    run = run_sync(tmp_path, data, export_post())

    english = created_page()
    pages = [english, translation_of(english), translation_of(english, "fr")]
    rows = [(row["wp_id"], row["locale"], row["slug"], row["migrated"], row["old_url"], row["new_url"]) for row in run.rows("redirects.csv")]
    assert rows == [
        ("101", "en", "first-post", "yes", f"{WORDPRESS}/en/products/firefox/first-post/", "https://www.firefox.com/en-US/blog/first-post/"),
        (
            "201",
            "de",
            "first-post-de",
            "yes",
            f"{WORDPRESS}/de/products/firefox/first-post-de/",
            f"https://www.firefox.com{pages[1].get_url_parts()[2]}",
        ),
        (
            "202",
            "fr",
            "first-post-fr",
            "yes",
            f"{WORDPRESS}/fr/products/firefox/first-post-fr/",
            f"https://www.firefox.com{pages[2].get_url_parts()[2]}",
        ),
    ]


# -------------------------------------------------------------------------
# Dry run
# -------------------------------------------------------------------------


def stored_files():
    return {os.path.join(folder, name) for folder, _, names in os.walk(settings.MEDIA_ROOT) for name in names}


@responses.activate
def test_a_dry_run_writes_nothing_and_lists_what_the_real_run_does(tmp_path, blog, settings):
    # Tests running in parallel share the media folder, so this one gets its own.
    settings.MEDIA_ROOT = str(tmp_path / "media")
    serve_post_images()
    serve(PLACEHOLDER["poster_url"], POSTER)
    clip = f"{UPLOADS}/clip.mp4"
    post = sync_post(media=[{"src": clip, "kind": "video", "alt": "A clip"}])
    content = f'<p>Intro.</p><figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><video src="{clip}"></video>'
    data = sync_data(post)
    counts = (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count(), BlogAuthor.objects.count())
    files = stored_files()

    dry = run_sync(tmp_path / "dry", data, export_post(content=content), dry_run=True)

    assert (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count(), BlogAuthor.objects.count()) == counts
    assert stored_files() == files
    assert dry.actions() == [("first-post", "en-US", "would create")]
    assert "images: 2 new, 0 reused" in dry.rows()[0]["detail"]
    assert "Dry run" in dry.text("summary.md")

    real = run_sync(tmp_path, copy.deepcopy(data), export_post(content=content))

    assert [slug for slug, _, _ in real.actions()] == [slug for slug, _, _ in dry.actions()]
    assert dry.text("hand-steps.md").replace("**Dry run: nothing was written.**\n\n", "") == real.text("hand-steps.md")


# -------------------------------------------------------------------------
# The check, in a run and with --check-only
# -------------------------------------------------------------------------


def check_results(run):
    return {(row["locale"], row["check"]): row for row in run.rows("check.csv")}


def publish_change(page, change):
    draft = page.get_latest_revision_as_object()
    change(draft)
    draft.save_revision().publish()


@responses.activate
def test_every_check_passes_for_pages_the_run_built(tmp_path, blog):
    serve_post_images()
    mock_translation()
    post = sync_post(translations=[translated_post()], image_alt=[{"position": 1, "hash": file_hash(BODY), "alt": "Green"}])

    run = run_sync(tmp_path, sync_data(post), export_post())

    results = check_results(run)
    assert {key: row["result"] for key, row in results.items() if row["result"] != "pass"} == {}
    assert ("de", "translation hero") in results
    assert "## first-post" not in run.text("hand-steps.md")


@responses.activate
def test_a_hero_swapped_by_hand_to_the_wrong_file_fails_with_both_hashes(tmp_path, blog):
    serve_post_images()
    run_sync(tmp_path / "first", sync_data(sync_post()), export_post())
    page = created_page()
    publish_change(page, lambda draft: setattr(draft, "image", SpringfieldImage.objects.get(file_hash=file_hash(BODY))))

    run, error = failing_run(tmp_path / "check", sync_data(sync_post()), export_post(), check_only=True)

    assert "1 checks failed" in error
    hero = check_results(run)[("en-US", "hero")]
    assert (hero["result"], hero["expected"], hero["found"]) == ("fail", file_hash(HERO), file_hash(BODY))
    assert (
        "## first-post\n\n"
        "- [ ] The hero isn't the reviewed image: use “Hero” from the image library\n"
        "- [ ] The first image in the body repeats the hero. Remove it if it isn't wanted\n"
    ) in run.text("hand-steps.md")


@responses.activate
def test_an_unpublished_english_page_fails_its_check(tmp_path, blog):
    serve_post_images()
    run_sync(tmp_path / "run", sync_data(sync_post()), export_post())
    created_page().unpublish()

    run, error = failing_run(tmp_path / "check", sync_data(sync_post()), export_post(), check_only=True)

    assert "1 checks failed" in error
    assert check_results(run)[("en-US", "page")]["result"] == "fail"
    assert "- [ ] The page isn't live. Publish it" in run.text("hand-steps.md")


@responses.activate
def test_a_translation_missing_its_body_images_gets_a_step_linking_to_wordpress(tmp_path, blog):
    serve_post_images()
    mock_translation()
    data = sync_data(sync_post(translations=[translated_post()]))
    run_sync(tmp_path / "run", data, export_post())
    publish_change(translation_of(created_page()), lambda draft: setattr(draft, "content", []))

    run, _ = failing_run(tmp_path / "check", data, export_post(), check_only=True)

    step = f"de: The body images don't match [WordPress]({WORDPRESS}/de/?p=201) (1 there, 0 here). Swap them in the editor"
    assert f"- [ ] {step}" in run.text("hand-steps.md")


@responses.activate
def test_a_gif_replaced_by_an_animation_passes_the_body_image_check(tmp_path, blog):
    serve_post_images()
    serve(f"{ASSETS}/gif.jpg", POSTER)
    gif = f"{UPLOADS}/huge.gif"
    content = f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><p><img src="{gif}" alt=""></p>'
    media = [{"src": gif, "kind": "gif", "alt": "A big animation", "webm_url": f"{ASSETS}/gif.webm", "poster_url": f"{ASSETS}/gif.jpg"}]

    run = run_sync(tmp_path, sync_data(sync_post(media=media)), export_post(content=content))

    body = check_results(run)[("en-US", "body images")]
    assert (body["result"], body["found"]) == ("pass", f"{file_hash(BODY)} animation")


@responses.activate
def test_check_only_with_no_media_files_matches_the_run_and_writes_nothing(tmp_path, blog):
    serve_post_images()
    mock_translation()
    data = sync_data(sync_post(translations=[translated_post()]))
    run = run_sync(tmp_path / "run", data, export_post())
    for image in SpringfieldImage.objects.all():
        image.file.delete(save=False)
    counts = (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count())

    check = run_sync(tmp_path / "check", data, export_post(), check_only=True)

    assert check.text("check.csv") == run.text("check.csv")
    assert check.rows() == []
    assert (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count()) == counts


@responses.activate
def test_a_placeholder_is_a_warning_and_a_hand_step_until_it_is_replaced(tmp_path, blog):
    serve_post_images()
    serve(PLACEHOLDER["poster_url"], POSTER)
    clip = f"{UPLOADS}/clip.mp4"
    data = sync_data(sync_post(media=[{"src": clip, "kind": "video", "alt": "A clip"}]))
    run_sync(tmp_path / "run", data, export_post(content=f'<video src="{clip}"></video>'))

    before = run_sync(tmp_path / "before", data, export_post(content=f'<video src="{clip}"></video>'), check_only=True)
    page = created_page()

    def replace(draft):
        draft.content[0].value[0].value["video_url"] = f"{ASSETS}/clip.webm"

    publish_change(page, replace)
    after = run_sync(tmp_path / "after", data, export_post(content=f'<video src="{clip}"></video>'), check_only=True)

    assert check_results(before)[("en-US", "placeholders")]["result"] == "warning"
    assert "Replace the placeholder animation with its webm" in before.text("hand-steps.md")
    assert check_results(after)[("en-US", "placeholders")]["result"] == "pass"


@responses.activate
def test_a_hero_repeated_as_the_first_image_is_a_warning_when_kept(tmp_path, blog):
    serve(f"{UPLOADS}/hero.png", HERO)
    content = f'<figure class="wp-block-image"><img src="{UPLOADS}/hero.png" alt=""></figure><p>Hello world.</p>'

    run = run_sync(tmp_path, sync_data(sync_post()), export_post(content=content))

    assert check_results(run)[("en-US", "hero duplicate")]["result"] == "warning"
    assert body_values(created_page(), "image")[0]["image"] == created_page().image_id
