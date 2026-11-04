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
    call_command("sync_wordpress_blog_posts", str(sync_path), out=str(out), stdout=stdout, stderr=stderr, **options)
    return Run(out, stdout.getvalue(), stderr.getvalue())


def failing_run(tmp_path, data, *posts, **options):
    with pytest.raises(CommandError) as raised:
        run_sync(tmp_path, data, *posts, **options)
    return Run(tmp_path / "out", "", ""), str(raised.value)


def serve_post_images():
    serve(f"{UPLOADS}/hero.png", HERO)
    serve(f"{UPLOADS}/body.png", BODY)


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
    assert f"`first-post`: block 2, after the heading “Listen” is a placeholder Animation. Make the webm from {clip}" in run.text("hand-steps.md")


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


def mock_translation(slug="first-post", language="de", wp_id=201, status=200, hero=GERMAN_HERO):
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
    for post, content in ((english, "<p>Hello world.</p>"), (translated, "<p>Hallo Welt.</p>")):
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
    mock_featured_image(language, wp_id, content=hero)
    return translated


def mock_featured_image(language, wp_id, content=GERMAN_HERO):
    responses.add(responses.GET, f"{WORDPRESS}/{language}/wp-json/wp/v2/posts/{wp_id}", json={"featured_media": 77})
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


def make_translation(tmp_path, english_slug="first-post"):
    serve_post_images()
    mock_translation(slug=english_slug)
    untouched_hero = {key: value for key, value in translated_post().items() if key != "hero"}
    post = sync_post(slug=english_slug, translations=[untouched_hero])
    run_sync(tmp_path / "setup", sync_data(post), export_post(slug=english_slug))
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
def test_a_rerun_creates_nothing(tmp_path, blog):
    serve_post_images()
    mock_translation()
    data = sync_data(sync_post(translations=[translated_post()]))
    run_sync(tmp_path, data, export_post())
    counts = (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count())

    rerun = run_sync(tmp_path, data, export_post())

    assert (Page.objects.count(), SpringfieldImage.objects.count(), Revision.objects.count()) == counts
    assert rerun.actions() == [("first-post", "en-US", "skipped"), ("first-post", "de", "skipped")]
    assert rerun.rows("redirects.csv") == []


@responses.activate
def test_a_translation_that_failed_is_created_on_the_rerun(tmp_path, blog):
    serve_post_images()
    mock_translation(status=500)
    data = sync_data(sync_post(translations=[translated_post()]))

    run, error = failing_run(tmp_path, data, export_post())
    assert ("first-post", "de", "failed") in run.actions()

    rerun = run_sync(tmp_path, data, export_post())

    assert rerun.actions() == [("first-post", "en-US", "skipped"), ("first-post", "de", "created")]


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
def test_a_dry_run_writes_nothing_and_lists_what_the_real_run_does(tmp_path, blog):
    serve_post_images()
    serve(PLACEHOLDER["poster_url"], POSTER)
    clip = f"{UPLOADS}/clip.mp4"
    post = sync_post(media=[{"src": clip, "kind": "video", "alt": "A clip"}])
    content = f'<figure class="wp-block-image"><img src="{UPLOADS}/body.png" alt=""></figure><video src="{clip}"></video>'
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
