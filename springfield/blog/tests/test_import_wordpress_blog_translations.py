# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import json
from datetime import date, datetime
from io import BytesIO, StringIO

from django.core.management import call_command
from django.utils.timezone import get_default_timezone, make_aware

import pytest
import responses
from bs4 import BeautifulSoup
from PIL import Image
from responses import matchers
from wagtail.models import Locale, Site
from wagtail.utils.file import hash_filelike

from springfield.blog.management.commands.fix_imported_blog_posts import youtube_thumbnail_url
from springfield.blog.models import BlogArticlePage, BlogIndexPage, BlogTopic, HeroStyle
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import SpringfieldImage

pytestmark = [pytest.mark.django_db]

WORDPRESS = "https://blog.mozilla.org"
UPLOADS = f"{WORDPRESS}/wp-content/uploads/2024/09"
RELEASE_NOTES = "https://www.mozilla.org/en-US/firefox/130.0/releasenotes/"

ENGLISH = [
    "Firefox 130 is out today, with features that keep you in control.",
    f'Read the <a href="{RELEASE_NOTES}">release notes</a> for everything new.',
    "Join the conversation on our community forum, where volunteers answer questions every day.",
    "This sentence stays in English on WordPress too.",
]
GERMAN = [
    "Firefox 130 ist da, mit Funktionen, die Ihnen die Kontrolle geben.",
    'Lesen Sie die <a href="https://www.mozilla.org/de/firefox/130.0/releasenotes/">Versionshinweise</a> für alles Neue.',
    # The community forum paragraph has no German version.
    "This sentence stays in English on WordPress too.",
]


def png(colour):
    buffer = BytesIO()
    Image.new("RGB", (40, 20), colour).save(buffer, "PNG")
    return buffer.getvalue()


def text_block(paragraphs):
    html = "".join(f'<p data-block-key="k{number}">{paragraph}</p>' for number, paragraph in enumerate(paragraphs))
    return {"type": "text", "value": html, "id": "00000000-0000-0000-0000-000000000001"}


def image_block(image):
    return {
        "type": "media",
        "value": [{"type": "image", "value": {"image": image.pk, "settings": {}}, "id": "00000000-0000-0000-0000-000000000003"}],
        "id": "00000000-0000-0000-0000-000000000002",
    }


def wordpress_html(paragraphs, image_url=None, alt=""):
    html = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
    if image_url:
        html += f'<figure class="wp-block-image"><img src="{image_url}" alt="{alt}"></figure>'
    return html


def wordpress_post(language, slug, content, title="Firefox 130", date="2024-09-17T10:30:00", yoast=None):
    return {
        "id": 1,
        "slug": slug,
        "date": date,
        "link": f"{WORDPRESS}/{language}/products/firefox/{slug}/",
        "title": {"rendered": title},
        "excerpt": {"rendered": ""},
        "content": {"rendered": content},
        "yoast_head_json": yoast or {},
    }


def mock_rest(language, post, status=200):
    responses.add(
        responses.GET,
        f"{WORDPRESS}/{language}/wp-json/wp/v2/posts",
        json=[post] if status == 200 else {"code": "error"},
        status=status,
        match=[matchers.query_param_matcher({"slug": post["slug"]}, strict_match=False)],
    )


def mock_wordpress(slug, english=ENGLISH, german=GERMAN, english_image=None, german_image=None, alt="", hreflang=("de",), **german_fields):
    """Publish `slug` on the fake WordPress in English and German, with the English post's page
    linking to the translations it names in `hreflang`."""
    english_post = wordpress_post("en", slug, wordpress_html(english, english_image))
    german_post = wordpress_post("de", f"{slug}-de", wordpress_html(german, german_image, alt), **german_fields)
    mock_rest("en", english_post)
    mock_rest("de", german_post)
    links = "".join(
        f'<link rel="alternate" hreflang="{language}" href="{WORDPRESS}/{language}/products/firefox/{slug}-{language}/">' for language in hreflang
    )
    responses.add(responses.GET, english_post["link"], body=f"<html><head>{links}</head><body></body></html>")
    return english_post, german_post


@pytest.fixture
def de_locale(minimal_site):
    return Locale.objects.get_or_create(language_code="de")[0]


