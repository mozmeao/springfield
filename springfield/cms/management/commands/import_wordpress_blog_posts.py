# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.utils.timezone import get_default_timezone, make_aware

import requests
from bs4 import BeautifulSoup, Comment
from wagtail.models import Locale

from springfield.cms.models import Author, BlogArticlePage, BlogIndexPage, SpringfieldImage, Tag

# WordPress wraps inline images with a `[caption ...]<img ...> caption text[/caption]` shortcode.
# We only care about the <img> itself; the caption prose has nowhere to go in our block set.
CAPTION_SHORTCODE_RE = re.compile(r"\[caption[^\]]*\](.*?)\[/caption\]", re.DOTALL)
IMG_TAG_RE = re.compile(r"<img[^>]*>")


def _text(post, tag):
    node = post.find(tag)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


class Command(BaseCommand):
    help = (
        "Imports blog posts from the flat WordPress export XML (mozilla-blog-posts.xml) into a "
        "BlogIndexPage, creating BlogArticlePage children plus any Tag/Author snippets and images "
        "they reference. Writes a CSV mapping old permalinks to new page IDs for use with the "
        "import_wordpress_redirects command."
    )

    def add_arguments(self, parser):
        parser.add_argument("xml_path", help="Path to the WordPress export XML file.")
        parser.add_argument("--locale", default="en-US", help="Locale code to import posts into (default: en-US).")
        parser.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing anything.")
        parser.add_argument(
            "--redirects-out",
            default="wordpress_redirects.csv",
            help="Path to write the old-permalink -> new-page-id CSV (default: wordpress_redirects.csv). "
            "An existing file at this path is overwritten, not appended to.",
        )

    def handle(self, *args, **options):
        xml_path = Path(options["xml_path"])
        if not xml_path.exists():
            raise CommandError(f"File not found: {xml_path}")

        self.dry_run = options["dry_run"]
        self._image_cache = {}

        locale = Locale.objects.filter(language_code=options["locale"]).first()
        if locale is None:
            raise CommandError(f"No Locale found for language code {options['locale']!r}")

        index_page = BlogIndexPage.objects.filter(locale=locale).first()
        if index_page is None:
            raise CommandError(f"No BlogIndexPage found for locale {locale.language_code!r}")

        posts = ElementTree.parse(xml_path).getroot().findall("post")
        self.stdout.write(f"Found {len(posts)} posts in {xml_path}")

        redirect_rows = []
        imported = skipped = failed = 0

        for post in posts:
            slug = _text(post, "Slug")
            title = _text(post, "Title")

            post_type = _text(post, "PostType")
            if post_type != "post":
                self.stderr.write(
                    f"    ! skipping post ID {_text(post, 'ID')} ({slug!r}): "
                    f"unsupported PostType {post_type!r} - this command only handles 'post'."
                )
                failed += 1
                continue

            if BlogArticlePage.objects.filter(slug=slug, locale=locale).exists():
                self.stdout.write(f"  skip (already imported): {slug}")
                skipped += 1
                continue

            self.stdout.write(f"  {'[dry-run] ' if self.dry_run else ''}importing: {title}")

            try:
                redirect_row = self._import_post(post, index_page, locale)
            except Exception as exc:
                self.stderr.write(f"    ! failed to import {slug!r}: {exc}")
                failed += 1
                continue

            if redirect_row is not None:
                redirect_rows.append(redirect_row)
            imported += 1

        if not self.dry_run and redirect_rows:
            self._write_redirects_csv(options["redirects_out"], redirect_rows)

        self.stdout.write(f"Done. {imported} imported, {skipped} skipped, {failed} failed.")

    @transaction.atomic
    def _import_post(self, post, index_page, locale):
        """Import a single post. Runs in its own transaction so that a failure
        (e.g. a dead image URL) rolls back cleanly without affecting other posts
        or leaving a half-written page behind."""
        slug = _text(post, "Slug")
        title = _text(post, "Title")

        content, warnings = self._build_content(_text(post, "Content"))
        for warning in warnings:
            self.stderr.write(f"    ! {warning}")

        if self.dry_run:
            return None

        categories = [name.strip() for name in _text(post, "Categories").split("|") if name.strip()]
        if not categories:
            raise ValueError(f"post {slug!r} has no Category - BlogArticlePage.topic is required and cannot be blank")

        # BlogArticlePage.topic is a single, required Tag. WordPress posts can carry more than
        # one category, so we use the first as the topic and fold any extras in alongside Tags.
        topic = self._get_or_create_snippet(Tag, categories[0], locale)
        tag_names = [name for name in _text(post, "Tags").split("|") if name.strip()] + categories[1:]
        tags = [self._get_or_create_snippet(Tag, name, locale) for name in tag_names]
        author = self._get_or_create_author(post, locale)
        image = self._get_or_create_image(_text(post, "ImageURL"), _text(post, "ImageTitle") or title)

        page = BlogArticlePage(
            title=title,
            slug=slug,
            locale=locale,
            topic=topic,
            author=author,
            image=image,
            content=content,
            first_published_at=self._parse_wp_date(_text(post, "Date")),
        )
        index_page.add_child(instance=page)
        if tags:
            page.tags.set(tags)
        revision = page.save_revision()
        revision.publish()

        return (_text(post, "ID"), _text(post, "Permalink"), page.id, page.url)

    def _parse_wp_date(self, text):
        """Parse a WordPress export Date (no timezone info) as wall-clock time in
        settings.TIME_ZONE (America/Los_Angeles), since that's where these dates originated."""
        parsed = parse_datetime(text)
        if parsed is None:
            return None
        return make_aware(parsed, get_default_timezone())

    def _get_or_create_snippet(self, model, name, locale):
        name = name.strip()
        if not name:
            return None

        slug = slugify(name)
        snippet, _created = model.objects.get_or_create(slug=slug, locale=locale, defaults={"name": name})
        return snippet

    def _get_or_create_author(self, post, locale):
        name = f"{_text(post, 'AuthorFirstName')} {_text(post, 'AuthorLastName')}".strip()
        if not name:
            name = _text(post, "AuthorUsername")
        return self._get_or_create_snippet(Author, name, locale)

    def _get_or_create_image(self, url, title):
        url = url.strip()
        if not url:
            return None

        title = title.strip() or Path(urlparse(url).path).name

        # Dedupe by the source filename, not `title`: `title` is free text (WordPress's
        # ImageTitle/alt text) and different images frequently share a generic title, which
        # would wrongly reuse an unrelated file. The filename from the WordPress media URL
        # is a much more reliable proxy for "is this the same asset".
        filename = Path(urlparse(url).path).name or "image.jpg"

        if filename in self._image_cache:
            return self._image_cache[filename]

        # Storage disambiguates same-named files by appending a suffix, so an exact filename
        # match only finds an existing image if this is the very first time that name was seen -
        # good enough for resuming an interrupted run without re-downloading everything.
        existing = SpringfieldImage.objects.filter(file__iendswith=filename).first()
        if existing is not None:
            self._image_cache[filename] = existing
            return existing

        response = None
        last_exc = None
        for attempt in range(1, 4):
            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_exc = exc
                response = None
                if attempt < 3:
                    time.sleep(2**attempt)  # 2s, 4s backoff, in case a slow/throttled connection just needs a moment

        if response is None:
            self.stderr.write(f"    ! could not download image {url} after 3 attempts: {last_exc}")
            return None

        image = SpringfieldImage.objects.create(title=title, file=ContentFile(response.content, name=filename))
        self._image_cache[filename] = image
        return image

    def _build_content(self, html):
        """Split raw WordPress HTML into `content` StreamField blocks (text/media/code).

        This is a pragmatic, one-off converter for this specific export, not a general
        WordPress-HTML-to-Wagtail-blocks library: it only needs to handle what actually
        appears in mozilla-blog-posts.xml (plain paragraphs, inline images, a handful of
        [caption] shortcodes, and a few YouTube iframe embeds).
        """
        warnings = []

        def replace_caption(match):
            inner = match.group(1)
            img_match = IMG_TAG_RE.search(inner)
            return img_match.group(0) if img_match else ""

        html = CAPTION_SHORTCODE_RE.sub(replace_caption, html)

        soup = BeautifulSoup(f"<div>{html}</div>", "html.parser")
        root = soup.div

        blocks = []
        text_buffer = []

        def flush_text():
            joined = "".join(str(node) for node in text_buffer).strip()
            text_buffer.clear()
            if joined:
                blocks.append(("text", joined))

        for node in root.contents:
            if isinstance(node, Comment):
                continue
            if getattr(node, "name", None) == "img":
                flush_text()
                if not self.dry_run:
                    image = self._get_or_create_image(node.get("src", ""), node.get("alt", ""))
                    if image is not None:
                        blocks.append(("media", [("image", {"image": image, "settings": {}})]))
                else:
                    blocks.append(("media", "[dry-run image]"))
                continue
            if getattr(node, "name", None) == "iframe":
                flush_text()
                src = node.get("src", "")
                warnings.append(f"iframe embed ({src}) has no poster image available - linked as plain text instead of a video block")
                text_buffer.append(f'<p><a href="{src}">{src}</a></p>')
                flush_text()
                continue
            if getattr(node, "name", None) == "pre":
                flush_text()
                blocks.append(("code", {"code": node.get_text()}))
                continue
            text_buffer.append(node)

        flush_text()
        return blocks, warnings

    def _write_redirects_csv(self, path, rows):
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["wp_id", "old_permalink", "new_page_id", "new_page_path"])
            writer.writerows(rows)
        self.stdout.write(f"Wrote {len(rows)} redirect mappings to {path}")
