# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Brings the German and French translations of imported blog posts over from blog.mozilla.org.

For each English blog post, it finds the post's WPML translation from the post's public page
(its hreflang links) and reads it from the WordPress REST API. It then creates the translated
page as a copy of the published English page in the target language, linked to the English page
as its translation but not synced with it, and fills it with the WordPress text, so the page
shows what blog.mozilla.org shows:

- each paragraph gets the translated paragraph it lines up with (see
  springfield.blog.wordpress_translations); text that is English on WordPress stays English;
  English paragraphs with nothing on WordPress are removed;
- the title, Title tag and Meta description come from WordPress (Yoast, as WordPress outputs it);
- localized images are downloaded and swapped in with their WordPress alt text, and localized
  YouTube videos swapped;
- the page gets the WordPress publication date and the translated topic.

The page is published. Blog pages sit under the blog index, so they are only public once the
index is. The translated blog index is created on first use, as a copy of the English one with no
featured articles or sections, so it lists every article in its language.

A translation is skipped, and reported, when a page in that language already exists, when the
English page is not published or has unpublished changes (the copy would start from old text),
when WordPress has no translation, or when it is on the skip list. `--dry-run` does everything
except write: it fetches from WordPress to check, and reports what would happen. One CSV row is
written per translation.
"""

import csv
import datetime
import difflib
import html
import json
import re
import time
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_default_timezone, make_aware

import requests
from bs4 import BeautifulSoup
from wagtail.models import Locale
from wagtail.utils.file import hash_filelike
from wagtail_localize.segments import OverridableSegmentValue, StringSegmentValue
from wagtail_localize.segments.extract import extract_segments
from wagtail_localize.segments.ingest import ingest_segments
from wagtail_localize.strings import StringValue

from springfield.blog import wordpress_translations as alignment
from springfield.blog.management.commands.fix_imported_blog_posts import YOUTUBE_THUMBNAILS, youtube_thumbnail_url
from springfield.blog.management.commands.import_wordpress_blog_posts import (
    DOWNLOAD_TIMEOUT_SECONDS,
    image_description,
    youtube_video_id,
    youtube_watch_url,
)
from springfield.blog.models import BlogArticlePage, BlogIndexPage
from springfield.cms.models import SpringfieldImage

DEFAULT_WORDPRESS_URL = "https://blog.mozilla.org"
DEFAULT_LOCALES = ("de", "fr")
REST_FIELDS = "id,slug,date,link,title,excerpt,content,yoast_head_json"
SITE_NAME_SUFFIX_RE = re.compile(r"\s+[-|–—]\s+The Mozilla Blog\s*$", re.IGNORECASE)

# translation_url's answer when the English post's page redirects away from WordPress.
REDIRECTED = object()

CREATED = "created"
WOULD_CREATE = "would create"
SKIPPED = "skipped"
FAILED = "failed"

REPORT_HEADER = [
    "slug",
    "locale",
    "action",
    "page_id",
    "url",
    "wordpress_url",
    "wordpress_date",
    "strings",
    "translated",
    "kept_english",
    "removed",
    "doubtful",
    "images_swapped",
    "images_missing",
    "videos_swapped",
    "detail",
]


class Command(BaseCommand):
    help = (
        "Creates the de/fr translations of imported blog posts from their WPML translations on "
        "blog.mozilla.org, as pages linked to the English ones but not synced, and publishes them. "
        "Writes a CSV report. Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument("--slug", action="append", dest="slugs", default=[], help="English post to translate. Repeat for several.")
        parser.add_argument("--all", action="store_true", help="Every English blog post (instead of --slug).")
        parser.add_argument(
            "--locale",
            action="append",
            dest="locales",
            default=[],
            help=f"Language to create. Repeat for several. Default: {', '.join(DEFAULT_LOCALES)}.",
        )
        parser.add_argument(
            "--since", type=datetime.date.fromisoformat, help="Only WordPress translations published on or after this date (YYYY-MM-DD)."
        )
        parser.add_argument(
            "--overrides",
            help='JSON file of hand corrections: {"<slug>-<locale>": [{"en", "tr"}], "_images": {"<slug>-<locale>": [[en_file, tr_file]]}, '
            '"_skip": ["<slug>-<locale>"]}.',
        )
        parser.add_argument("--dry-run", action="store_true", help="Report what would be created without writing to the database.")
        parser.add_argument("--wordpress-url", default=DEFAULT_WORDPRESS_URL, help=f"WordPress site to read from (default: {DEFAULT_WORDPRESS_URL}).")
        parser.add_argument(
            "--report-out",
            default="blog_translations_report.csv",
            help="Path to write the CSV report (default: blog_translations_report.csv). An existing file is overwritten.",
        )

    def handle(self, *args, **options):
        if bool(options["slugs"]) == options["all"]:
            raise CommandError("Pass --slug (one or more) or --all")
        self.dry_run = options["dry_run"]
        self.since = options["since"]
        self.wordpress_url = options["wordpress_url"].rstrip("/")
        self.corrections, self.image_pairs, self.skip = self.read_overrides(options["overrides"])

        source_locale = Locale.get_default()
        locales = []
        for code in options["locales"] or DEFAULT_LOCALES:
            locale = Locale.objects.filter(language_code=code).first()
            if locale is None:
                raise CommandError(f"No Locale found for language code {code!r}")
            locales.append(locale)

        pages = BlogArticlePage.objects.filter(locale=source_locale).order_by("path")
        if options["slugs"]:
            pages = pages.filter(slug__in=options["slugs"])
            missing = set(options["slugs"]) - set(pages.values_list("slug", flat=True))
            if missing:
                raise CommandError(f"No {source_locale.language_code} blog post with slug {', '.join(sorted(missing))}")

        self.english_posts = {}
        self.announced_indexes = set()
        self.counts = {}
        self.report_path = options["report_out"]
        self.report_rows = 0
        prefix = "[dry-run] " if self.dry_run else ""
        self.stdout.write(f"{prefix}Translating {pages.count()} blog posts into {', '.join(locale.language_code for locale in locales)}")
        with open(self.report_path, "w", newline="") as self.report_file:
            self.report = csv.writer(self.report_file)
            self.report.writerow(REPORT_HEADER)
            for page in pages:
                for locale in locales:
                    self.record(self.translate(page.specific, locale))

        summary = ", ".join(f"{action}: {count}" for action, count in sorted(self.counts.items())) or "nothing to do"
        self.stdout.write(f"Done. {summary}.")
        self.stdout.write(f"Wrote {self.report_rows} rows to {self.report_path}")

    # -----------------------------------------------------------------------
    # One translation
    # -----------------------------------------------------------------------

    def translate(self, page, locale):
        """Create the `locale` translation of `page` from WordPress; returns its report row."""
        # A fresh instance each time: ingest_segments writes the translated text into the
        # source page's field values as well as the copy's.
        page = BlogArticlePage.objects.get(pk=page.pk)
        key = f"{page.slug}-{locale.language_code}"
        row = {"slug": page.slug, "locale": locale.language_code}
        if key in self.skip:
            return {**row, "action": SKIPPED, "detail": "on the skip list"}
        existing = page.get_translation_or_none(locale)
        if existing:
            return {**row, "action": SKIPPED, "page_id": existing.pk, "detail": f"a {locale.language_code} page already exists"}
        try:
            english_post = self.english_post(page.slug)
            if english_post is None:
                return {**row, "action": SKIPPED, "detail": "not found on WordPress"}
            translation_url = self.translation_url(english_post["link"], locale.language_code)
            if translation_url is REDIRECTED:
                return {
                    **row,
                    "action": SKIPPED,
                    "detail": "the English post on WordPress redirects (its redirect is active), so its translations can't be looked up",
                }
            if translation_url is None:
                return {**row, "action": SKIPPED, "detail": f"no {locale.language_code} translation on WordPress"}
            row["wordpress_url"] = translation_url
            translated_post = self.wordpress_post(locale.language_code, urlparse(translation_url).path.rstrip("/").rsplit("/", 1)[-1])
            if translated_post is None:
                return {**row, "action": SKIPPED, "detail": f"{translation_url} not found in the WordPress REST API"}
            # WordPress's `date` is wall-clock time in the blog's time zone, which the importer
            # also reads as settings.TIME_ZONE.
            published = make_aware(parse_datetime(translated_post["date"]), get_default_timezone())
            row["wordpress_date"] = published.date().isoformat()
            if self.since and published.date() < self.since:
                return {**row, "action": SKIPPED, "detail": f"translated before {self.since.isoformat()}"}
            if not page.live or page.has_unpublished_changes:
                return {**row, "action": SKIPPED, "detail": "the English page isn't published, or has unpublished changes: publish it first"}

            with transaction.atomic():
                translated_page = self.create_translation(page, locale, english_post, translated_post, published, row, key)
                if self.dry_run:
                    transaction.set_rollback(True)
                    return {**row, "action": WOULD_CREATE}
            return {**row, "action": CREATED, "page_id": translated_page.pk, "url": translated_page.full_url or ""}
        except Exception as exc:
            return {**row, "action": FAILED, "detail": f"{type(exc).__name__}: {exc}"}

    def create_translation(self, page, locale, english_post, translated_post, published, row, key):
        """Copy `page` into `locale`, fill it with the WordPress translation and publish it.
        Fills in `row` with what was translated, kept, removed and swapped."""
        english_paragraphs = alignment.paragraphs(english_post["content"]["rendered"])
        translated_paragraphs = alignment.paragraphs(translated_post["content"]["rendered"])
        paired = alignment.align(english_paragraphs, translated_paragraphs)
        unmatched = alignment.apply_corrections(paired, english_paragraphs, translated_paragraphs, self.corrections.get(key, []))

        english_segments = extract_segments(page)
        page_keys = {alignment.normalise(segment.string.data) for segment in english_segments if isinstance(segment, StringSegmentValue)}
        # WordPress paragraphs whose English the page no longer has word for word (edited since
        # the import): the only ones a near match may take, each once.
        unclaimed = [key for key, translation in paired.translations.items() if translation and key not in page_keys]

        segments, counts, to_remove, doubtful = [], dict(strings=0, translated=0, kept_english=0, removed=0), set(), []
        for segment in english_segments:
            if isinstance(segment, StringSegmentValue):
                counts["strings"] += 1
                new_html = self.translated_string(segment, translated_post, paired, unclaimed, counts, to_remove, doubtful)
                segment = StringSegmentValue(segment.path, StringValue(new_html), attrs=segment.attrs).with_order(segment.order)
            segments.append(segment)

        swaps, dry_run_swaps, missing_images, videos = self.localized_media(english_segments, english_post, translated_post, key)
        segments = [
            OverridableSegmentValue(segment.path, swaps[segment.path]).with_order(segment.order) if segment.path in swaps else segment
            for segment in segments
        ]

        self.translated_blog_index(page.get_parent().specific, locale)
        if page.topic and not page.topic.get_translation_or_none(locale):
            self.publish_topic_translation(page.topic, locale)

        translated_page = page.copy_for_translation(locale)
        ingest_segments(page, translated_page, page.locale, locale, segments)
        counts["removed"], not_removed = self.remove_english_only(translated_page, to_remove)
        videos_swapped = self.swap_videos(translated_page, videos)
        translated_page.first_published_at = published
        translated_page.save_revision(log_action=True).publish(log_action=True)

        notes = [f"doubtful: {text}" for text in doubtful[:3]]
        notes += [f"correction matched nothing: {correction['en']!r}" for correction in unmatched]
        notes += [f"left in English, not on WordPress: {text[:60]}" for text in sorted(not_removed)]
        notes += [f"image not downloadable: {url}" for url in missing_images]
        row.update(
            counts,
            doubtful=len(doubtful),
            images_swapped=len(swaps) + dry_run_swaps,
            images_missing=len(missing_images),
            videos_swapped=videos_swapped,
            detail="; ".join(notes),
        )
        return translated_page

    def translated_string(self, segment, translated_post, paired, unclaimed, counts, to_remove, doubtful):
        """The WordPress text for one English string, mirroring what WordPress shows."""
        english_html = segment.string.data
        if segment.path == "title":
            counts["translated"] += 1
            return StringValue.from_plaintext(html.unescape(translated_post["title"]["rendered"])).data
        yoast = translated_post.get("yoast_head_json") or {}
        if segment.path == "seo_title":
            counts["translated"] += 1
            # Yoast's title is the whole <title>, often with the WordPress site name on the end.
            seo_title = SITE_NAME_SUFFIX_RE.sub("", yoast.get("title") or "")
            return StringValue.from_plaintext(seo_title or html.unescape(translated_post["title"]["rendered"])).data
        if segment.path == "search_description":
            counts["translated"] += 1
            excerpt = BeautifulSoup(translated_post["excerpt"]["rendered"], "html.parser").get_text(" ", strip=True)
            return StringValue.from_plaintext(
                yoast.get("description") or excerpt or alignment.first_words(translated_post["content"]["rendered"])
            ).data
        if english_html.strip().startswith("<!--"):
            return english_html

        key = alignment.normalise(english_html)
        translated_html = paired.translations.get(key, "")
        if translated_html == "" and unclaimed:
            close = difflib.get_close_matches(key, unclaimed, n=1, cutoff=0.8)
            if close:
                unclaimed.remove(close[0])
                translated_html = paired.translations[close[0]]
                doubtful.append(key[:60])
        elif key in paired.doubtful:
            doubtful.append(key[:60])

        if not translated_html:
            if alignment.same_in_every_language(english_html):
                counts["kept_english"] += 1
            else:
                to_remove.add(key)
            return english_html
        if alignment.normalise(translated_html) == key:
            counts["kept_english"] += 1
            return english_html
        counts["translated"] += 1
        tidied = alignment.tidy(translated_html)
        kept = alignment.keep_links(tidied, set(segment.attrs or {}))
        if kept != tidied:
            doubtful.append(f"{key[:50]} (extra link dropped)")
        return kept

    # -----------------------------------------------------------------------
    # Page structure
    # -----------------------------------------------------------------------

    def translated_blog_index(self, english_index, locale):
        """The blog index in `locale`, created on first use with nothing curated, so it lists
        every article in that language."""
        existing = english_index.get_translation_or_none(locale)
        if existing:
            return existing
        index = english_index.copy_for_translation(locale)
        index.featured_articles = []
        index.article_sections = []
        index.save_revision(log_action=True).publish(log_action=True)
        # A dry run rolls the index back with each translation; say so once, not per post.
        if locale.language_code not in self.announced_indexes:
            self.announced_indexes.add(locale.language_code)
            self.stdout.write(f"  {'would create' if self.dry_run else 'created'} the {locale.language_code} blog index")
        return BlogIndexPage.objects.get(pk=index.pk)

    def publish_topic_translation(self, topic, locale):
        """Copy a topic into `locale` with its English name, and publish it."""
        translated_topic = topic.copy_for_translation(locale)
        translated_topic.save()
        translated_topic.save_revision().publish()

    def remove_english_only(self, translated_page, keys):
        """Remove the paragraphs, headings, list items and captions WordPress has no translation
        for, wherever they sit in the body. Returns how many were removed and the texts that
        could not be (plain text fields such as alt text), which stay in English."""
        if not keys:
            return 0, set()
        removed_keys = set()
        removed = 0

        def strip(value, block_type=None):
            nonlocal removed
            if isinstance(value, list):
                return [strip(item) for item in value]
            if isinstance(value, dict):
                # Code is shown as typed; never reparse it as HTML.
                inner_type = value.get("type", block_type)
                if inner_type == "code":
                    return value
                return {name: strip(item, inner_type) for name, item in value.items()}
            if isinstance(value, str) and value.lstrip().startswith("<"):
                soup = BeautifulSoup(value, "html.parser")
                found = [
                    element
                    for element in soup.find_all(["p", "h2", "h3", "h4", "h5", "li", "figcaption"])
                    if alignment.normalise(str(element)) in keys
                ]
                if not found:
                    return value
                for element in found:
                    removed_keys.add(alignment.normalise(str(element)))
                    element.decompose()
                    removed += 1
                return str(soup)
            return value

        # get_prep_value, not raw_data: ingest_segments updates the block values, and raw_data
        # still holds the English the page was copied with.
        translated_page.content = strip(translated_page.content.get_prep_value())
        return removed, keys - removed_keys

    def swap_videos(self, translated_page, videos):
        """Replace English YouTube videos with the translation's, in the body and the hero: the
        video URL and its poster, which is the translated video's own thumbnail."""
        if not videos:
            return 0
        replacements = dict(videos)
        swapped = 0

        def swap(value):
            nonlocal swapped
            if isinstance(value, list):
                return [swap(item) for item in value]
            if not isinstance(value, dict):
                return value
            value = {name: swap(item) for name, item in value.items()}
            english_id = youtube_video_id(value.get("video_url") or "") if isinstance(value.get("video_url"), str) else None
            if english_id in replacements:
                translated_id = replacements[english_id]
                value["video_url"] = youtube_watch_url(translated_id)
                poster = self.youtube_poster(translated_id, value.get("poster"))
                if poster is not None and poster.pk is not None:
                    value["poster"] = poster.pk
                swapped += 1
            return value

        for field_name in ("content", "hero_video"):
            stream = getattr(translated_page, field_name)
            if stream:
                setattr(translated_page, field_name, swap(stream.get_prep_value()))
        return swapped

    def youtube_poster(self, video_id, english_poster_id):
        """The largest YouTube thumbnail of `video_id` as a library image (an existing one with
        the same file, or a new one in the English poster's collection). None if YouTube has
        none; in a dry run, an unsaved image."""
        english_poster = SpringfieldImage.objects.filter(pk=english_poster_id).first() if english_poster_id else None
        for name in YOUTUBE_THUMBNAILS:
            content = self.fetch(youtube_thumbnail_url(video_id, name))
            if not content:
                continue
            existing = SpringfieldImage.objects.filter(file_hash=hash_filelike(ContentFile(content))).first()
            if existing:
                return existing
            if self.dry_run:
                return SpringfieldImage(title=f"{video_id}-{name}")
            return self.create_image(
                f"{video_id}-{name}", "", english_poster.collection if english_poster else None, content, f"{video_id}-{name}.jpg"
            )
        return None

    # -----------------------------------------------------------------------
    # Media
    # -----------------------------------------------------------------------

    def localized_media(self, english_segments, english_post, translated_post, key):
        """For the media that differ between the posts: image overrides keyed by segment path,
        how many images a dry run would swap, image URLs that couldn't be downloaded, and
        (English, translated) YouTube id pairs."""
        english_media = alignment.media(english_post["content"]["rendered"])
        translated_media = alignment.media(translated_post["content"]["rendered"])
        if key in self.image_pairs:
            by_stem = {item.stem: item for item in translated_media}
            pairs = [
                (alignment.Media("image", english_name), by_stem.get(alignment.file_stem(translated_name)))
                for english_name, translated_name in self.image_pairs[key]
            ]
        else:
            matcher = difflib.SequenceMatcher(a=[item.stem for item in english_media], b=[item.stem for item in translated_media], autojunk=False)
            pairs = []
            for operation, english_start, english_end, translated_start, translated_end in matcher.get_opcodes():
                if operation == "replace" and english_end - english_start == translated_end - translated_start:
                    pairs += zip(english_media[english_start:english_end], translated_media[translated_start:translated_end])

        # Body images the English page uses, by file name: (segment path, image), in page order.
        image_segments = [
            segment
            for segment in english_segments
            if isinstance(segment, OverridableSegmentValue) and segment.path.startswith("content.") and segment.path.endswith(".image")
        ]
        images = SpringfieldImage.objects.in_bulk([segment.data for segment in image_segments])
        page_images = {}
        for segment in image_segments:
            if segment.data in images:
                page_images.setdefault(alignment.file_stem(images[segment.data].file.name), []).append((segment.path, images[segment.data]))

        swaps, dry_run_swaps, missing, videos = {}, 0, [], []
        for english, translated in pairs:
            if translated is None or english.kind != translated.kind:
                continue
            if english.kind == "video":
                videos.append((english.source, translated.source))
                continue
            if not page_images.get(english.stem):
                continue
            path, english_image = page_images[english.stem].pop(0)
            image = self.localized_image(translated, english_image.collection)
            if image is None:
                missing.append(translated.source)
            elif image.pk is not None:
                swaps[path] = image.pk
            else:
                dry_run_swaps += 1
        return swaps, dry_run_swaps, missing, videos

    def localized_image(self, translated, collection):
        """The image library copy of a localized WordPress image: an existing one with the same
        file, or a new one with the WordPress alt text. None if it can't be downloaded. In a dry
        run, an unsaved image, so no file is written to storage."""
        content = None
        for url in dict.fromkeys([self.full_size_url(translated.source), translated.source]):
            content = self.fetch(url)
            if content:
                break
        if not content:
            return None
        # An image's description is its alt text, so a file the library holds with different
        # (often English) alt gets its own image. Alt text that is only a file name is dropped,
        # as the importer does, and then any copy of the file will do.
        alt = image_description(translated.alt)
        same_file = SpringfieldImage.objects.filter(file_hash=hash_filelike(ContentFile(content)))
        existing = same_file.filter(description=alt).first() if alt else same_file.first()
        if existing:
            return existing
        name = urlparse(self.full_size_url(translated.source)).path.rsplit("/", 1)[-1]
        title = alignment.file_stem(name).replace("-", " ").replace("_", " ")
        if self.dry_run:
            return SpringfieldImage(title=title)
        return self.create_image(title, alt, collection, content, name)

    def create_image(self, title, description, collection, content, name):
        """Save a downloaded file as a library image, like the importer does, or None if saving
        fails (computing the dimensions fails on some files, such as large animated GIFs)."""
        fields = dict(title=title, description=description, file=ContentFile(content, name=name), file_hash=hash_filelike(ContentFile(content)))
        if collection is not None:
            fields["collection"] = collection
        try:
            with transaction.atomic():
                return SpringfieldImage.objects.create(**fields)
        except Exception:
            return None

    @staticmethod
    def full_size_url(url):
        """The original upload behind one of WordPress's resized copies (`-1024x576`)."""
        path = url.partition("?")[0]
        stem, dot, extension = path.rpartition(".")
        if not dot:
            return url
        return re.sub(r"-\d+x\d+$", "", stem) + dot + extension

    # -----------------------------------------------------------------------
    # WordPress
    # -----------------------------------------------------------------------

    def english_post(self, slug):
        if slug not in self.english_posts:
            self.english_posts[slug] = self.wordpress_post("en", slug)
        return self.english_posts[slug]

    def wordpress_post(self, language, slug):
        response = self.get(f"{self.wordpress_url}/{language}/wp-json/wp/v2/posts", params={"slug": slug, "_fields": REST_FIELDS})
        posts = response.json() if response is not None else []
        return posts[0] if posts else None

    def translation_url(self, english_url, language):
        """The URL of the `language` translation, from the English post's hreflang links, or
        REDIRECTED when the post's page no longer serves WordPress."""
        response = self.get(english_url, follow_redirects=False)
        if response is None:
            return None
        if response.is_redirect:
            return REDIRECTED
        link = BeautifulSoup(response.text, "html.parser").find("link", rel="alternate", hreflang=language)
        return link["href"] if link and link.get("href") else None

    def fetch(self, url):
        try:
            response = self.get(url)
        except requests.RequestException:
            return None
        return response.content if response is not None else None

    def get(self, url, params=None, follow_redirects=True):
        """GET `url`, or None on a 404. A connection problem is retried twice, after 1s and 2s."""
        for attempt in range(3):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=DOWNLOAD_TIMEOUT_SECONDS,
                    headers={"User-Agent": "springfield-blog-translations"},
                    allow_redirects=follow_redirects,
                )
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response

    # -----------------------------------------------------------------------
    # Input and report
    # -----------------------------------------------------------------------

    def read_overrides(self, path):
        if not path:
            return {}, {}, set()
        try:
            with open(path) as overrides_file:
                data = json.load(overrides_file)
        except (OSError, ValueError) as exc:
            raise CommandError(f"Could not read {path}: {exc}") from exc
        corrections = {key: value for key, value in data.items() if not key.startswith("_")}
        image_pairs = {key: value for key, value in data.get("_images", {}).items() if not key.startswith("_")}
        return corrections, image_pairs, set(data.get("_skip", []))

    def record(self, row):
        row = {name: "" for name in REPORT_HEADER} | row
        self.counts[row["action"]] = self.counts.get(row["action"], 0) + 1
        self.report.writerow([row[name] for name in REPORT_HEADER])
        self.report_file.flush()
        self.report_rows += 1
        (self.stderr if row["action"] == FAILED else self.stdout).write(
            f"  {row['action']}: {row['slug']} {row['locale']}{': ' + row['detail'] if row['detail'] else ''}"
        )