@pytest.fixture
def blog_index(minimal_site, de_locale):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = BlogIndexPage(title="Blog", slug="test-unit-blog", locale=Locale.get_default())
    root_page.add_child(instance=index_page)
    index_page.save_revision().publish()
    return index_page


@pytest.fixture
def blog_topic(blog_index):
    return BlogTopic.objects.create(name="Firefox", slug="test-unit-firefox", locale=blog_index.locale)


@pytest.fixture
def make_article(blog_index, blog_topic):
    def make_article(slug="firefox-130", content=None, publish=True):
        article = BlogArticlePage(
            title="Firefox 130",
            slug=slug,
            seo_title="Firefox 130 | The Mozilla Blog",
            search_description="Everything new in Firefox 130.",
            topic=blog_topic,
            hero_style=HeroStyle.TEXT_ONLY,
            content=content or [text_block(ENGLISH)],
            live=publish,
        )
        blog_index.add_child(instance=article)
        if publish:
            article.save_revision().publish()
        return article

    return make_article


@pytest.fixture
def placeholder_image(minimal_site):
    return get_placeholder_images().image


def run(tmp_path, *slugs, **options):
    stdout, stderr = StringIO(), StringIO()
    report = tmp_path / "report.csv"
    args = [arg for slug in slugs for arg in ("--slug", slug)]
    call_command("import_wordpress_blog_translations", *args, "--locale", "de", report_out=str(report), stdout=stdout, stderr=stderr, **options)
    with open(report, newline="") as report_file:
        rows = list(csv.DictReader(report_file))
    return stdout.getvalue(), stderr.getvalue(), rows


def german_page(english_page):
    return BlogArticlePage.objects.get(locale__language_code="de", translation_key=english_page.translation_key)


def german_text(english_page):
    return german_page(english_page).content.raw_data[0]["value"]


def plain(html):
    return BeautifulSoup(html, "html.parser").get_text()


def links(html):
    return [(link.get_text(), link["href"]) for link in BeautifulSoup(html, "html.parser").find_all("a")]


def content_image(page):
    media = next(block for block in page.content.raw_data if block["type"] == "media")
    return SpringfieldImage.objects.get(pk=media["value"][0]["value"]["image"])


# -------------------------------------------------------------------------
# Creating a translation
# -------------------------------------------------------------------------


@responses.activate
def test_creates_a_published_german_page_linked_to_the_english_one(tmp_path, make_article):
    english = make_article()
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    page = german_page(english)
    assert page.live
    assert not page.has_unpublished_changes
    assert page.alias_of is None
    assert rows[0]["action"] == "created"
    assert rows[0]["page_id"] == str(page.pk)
    assert rows[0]["wordpress_url"] == f"{WORDPRESS}/de/products/firefox/firefox-130-de/"


@responses.activate
def test_creates_the_german_blog_index_with_nothing_curated(tmp_path, blog_index, make_article):
    english = make_article()
    mock_wordpress("firefox-130")

    run(tmp_path, "firefox-130")

    index = BlogIndexPage.objects.get(locale__language_code="de", translation_key=blog_index.translation_key)
    assert index.live
    assert list(index.featured_articles) == []
    assert list(index.article_sections) == []
    assert german_page(english).get_parent().pk == index.pk


@responses.activate
def test_title_tag_and_meta_description_come_from_wordpress_and_yoast(tmp_path, make_article):
    english = make_article()
    mock_wordpress(
        "firefox-130",
        title="Firefox 130 ist da &#8211; jetzt",
        yoast={"title": "Firefox 130 | Der Mozilla-Blog", "description": "Alles Neue in Firefox 130."},
    )

    run(tmp_path, "firefox-130")

    page = german_page(english)
    assert page.title == "Firefox 130 ist da – jetzt"
    assert page.seo_title == "Firefox 130 | Der Mozilla-Blog"
    assert page.search_description == "Alles Neue in Firefox 130."


