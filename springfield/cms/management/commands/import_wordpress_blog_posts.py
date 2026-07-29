# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import html
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
from bs4 import BeautifulSoup, Comment, Tag as HtmlTag
from wagtail.models import Locale

from springfield.cms.models import Author, BlogArticlePage, BlogIndexPage, SpringfieldImage, Tag

# Older WordPress posts wrap inline images with a `[caption ...]<img ...> caption text[/caption]`
# shortcode, while newer (Gutenberg) ones use `<figure><img ...><figcaption>...</figcaption></figure>`.
# The shortcode is rewritten into the figure form so both take the same path through parse_content.
CAPTION_SHORTCODE_RE = re.compile(r"\[caption[^\]]*\](.*?)\[/caption\]", re.DOTALL)
IMG_TAG_RE = re.compile(r"<img[^>]*>")


def element_text(post, tag):
    node = post.find(tag)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def parse_categories(raw):
    """Turn the WordPress Categories field into topic/tag names, most specific first.

    Categories are pipe-separated and may be hierarchical with '>'. Each level becomes its own
    name, leaf first, so the caller takes the first as the topic and the rest as tags. HTML
    entities are decoded, and the blanket 'Firefox' category is dropped unless it's all a post has.

    e.g. 'Our Work>AI>AI Tech|Firefox>Firefox AI' -> ['AI Tech', 'Our Work', 'AI', 'Firefox AI']
    """
    names = []
    for category in raw.split("|"):
        if not category.strip():
            continue
        segments = [html.unescape(segment).strip() for segment in category.split(">")]
        for name in [segments[-1], *segments[:-1]]:
            if name and name not in names:
                names.append(name)
    meaningful = [name for name in names if name != "Firefox"]
    return meaningful or names


def caption_html(figcaption):
    """Return a figcaption's inner HTML wrapped in a paragraph, ready for a RichTextBlock.

    The <p> matters: the block template runs the value through `remove_p_tag`, which
    yields nothing at all for rich text that isn't wrapped in a block-level tag.
    """
    inner = figcaption.decode_contents().strip()
    return f"<p>{inner}</p>" if inner else ""


def parse_content(raw_html):
    """Convert a post's WordPress HTML body into ordered block specs, plus any warnings.

    Specs are ("text", html), ("image", {"src", "alt", "caption"}) or ("code", {"code": ...}).
    Image specs hold only the URL and are downloaded later, so parsing does no I/O. Only the
    markup this export uses is handled: paragraphs, inline images, captioned figures (and the
    equivalent [caption] shortcode), and YouTube iframes (linked as plain text, as we have no
    poster image for them).
    """
    warnings = []

    def replace_caption(match):
        """Rewrite a [caption] shortcode as a <figure>, keeping the prose after the <img>."""
        body = match.group(1)
        img_match = IMG_TAG_RE.search(body)
        if img_match is None:
            return ""
        img_tag = img_match.group(0)
        caption = body[img_match.end() :].strip()
        if not caption:
            return img_tag
        return f"<figure>{img_tag}<figcaption>{caption}</figcaption></figure>"

    raw_html = CAPTION_SHORTCODE_RE.sub(replace_caption, raw_html)

    soup = BeautifulSoup(f"<div>{raw_html}</div>", "html.parser")
    root = soup.div

    specs = []
    text_buffer = []

    def flush_text():
        joined = "".join(str(node) for node in text_buffer).strip()
        text_buffer.clear()
        if joined:
            specs.append(("text", joined))

    def image_spec(img, figcaption=None):
        return (
            "image",
            {
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "caption": caption_html(figcaption) if figcaption is not None else "",
            },
        )

    def keep_as_text(node):
        """Buffer a node as rich text, reporting any caption that goes with it.

        Captions only survive as an Image + Caption block when they sit on a figure holding a
        single image. Anything else (a gallery, an embed, a figure nested in another container)
        keeps its caption inline in the text, which is worth telling the operator about.
        """
        figcaptions = node.find_all("figcaption") if isinstance(node, HtmlTag) else []
        for figcaption in figcaptions:
            text = figcaption.get_text(strip=True)
            if text:
                warnings.append(f"caption {text!r} could not be attached to a single image - left inline in a text block")
        text_buffer.append(node)

    for node in root.contents:
        if isinstance(node, Comment):
            continue
        name = getattr(node, "name", None)
        if name == "img":
            flush_text()
            specs.append(image_spec(node))
            continue
        if name == "figure":
            # Only a figure holding exactly one image maps onto a block. A gallery's caption
            # describes the whole gallery, and an embed's has no image to attach to at all.
            images = node.find_all("img")
            if len(images) == 1 and node.find("figure") is None:
                flush_text()
                specs.append(image_spec(images[0], node.find("figcaption", recursive=False)))
            else:
                keep_as_text(node)
            continue
        if name == "iframe":
            flush_text()
            src = node.get("src", "")
            warnings.append(f"iframe embed ({src}) has no poster image available - linked as plain text instead of a video block")
            text_buffer.append(f'<p><a href="{src}">{src}</a></p>')
            flush_text()
            continue
        if name == "pre":
            flush_text()
            specs.append(("code", {"code": node.get_text()}))
            continue
        keep_as_text(node)

    flush_text()
    return specs, warnings


