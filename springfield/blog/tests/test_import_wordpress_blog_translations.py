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

from springfield.blog.management.commands import import_wordpress_blog_translations
from springfield.blog.management.commands.fix_imported_blog_posts import youtube_thumbnail_url
from springfield.blog.models import BlogArticlePage, BlogIndexPage, BlogTopic, HeroStyle
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import PretranslatedPhrase, SpringfieldImage

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


def image_block(image, number=0):
    return {
        "type": "media",
        "value": [{"type": "image", "value": {"image": image.pk, "settings": {}}, "id": f"00000000-0000-0000-0000-00000000{number}003"}],
        "id": f"00000000-0000-0000-0000-00000000{number}002",
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
    def make_article(
        slug="firefox-130",
        content=None,
        publish=True,
        seo_title="Firefox 130 | The Mozilla Blog",
        search_description="Everything new in Firefox 130.",
        description="",
    ):
        article = BlogArticlePage(
            title="Firefox 130",
            slug=slug,
            seo_title=seo_title,
            search_description=search_description,
            description=description,
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


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(import_wordpress_blog_translations.time, "sleep", lambda seconds: None)


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


def content_images(page):
    return [SpringfieldImage.objects.get(pk=block["value"][0]["value"]["image"]) for block in page.content.raw_data if block["type"] == "media"]


def content_image(page):
    return content_images(page)[0]


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
def test_title_tag_and_meta_description_are_set_when_the_english_page_leaves_them_blank(tmp_path, make_article):
    # The importer leaves both blank, and wagtail-localize has no segment for a blank field.
    english = make_article(seo_title="", search_description="")
    mock_wordpress("firefox-130", yoast={"title": "Firefox 130 | Der Mozilla-Blog", "description": "Alles Neue in Firefox 130."})

    _, _, rows = run(tmp_path, "firefox-130")

    page = german_page(english)
    assert page.seo_title == "Firefox 130 | Der Mozilla-Blog"
    assert page.search_description == "Alles Neue in Firefox 130."
    assert rows[0]["translated"] == "5"


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
def test_a_description_repeating_a_paragraph_does_not_take_the_paragraph_translation(tmp_path, make_article):
    english = make_article(description=f"<p>{ENGLISH[0]}</p>")
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    page = german_page(english)
    assert GERMAN[0] in page.content.raw_data[0]["value"]
    assert GERMAN[0] in page.description
    assert rows[0]["removed"] == "1"


@responses.activate
def test_an_english_only_quote_is_removed(tmp_path, make_article):
    quote = "<blockquote>Only in English, said nobody.</blockquote>"
    english = make_article(content=[{"type": "text", "value": text_block(ENGLISH)["value"] + quote, "id": "00000000-0000-0000-0000-000000000001"}])
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH) + quote)
    mock_rest("en", english_post)
    mock_rest("de", wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN)))
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )

    _, _, rows = run(tmp_path, "firefox-130")

    assert "blockquote" not in german_text(english)
    assert rows[0]["removed"] == "2"


@responses.activate
def test_a_link_between_imported_posts_keeps_its_local_href(tmp_path, make_article):
    english = list(ENGLISH)
    english[1] = 'Read <a href="https://blog.mozilla.org/en/products/firefox/other-post/">our other post</a> for everything new.'
    page_english = list(english)
    page_english[1] = 'Read <a href="/en-US/blog/other-post/">our other post</a> for everything new.'
    page = make_article(content=[text_block(page_english)])
    german = list(GERMAN)
    german[1] = (
        'Lesen Sie <a href="https://blog.mozilla.org/de/products/firefox/other-post/">unseren anderen Beitrag</a> '
        'und <a href="https://support.mozilla.org/de/">die Hilfe</a> für alles Neue.'
    )
    mock_wordpress("firefox-130", english=english, german=german)

    _, _, rows = run(tmp_path, "firefox-130")

    assert links(german_text(page)) == [("unseren anderen Beitrag", "/en-US/blog/other-post/")]
    assert "paired by position" not in rows[0]["detail"]


@responses.activate
def test_a_translation_reading_like_another_english_paragraph_does_not_break_removal(tmp_path, make_article):
    english = make_article(content=[text_block(["Get Firefox", "Firefox", ENGLISH[2]])])
    mock_wordpress("firefox-130", english=["Get Firefox", "Firefox", ENGLISH[2]], german=["Firefox", "Firefox"])

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "created", rows[0]["detail"]
    assert plain(german_text(english)).count("Firefox") == 2
    assert rows[0]["removed"] == "1"