@responses.activate
def test_body_paragraphs_are_translated_and_links_keep_the_english_href(tmp_path, make_article):
    english = make_article()
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    text = german_text(english)
    assert "Firefox 130 ist da, mit Funktionen, die Ihnen die Kontrolle geben." in text
    assert "Lesen Sie die Versionshinweise für alles Neue." in plain(text)
    assert links(text) == [("Versionshinweise", RELEASE_NOTES)]
    assert "Firefox 130 is out today" not in text
    assert rows[0]["translated"] == "5"  # title, Title tag, Meta description and two paragraphs


@responses.activate
def test_first_published_date_is_the_wordpress_date(tmp_path, make_article):
    english = make_article()
    mock_wordpress("firefox-130", date="2024-09-17T10:30:00")

    _, _, rows = run(tmp_path, "firefox-130")

    # WordPress dates are wall-clock time in the blog's time zone, as the importer reads them.
    assert german_page(english).first_published_at == make_aware(datetime(2024, 9, 17, 10, 30), get_default_timezone())
    assert rows[0]["wordpress_date"] == "2024-09-17"


@responses.activate
def test_topic_is_a_published_german_translation_of_the_english_topic(tmp_path, make_article, blog_topic):
    english = make_article()
    mock_wordpress("firefox-130")

    run(tmp_path, "firefox-130")

    topic = BlogTopic.objects.get(locale__language_code="de", translation_key=blog_topic.translation_key)
    assert topic.live
    assert german_page(english).topic_id == topic.pk


@responses.activate
def test_english_paragraph_with_no_wordpress_counterpart_is_removed(tmp_path, make_article):
    english = make_article()
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    assert "community forum" not in german_text(english)
    assert rows[0]["removed"] == "1"


@responses.activate
def test_text_that_is_english_on_wordpress_stays_english(tmp_path, make_article):
    english = make_article()
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    assert "This sentence stays in English on WordPress too." in german_text(english)
    assert rows[0]["kept_english"] == "1"


@responses.activate
def test_links_the_english_paragraph_lacks_are_dropped_and_the_page_still_publishes(tmp_path, make_article):
    english = make_article()
    german = list(GERMAN)
    german[1] = (
        'Lesen Sie die <a href="https://www.mozilla.org/de/firefox/130.0/releasenotes/">Versionshinweise</a> '
        'und den <a href="https://support.mozilla.org/de/">Support</a> für alles Neue.'
    )
    mock_wordpress("firefox-130", german=german)

    _, _, rows = run(tmp_path, "firefox-130")

    text = german_text(english)
    assert "Lesen Sie die Versionshinweise und den Support für alles Neue." in plain(text)
    assert links(text) == [("Versionshinweise", RELEASE_NOTES)]
    assert german_page(english).live
    assert rows[0]["action"] == "created"
    assert "(extra link dropped)" in rows[0]["detail"]


@responses.activate
def test_dry_run_writes_nothing_but_reports_would_create(tmp_path, make_article, placeholder_image):
    make_article(content=[text_block(ENGLISH), image_block(placeholder_image)])
    mock_wordpress(
        "firefox-130",
        english_image=f"{UPLOADS}/placeholder_image-1024x576.png",
        german_image=f"{UPLOADS}/placeholder_image-de-1024x576.png",
    )
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image-de.png", body=png((10, 200, 10)), content_type="image/png")
    images_before = SpringfieldImage.objects.count()

    stdout, _, rows = run(tmp_path, "firefox-130", dry_run=True)

    assert not BlogArticlePage.objects.filter(locale__language_code="de").exists()
    assert not BlogIndexPage.objects.filter(locale__language_code="de").exists()
    assert not BlogTopic.objects.filter(locale__language_code="de").exists()
    assert SpringfieldImage.objects.count() == images_before
    assert rows[0]["action"] == "would create"
    assert rows[0]["images_swapped"] == "1"
    assert stdout.startswith("[dry-run] ")


# -------------------------------------------------------------------------
# Skipping
# -------------------------------------------------------------------------


@responses.activate
def test_skips_when_a_german_page_already_exists(tmp_path, make_article):
    english = make_article()
    mock_wordpress("firefox-130")
    run(tmp_path, "firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"] == "a de page already exists"
    assert rows[0]["page_id"] == str(german_page(english).pk)
    assert BlogArticlePage.objects.filter(locale__language_code="de").count() == 1