class Command(BaseCommand):
    help = (
        "Imports blog posts from the flat WordPress export XML (mozilla-blog-posts.xml) into a "
        "BlogIndexPage, creating BlogArticlePage children plus any Tag/Author snippets and images "
        "they reference. Writes a CSV mapping each post's old blog.mozilla.org URL to its new URL "
        "on this site, to hand to the blog.mozilla.org team so they can set up redirects on their end."
    )

    def add_arguments(self, parser):
        parser.add_argument("xml_path", help="Path to the WordPress export XML file.")
        parser.add_argument("--locale", default="en-US", help="Locale code to import posts into (default: en-US).")
        parser.add_argument("--index-slug", default="blog", help="Slug of the BlogIndexPage to import posts under (default: blog).")
        parser.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing anything.")
        parser.add_argument(
            "--url-map-out",
            default="wordpress_url_map.csv",
            help="Path to write the old-URL -> new-URL CSV (default: wordpress_url_map.csv). "
            "An existing file at this path is overwritten, not appended to.",
        )

    def handle(self, *args, **options):
        xml_path = Path(options["xml_path"])
        if not xml_path.exists():
            raise CommandError(f"File not found: {xml_path}")

        self.dry_run = options["dry_run"]
        self.image_cache = {}

        locale = Locale.objects.filter(language_code=options["locale"]).first()
        if locale is None:
            raise CommandError(f"No Locale found for language code {options['locale']!r}")

        index_page = BlogIndexPage.objects.filter(locale=locale, slug=options["index_slug"]).first()
        if index_page is None:
            raise CommandError(f"No BlogIndexPage found with slug {options['index_slug']!r} for locale {locale.language_code!r}")

        posts = ElementTree.parse(xml_path).getroot().findall("post")
        self.stdout.write(f"Found {len(posts)} posts in {xml_path}")

        url_map_rows = []
        imported = skipped = failed = 0

        for post in posts:
            slug = element_text(post, "Slug")
            title = element_text(post, "Title")

            post_type = element_text(post, "PostType")
            if post_type != "post":
                # Not an error - the export includes pages/attachments this command deliberately
                # doesn't handle. Report it as a skip rather than a failure.
                self.stdout.write(f"  skip (unsupported PostType {post_type!r}): {slug}")
                skipped += 1
                continue

            if BlogArticlePage.objects.filter(slug=slug, locale=locale).exists():
                self.stdout.write(f"  skip (already imported): {slug}")
                skipped += 1
                continue

            self.stdout.write(f"  {'[dry-run] ' if self.dry_run else ''}importing: {title}")

            try:
                url_map_row = self.import_post(post, index_page, locale)
            except Exception as exc:
                self.stderr.write(f"    ! failed to import {slug!r}: {exc}")
                failed += 1
                continue

            if url_map_row is not None:
                url_map_rows.append(url_map_row)
            imported += 1

        if not self.dry_run and url_map_rows:
            self.write_url_map_csv(options["url_map_out"], url_map_rows)

        self.stdout.write(f"Done. {imported} imported, {skipped} skipped, {failed} failed.")

    @transaction.atomic
    def import_post(self, post, index_page, locale):
        """Import one post in its own transaction, so a failure (e.g. a dead image URL)
        rolls back cleanly instead of leaving a half-written page behind."""
        slug = element_text(post, "Slug")
        title = element_text(post, "Title")

        content_specs, warnings = parse_content(element_text(post, "Content"))
        for warning in warnings:
            self.stderr.write(f"    ! {warning}")

        if self.dry_run:
            return None

        categories = parse_categories(element_text(post, "Categories"))
        if not categories:
            raise ValueError(f"post {slug!r} has no Category - BlogArticlePage.topic is required and cannot be blank")

        # topic is a single required Tag; the first (most specific) category becomes the topic
        # and the rest join the post's tags.
        topic = self.get_or_create_snippet(Tag, categories[0], locale)
        tag_names = [name for name in element_text(post, "Tags").split("|") if name.strip()] + categories[1:]
        tags = [self.get_or_create_snippet(Tag, name, locale) for name in tag_names]
        author = self.get_or_create_author(post, locale)
        image = self.get_or_create_image(element_text(post, "ImageURL"), element_text(post, "ImageTitle") or title)
        content = self.materialize_content(content_specs)

        page = BlogArticlePage(
            title=title,
            slug=slug,
            locale=locale,
            topic=topic,
            author=author,
            image=image,
            display_image=True,
            content=content,
            first_published_at=self.parse_wp_date(element_text(post, "Date")),
        )
        index_page.add_child(instance=page)
        if tags:
            page.tags.set(tags)
        revision = page.save_revision()
        revision.publish()

        return (element_text(post, "ID"), element_text(post, "Permalink"), page.full_url)

    def parse_wp_date(self, text):
        """Parse a WordPress export Date (no timezone info) as wall-clock time in
        settings.TIME_ZONE (America/Los_Angeles), since that's where these dates originated."""
        parsed = parse_datetime(text)
        if parsed is None:
            return None
        return make_aware(parsed, get_default_timezone())

    def get_or_create_snippet(self, model, name, locale):
        name = name.strip()
        if not name:
            return None

        slug = slugify(name)
        snippet, _ = model.objects.get_or_create(slug=slug, locale=locale, defaults={"name": name})
        return snippet

    def get_or_create_author(self, post, locale):
        name = f"{element_text(post, 'AuthorFirstName')} {element_text(post, 'AuthorLastName')}".strip()
        if not name:
            name = element_text(post, "AuthorUsername")
        return self.get_or_create_snippet(Author, name, locale)

    def get_or_create_image(self, url, title):
        url = url.strip()
        if not url:
            return None

        title = title.strip() or Path(urlparse(url).path).name

        # Identify an asset by its source filename, not its title: titles are free WordPress
        # text that unrelated images often share, while the media URL's filename is reliable.
        filename = Path(urlparse(url).path).name or "image.jpg"

        if filename in self.image_cache:
            return self.image_cache[filename]

        # Reuse an already-imported file (e.g. when resuming a run). Match the exact stored
        # basename: `file__iendswith` alone would also match a name that is merely a suffix of
        # another, e.g. 'cat.jpg' inside 'bobcat.jpg'.
        existing = next(
            (candidate for candidate in SpringfieldImage.objects.filter(file__iendswith=filename) if Path(candidate.file.name).name == filename),
            None,
        )
        if existing is not None:
            self.image_cache[filename] = existing
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
                    time.sleep(2**attempt)  # 2s then 4s backoff between attempts

        if response is None:
            self.stderr.write(f"    ! could not download image {url} after 3 attempts: {last_exc}")
            return None

        image = SpringfieldImage.objects.create(title=title, file=ContentFile(response.content, name=filename))
        self.image_cache[filename] = image
        return image

    def materialize_content(self, specs):
        """Build the StreamField `content` from block specs, downloading each inline image.

        A captioned image becomes an Image + Caption block; an uncaptioned one a plain media
        image. An image that fails to download is skipped, along with its caption, so one dead
        URL doesn't lose the whole post.
        """
        blocks = []
        for block_type, value in specs:
            if block_type == "image":
                image = self.get_or_create_image(value["src"], value["alt"])
                if image is None:
                    continue
                image_value = {"image": image, "settings": {}}
                if value.get("caption"):
                    blocks.append(("image_caption", {"image": image_value, "caption": value["caption"]}))
                else:
                    blocks.append(("media", [("image", image_value)]))
            else:
                blocks.append((block_type, value))
        return blocks

    def write_url_map_csv(self, path, rows):
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["wp_id", "old_url", "new_url"])
            writer.writerows(rows)
        self.stdout.write(f"Wrote {len(rows)} URL mappings to {path}")