@responses.activate
def test_a_list_with_no_translated_items_is_removed_whole(tmp_path, make_article):
    list_html = "<ul><li>Only in English, first point.</li><li>Only in English, second point.</li></ul>"
    english = make_article(
        content=[{"type": "text", "value": text_block(ENGLISH)["value"] + list_html, "id": "00000000-0000-0000-0000-000000000001"}]
    )
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH) + list_html)
    mock_rest("en", english_post)
    mock_rest("de", wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN)))
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )

    _, _, rows = run(tmp_path, "firefox-130")

    assert "<ul>" not in german_text(english)
    assert rows[0]["removed"] == "3"


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
def test_a_translated_link_gets_the_english_link_to_the_same_target_not_the_one_in_its_position(tmp_path, make_article):
    support = "https://support.mozilla.org/en-US/products/firefox"
    english = list(ENGLISH)
    english[1] = f'Read the <a href="{RELEASE_NOTES}">release notes</a> or ask <a href="{support}">Support</a> for everything new.'
    page = make_article(content=[text_block(english)])
    german = list(GERMAN)
    german[1] = 'Fragen Sie den <a href="https://support.mozilla.org/de/products/firefox">Support</a> nach allem Neuen.'
    mock_wordpress("firefox-130", english=english, german=german)

    _, _, rows = run(tmp_path, "firefox-130")

    assert links(german_text(page)) == [("Support", support)]
    assert "link" not in rows[0]["detail"]


@responses.activate
def test_repeated_english_paragraphs_each_get_their_own_translation(tmp_path, make_article):
    features = "https://www.mozilla.org/en-US/firefox/features/"
    passwords = "https://support.mozilla.org/en-US/kb/passwords"
    english = [f'<a href="{features}">Learn more</a>', ENGLISH[0], f'<a href="{passwords}">Learn more</a>']
    german = [
        '<a href="https://www.mozilla.org/de/firefox/features/">Mehr erfahren</a>',
        GERMAN[0],
        '<a href="https://support.mozilla.org/de/kb/passwords">Mehr erfahren</a>',
    ]
    page = make_article(content=[text_block(english)])
    mock_wordpress("firefox-130", english=english, german=german)

    _, _, rows = run(tmp_path, "firefox-130")

    assert links(german_text(page)) == [("Mehr erfahren", features), ("Mehr erfahren", passwords)]
    assert rows[0]["removed"] == "0"


@responses.activate
def test_inline_tags_with_attributes_in_the_translation_do_not_fail_the_page(tmp_path, make_article):
    german = list(GERMAN)
    german[0] = 'Firefox 130 ist da, mit <strong class="has-inline-color">Funktionen</strong>, die Ihnen die Kontrolle geben.'
    english = make_article()
    mock_wordpress("firefox-130", german=german)

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "created"
    assert "<strong>Funktionen</strong>" in german_text(english)


@responses.activate
def test_a_null_correction_removes_a_short_paragraph_the_heuristic_would_keep(tmp_path, make_article):
    english = make_article(content=[text_block([*ENGLISH, "Learn more"])])
    mock_wordpress("firefox-130", english=[*ENGLISH, "Learn more"])
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"firefox-130-de": [{"en": "Learn more", "tr": None}]}))

    _, _, rows = run(tmp_path, "firefox-130", overrides=str(overrides))

    assert "Learn more" not in german_text(english)
    assert rows[0]["removed"] == "2"


@responses.activate
def test_a_null_correction_removes_only_the_occurrence_it_names(tmp_path, make_article):
    english = make_article(content=[text_block(["Learn more", ENGLISH[0], "Learn more"])])
    mock_wordpress("firefox-130", english=["Learn more", ENGLISH[0], "Learn more"], german=[GERMAN[0]])
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"firefox-130-de": [{"en": "Learn more", "tr": None}]}))

    _, _, rows = run(tmp_path, "firefox-130", overrides=str(overrides))

    text = german_text(english)
    assert plain(text).count("Learn more") == 1
    assert plain(text).index(GERMAN[0]) < plain(text).index("Learn more")
    assert rows[0]["removed"] == "1"
    assert rows[0]["kept_english"] == "1"


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


@responses.activate
def test_a_block_referencing_an_untranslated_snippet_keeps_the_english_snippet(tmp_path, make_article):
    phrase = PretranslatedPhrase.objects.create(label="Learn more", locale=Locale.get_default(), live=True)
    link = {"link_to": "custom_url", "custom_url": "https://example.com/", "relative_url": "", "anchor": "", "phone": ""}
    button = {
        "type": "button",
        "value": {"pretranslated_label": phrase.pk, "custom_label": "", "link": link, "settings": {"analytics_id": ""}},
        "id": "b1",
    }
    buttons = {"type": "buttons", "value": {"buttons": [button]}, "id": "b2"}
    card = {"type": "card", "value": {"content": [buttons]}, "id": "b3"}
    cards_list = {"type": "cards_list", "value": {"cards": [card]}, "id": "00000000-0000-0000-0000-000000000006"}
    english = make_article(content=[text_block(ENGLISH), cards_list])
    mock_wordpress("firefox-130")

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "created", rows[0]["detail"]
    german_button = german_page(english).content[1].value["cards"][0].value["content"][0].value["buttons"][0].value
    assert german_button["pretranslated_label"].pk == phrase.pk


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