@responses.activate
def test_skips_an_unpublished_english_page(tmp_path, make_article):
    english = make_article(publish=False)
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"] == "the English page isn't published, or has unpublished changes: publish it first"
    assert not BlogArticlePage.objects.get(pk=english.pk).live
    assert not BlogArticlePage.objects.filter(locale__language_code="de").exists()


@responses.activate
def test_skips_an_english_page_with_unpublished_changes_and_leaves_them_unpublished(tmp_path, make_article):
    english = make_article()
    english.title = "Firefox 130, edited"
    english.save_revision()
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    english.refresh_from_db()
    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"] == "the English page isn't published, or has unpublished changes: publish it first"
    assert english.has_unpublished_changes
    assert english.title == "Firefox 130"
    assert not BlogArticlePage.objects.filter(locale__language_code="de").exists()


@responses.activate
def test_skips_when_wordpress_has_no_hreflang_for_the_locale(tmp_path, make_article):
    make_article()
    mock_wordpress("firefox-130", hreflang=("fr",))

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"] == "no de translation on WordPress"


@responses.activate
def test_skips_a_translation_on_the_skip_list(tmp_path, make_article):
    make_article()
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"_skip": ["firefox-130-de"]}))

    _, _, rows = run(tmp_path, "firefox-130", overrides=str(overrides))

    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"] == "on the skip list"
    assert len(responses.calls) == 0


@responses.activate
def test_skips_a_translation_published_before_since(tmp_path, make_article):
    make_article()
    mock_wordpress("firefox-130", date="2024-09-17T10:30:00")

    _, _, rows = run(tmp_path, "firefox-130", since=date(2024, 10, 1))

    assert rows[0]["action"] == "skipped"
    assert rows[0]["detail"] == "translated before 2024-10-01"
    assert not BlogArticlePage.objects.filter(locale__language_code="de").exists()


# -------------------------------------------------------------------------
# Images
# -------------------------------------------------------------------------


@responses.activate
def test_localized_image_is_downloaded_described_and_swapped_in(tmp_path, make_article, placeholder_image):
    english = make_article(content=[text_block(ENGLISH), image_block(placeholder_image)])
    mock_wordpress(
        "firefox-130",
        english_image=f"{UPLOADS}/placeholder_image-1024x576.png",
        german_image=f"{UPLOADS}/placeholder_image-de-1024x576.png",
        alt="Die Einstellungen auf Deutsch",
    )
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image-de.png", body=png((10, 200, 10)), content_type="image/png")

    _, _, rows = run(tmp_path, "firefox-130")

    image = content_image(german_page(english))
    assert image.pk != placeholder_image.pk
    assert image.description == "Die Einstellungen auf Deutsch"
    assert content_image(BlogArticlePage.objects.get(pk=english.pk)).pk == placeholder_image.pk
    assert rows[0]["images_swapped"] == "1"
    assert rows[0]["images_missing"] == "0"


@responses.activate
def test_localized_image_that_404s_is_reported_and_the_english_image_kept(tmp_path, make_article, placeholder_image):
    english = make_article(content=[text_block(ENGLISH), image_block(placeholder_image)])
    mock_wordpress(
        "firefox-130",
        english_image=f"{UPLOADS}/placeholder_image-1024x576.png",
        german_image=f"{UPLOADS}/placeholder_image-de-1024x576.png",
    )
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image-de.png", status=404)
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image-de-1024x576.png", status=404)

    _, _, rows = run(tmp_path, "firefox-130")

    assert content_image(german_page(english)).pk == placeholder_image.pk
    assert rows[0]["action"] == "created"
    assert rows[0]["images_missing"] == "1"
    assert f"image not downloadable: {UPLOADS}/placeholder_image-de-1024x576.png" in rows[0]["detail"]


@responses.activate
def test_a_library_file_is_reused_only_with_the_same_alt_text(tmp_path, make_article, placeholder_image):
    with placeholder_image.file.open("rb") as image_file:
        content = image_file.read()
    placeholder_image.description = "The settings page in English"
    placeholder_image.file_hash = hash_filelike(BytesIO(content))
    placeholder_image.save()
    english = make_article(content=[text_block(ENGLISH), image_block(placeholder_image)])
    mock_wordpress(
        "firefox-130",
        english_image=f"{UPLOADS}/placeholder_image-1024x576.png",
        german_image=f"{UPLOADS}/placeholder_image-de.png",
        alt="Die Einstellungen auf Deutsch",
    )
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image-de.png", body=content, content_type="image/png")

    run(tmp_path, "firefox-130")

    image = content_image(german_page(english))
    assert image.pk != placeholder_image.pk
    assert image.description == "Die Einstellungen auf Deutsch"