@responses.activate
def test_a_repeated_image_is_swapped_at_the_occurrence_that_changed(tmp_path, make_article, placeholder_image):
    english = make_article(content=[text_block(ENGLISH), image_block(placeholder_image), image_block(placeholder_image, number=1)])
    figure = f'<figure class="wp-block-image"><img src="{UPLOADS}/placeholder_image.png" alt=""></figure>'
    german_figure = f'<figure class="wp-block-image"><img src="{UPLOADS}/placeholder_image-de.png" alt=""></figure>'
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH) + figure + figure)
    mock_rest("en", english_post)
    mock_rest("de", wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN) + figure + german_figure))
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image-de.png", body=png((10, 200, 10)), content_type="image/png")

    _, _, rows = run(tmp_path, "firefox-130")

    first, second = content_images(german_page(english))
    assert first.pk == placeholder_image.pk
    assert second.pk != placeholder_image.pk
    assert rows[0]["images_swapped"] == "1"


@responses.activate
def test_a_localized_image_with_no_image_block_on_the_page_is_reported(tmp_path, make_article):
    make_article()
    mock_wordpress(
        "firefox-130",
        english_image=f"{UPLOADS}/placeholder_image-1024x576.png",
        german_image=f"{UPLOADS}/placeholder_image-de-1024x576.png",
    )

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "created"
    assert rows[0]["images_swapped"] == "0"
    assert rows[0]["images_missing"] == "1"
    assert f"image not swapped in, no image block for it on the page: {UPLOADS}/placeholder_image-de-1024x576.png" in rows[0]["detail"]


@responses.activate
def test_the_same_image_with_translated_alt_text_gets_its_own_described_copy(tmp_path, make_article, placeholder_image):
    with placeholder_image.file.open("rb") as image_file:
        content = image_file.read()
    placeholder_image.description = "The settings page in English"
    placeholder_image.file_hash = hash_filelike(BytesIO(content))
    placeholder_image.save()
    english = make_article(content=[text_block(ENGLISH), image_block(placeholder_image)])
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH, f"{UPLOADS}/placeholder_image.png", "The settings page in English"))
    mock_rest("en", english_post)
    mock_rest(
        "de", wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN, f"{UPLOADS}/placeholder_image.png", "Die Einstellungen auf Deutsch"))
    )
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )
    responses.add(responses.GET, f"{UPLOADS}/placeholder_image.png", body=content, content_type="image/png")

    _, _, rows = run(tmp_path, "firefox-130")

    image = content_image(german_page(english))
    assert image.pk != placeholder_image.pk
    assert image.description == "Die Einstellungen auf Deutsch"
    assert image.file_hash == placeholder_image.file_hash
    assert rows[0]["images_swapped"] == "1"


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
    assert rows[0]["videos_missing"] == "0"
    # The video's alt text has no WordPress counterpart and can't be removed, so it is reported.
    assert "left in English, not on WordPress: a tour of firefox 130" in rows[0]["detail"]


@responses.activate
def test_translated_videos_that_do_not_pair_with_an_english_one_are_reported_missing(tmp_path, make_article):
    make_article()
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH) + youtube_embed("AAAAAAAAAAA"))
    german_post = wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN) + youtube_embed("BBBBBBBBBBB") + youtube_embed("CCCCCCCCCCC"))
    mock_rest("en", english_post)
    mock_rest("de", german_post)
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["videos_swapped"] == "0"
    assert rows[0]["videos_missing"] == "2"
    assert "video not swapped in: https://www.youtube.com/watch?v=BBBBBBBBBBB" in rows[0]["detail"]


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
def test_rate_limited_and_server_error_responses_are_retried(tmp_path, make_article):
    english = make_article()
    english_post = wordpress_post("en", "firefox-130", wordpress_html(ENGLISH))
    responses.add(responses.GET, f"{WORDPRESS}/en/wp-json/wp/v2/posts", status=429, headers={"Retry-After": "1"})
    responses.add(responses.GET, f"{WORDPRESS}/en/wp-json/wp/v2/posts", status=503)
    mock_rest("en", english_post)
    mock_rest("de", wordpress_post("de", "firefox-130-de", wordpress_html(GERMAN)))
    responses.add(
        responses.GET, english_post["link"], body=f'<link rel="alternate" hreflang="de" href="{WORDPRESS}/de/products/firefox/firefox-130-de/">'
    )

    _, _, rows = run(tmp_path, "firefox-130")

    assert rows[0]["action"] == "created"
    assert german_page(english).live


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