# -------------------------------------------------------------------------
# Videos
# -------------------------------------------------------------------------


def youtube_embed(video_id):
    return f'<figure class="wp-block-embed"><div class="wp-block-embed__wrapper"><iframe src="https://www.youtube.com/embed/{video_id}"></iframe></div></figure>'


@responses.activate
def test_localized_youtube_video_gets_the_translated_video_and_its_thumbnail_as_poster(tmp_path, make_article, placeholder_image):
    video = {
        "type": "media",
        "value": [
            {
                "type": "video",
                "value": {
                    "video_url": "https://www.youtube.com/watch?v=AAAAAAAAAAA",
                    "alt": "A tour of Firefox 130",
                    "poster": placeholder_image.pk,
                    "aspect_ratio": "",
                },
                "id": "00000000-0000-0000-0000-000000000005",
            }
        ],
        "id": "00000000-0000-0000-0000-000000000004",
    }
    english = make_article(content=[text_block(ENGLISH), video])
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH) + youtube_embed("AAAAAAAAAAA"))
    german_post = wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN) + youtube_embed("BBBBBBBBBBB"))
    mock_rest("en", english_post)
    mock_rest("de", german_post)
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )
    responses.add(responses.GET, youtube_thumbnail_url("BBBBBBBBBBB", "maxresdefault"), body=png((200, 10, 10)), content_type="image/jpeg")

    _, _, rows = run(tmp_path, "firefox-130")

    german_video = next(block for block in german_page(english).content.raw_data if block["type"] == "media")["value"][0]["value"]
    assert german_video["video_url"] == "https://www.youtube.com/watch?v=BBBBBBBBBBB"
    assert german_video["poster"] != placeholder_image.pk
    assert SpringfieldImage.objects.get(pk=german_video["poster"]).title == "BBBBBBBBBBB-maxresdefault"
    assert rows[0]["videos_swapped"] == "1"
    # The video's alt text has no WordPress counterpart and can't be removed, so it is reported.
    assert "left in English, not on WordPress: a tour of firefox 130" in rows[0]["detail"]


# -------------------------------------------------------------------------
# Matching
# -------------------------------------------------------------------------


@responses.activate
def test_a_near_match_never_reuses_a_paragraph_already_placed(tmp_path, make_article):
    lookalike = ENGLISH[0].replace("today", "this week")
    english = make_article(content=[text_block([ENGLISH[0], lookalike])])
    mock_wordpress("firefox-130", english=[ENGLISH[0]], german=[GERMAN[0]])

    run(tmp_path, "firefox-130")

    assert plain(german_text(english)).count(GERMAN[0]) == 1


@responses.activate
def test_skips_when_the_english_post_redirects(tmp_path, make_article):
    make_article()
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH))
    mock_rest("en", english_post)
    responses.add(responses.GET, english_post["link"], status=302, headers={"Location": "https://www.firefox.com/en-US/blog/firefox-130/"})

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "skipped"
    assert "redirects" in rows[0]["detail"]


# -------------------------------------------------------------------------
# Failures
# -------------------------------------------------------------------------


@responses.activate
def test_a_failed_translation_is_reported_and_the_run_continues(tmp_path, make_article):
    make_article(slug="broken")
    working = make_article(slug="firefox-130")
    mock_rest("en", wordpress_post("en", "broken", ""), status=500)
    mock_wordpress("firefox-130")

    _, stderr, rows = run(tmp_path, "broken", "firefox-130")

    by_slug = {row["slug"]: row for row in rows}
    assert by_slug["broken"]["action"] == "failed"
    assert by_slug["broken"]["detail"].startswith("HTTPError: 500")
    assert "failed: broken de" in stderr
    assert by_slug["firefox-130"]["action"] == "created"
    assert german_page(working).live
