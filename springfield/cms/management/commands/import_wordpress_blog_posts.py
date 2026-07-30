# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Import blog.mozilla.org posts from a flat WordPress export into BlogArticlePages.

Each <post> in the export becomes one BlogArticlePage, in its own transaction, so a post that
fails leaves nothing half-written behind and doesn't stop the ones after it.

A post's HTML body is converted in two passes, which is the main thing to know when reading this
module:

1. `parse_content` (and `ContentParser`) turn the HTML into ordered *block specs* - plain tuples
   like ("image", {"src": ..., "alt": ..., "caption": ...}). This pass is pure: it downloads
   nothing and touches no database, so it can be tested against HTML strings.
2. `Command.materialize_content` turns those specs into real StreamField blocks, downloading each
   image as it goes. This is where all the I/O lives.

The export's markup rarely maps onto our blocks one-to-one, so anything that can't be represented
is reported through `Command.warn` rather than dropped silently: a caption with no single image to
attach to, a self-hosted video, an image that won't download. Warnings go to stderr as the run
proceeds and to a CSV keyed by the post they came from, because a long run's output scrolls past.

Two CSVs are written, both row by row so a crash keeps whatever finished:
- the old-URL -> new-URL map, to hand to the blog.mozilla.org team for their redirects
- the warnings, as a worklist of what needs a human afterwards
"""

import csv
import html
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse
from xml.etree import ElementTree

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.template.defaultfilters import filesizeformat
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.utils.timezone import get_default_timezone, make_aware

import requests
from bs4 import BeautifulSoup, Comment, Tag as HtmlTag
from wagtail.models import Locale

from springfield.cms.models import Author, BlogArticlePage, BlogIndexPage, SpringfieldImage, Tag

# Older WordPress posts wrap inline images with a `[caption ...]<img ...> caption text[/caption]`
# shortcode, while newer (Gutenberg) ones use `<figure><img ...><figcaption>...</figcaption></figure>`.
# The shortcode is rewritten into the figure form so both take the same path through the parser.
CAPTION_SHORTCODE_RE = re.compile(r"\[caption[^\]]*\](.*?)\[/caption\]", re.DOTALL)
IMG_TAG_RE = re.compile(r"<img[^>]*>")

# Layout wrappers WordPress puts around blocks (groups, media-and-text pairs, columns). They
# carry no meaning we keep, so the parser steps inside them to reach the figures they hold.
CONTAINER_TAGS = {"div", "section"}

# Media URLs go down often enough that one attempt isn't enough, with a widening gap between tries.
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_TIMEOUT_SECONDS = 60

# Warning kinds, recorded alongside each message so the CSV can be filtered by them.
WARNING_CAPTION = "caption"
WARNING_VIDEO = "video"
WARNING_EMBED = "embed"
WARNING_DOWNLOAD = "download"
WARNING_PROCESSING = "processing"
WARNING_ALT_TEXT = "alt-text"
WARNING_FAILURE = "failure"

# Wagtail's own accessibility check rejects alt text that ends in an image extension or contains
# an underscore (see AccessibilityItem.axe_custom_checks). Trailing pixel dimensions and text with
# no spaces at all are the other two shapes the WordPress media library produces.
FILENAME_LIKE_PATTERNS = (
    re.compile(r"\.(avif|gif|jpg|jpeg|png|svg|webp)$", re.IGNORECASE),
    re.compile(r"_"),
    re.compile(r"[-_]\d{2,4}x\d{2,4}\b"),
    re.compile(r"^\S+$"),
)


# ---------------------------------------------------------------------------
# Reading the export's fields
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Output files
# ---------------------------------------------------------------------------


class IncrementalCsv:
    """A CSV that is written as rows arrive, rather than all at once at the end.

    Importing is long-running and can die outright - a segfault in the image libraries, an OOM
    kill, a Ctrl-C. Each post is committed in its own transaction, so a crash still leaves
    imported pages behind; flushing every row keeps the record of them instead of losing the
    whole file. Re-running does not rebuild it, because those posts are skipped as already
    imported.

    The file is only created once there is a row to write, so a run with nothing to report
    doesn't leave an empty CSV behind.
    """

    def __init__(self, path, header):
        self.path = path
        self.header = header
        self.count = 0
        self._file = None
        self._writer = None

    def write(self, row):
        if self._file is None:
            self._file = open(self.path, "w", newline="")
            self._writer = csv.writer(self._file)
            self._writer.writerow(self.header)
        self._writer.writerow(row)
        # Hand the row to the OS now: a segfault loses Python's buffer, not the kernel's.
        self._file.flush()
        self.count += 1

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None


# ---------------------------------------------------------------------------
# Media URLs and text, all pure functions of their input
# ---------------------------------------------------------------------------


def youtube_video_id(url):
    """Return the YouTube video id in `url`, or None if it isn't a YouTube link.

    Covers the three forms this export uses: /watch?v=, youtu.be/ and /embed/.
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host == "youtu.be" or host.endswith(".youtu.be"):
        return parsed.path.strip("/").split("/")[0] or None
    if host == "youtube.com" or host.endswith(".youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/embed/"):
            return parsed.path[len("/embed/") :].strip("/").split("/")[0] or None
    return None


def youtube_watch_url(video_id):
    """Build the canonical watch URL for a video id.

    VideoBlock and its component both detect YouTube by looking for 'youtube.com' or 'youtu.be'
    in the URL, and the player swaps in the youtube-nocookie domain when the video is played,
    so the stored URL stays on the canonical host.
    """
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_poster_url(video_id):
    """Build the thumbnail URL used as the video block's poster image.

    hqdefault is the largest size YouTube generates for every upload; maxresdefault is missing
    for older videos.
    """
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


def embed_block_url(figure):
    """Return the URL a WordPress embed block wraps, or "" if this figure isn't one."""
    wrapper = figure.find("div", class_="wp-block-embed__wrapper")
    if wrapper is None:
        return ""
    url = wrapper.get_text(strip=True)
    return url if url.startswith("http") else ""


def image_description(text):
    """Return `text` if it reads as a description of an image, or "" if it looks like a file name.

    WordPress fills its image fields with whatever the file happened to be called, so most of
    these are names like 'fx_blog_header_extensions_writing' rather than descriptions. Wagtail
    uses this as the image's alt text, where a file name is worse than nothing - a screen reader
    reads it out - so it is dropped rather than passed on.
    """
    text = (text or "").strip()
    if any(pattern.search(text) for pattern in FILENAME_LIKE_PATTERNS):
        return ""
    return text


def video_link(url):
    """Link to a video we can't turn into a block, labelled rather than showing a raw URL.

    The query string goes too. WordPress captured these from share links, so it carries tracking
    - session ids, checksums, timestamps - rather than anything needed to reach the video.
    """
    without_tracking = urlunparse(urlparse(url)._replace(query="", fragment=""))
    return f'<p><a href="{html.escape(without_tracking, quote=True)}">Watch video</a></p>'


def caption_html(figcaption):
    """Return a figcaption's inner HTML wrapped in a paragraph, ready for a RichTextBlock.

    The <p> matters: the block template runs the value through `remove_p_tag`, which
    yields nothing at all for rich text that isn't wrapped in a block-level tag.
    """
    inner = figcaption.decode_contents().strip()
    return f"<p>{inner}</p>" if inner else ""


# ---------------------------------------------------------------------------
# HTML body -> block specs (no I/O)
# ---------------------------------------------------------------------------


def rewrite_caption_shortcodes(raw_html):
    """Rewrite every `[caption]` shortcode as a `<figure>`, keeping the prose after the `<img>`.

    Doing this up front means the parser only has to understand one way of writing a captioned
    image. A shortcode with no image in it carries nothing we can use, so it goes.
    """

    def replace(match):
        body = match.group(1)
        img_match = IMG_TAG_RE.search(body)
        if img_match is None:
            return ""
        img_tag = img_match.group(0)
        caption = body[img_match.end() :].strip()
        if not caption:
            return img_tag
        return f"<figure>{img_tag}<figcaption>{caption}</figcaption></figure>"

    return CAPTION_SHORTCODE_RE.sub(replace, raw_html)


def image_spec(img, figcaption=None):
    """Build an image spec from an `<img>` tag and, if it has one, its caption."""
    return (
        "image",
        {
            "src": img.get("src", ""),
            "alt": img.get("alt", ""),
            "caption": caption_html(figcaption) if figcaption is not None else "",
        },
    )


class ContentParser:
    """Converts a post's HTML body into ordered block specs, collecting warnings as it goes.

    Prose accumulates in `text_buffer` and is flushed into a text spec whenever a block-level
    element interrupts it, which is what preserves the original running order. Nothing here
    downloads anything: image specs carry only the source URL.

    Use `parse_content`; this class is the machinery behind it.
    """

    def __init__(self):
        self.specs = []
        self.warnings = []
        self.text_buffer = []

    def parse(self, raw_html):
        soup = BeautifulSoup(f"<div>{rewrite_caption_shortcodes(raw_html)}</div>", "html.parser")
        self.process(soup.div.contents)
        self.flush_text()
        return self.specs, self.warnings

    def process(self, nodes):
        """Walk a run of sibling nodes, turning the ones we have blocks for into specs."""
        for node in nodes:
            if isinstance(node, Comment):
                continue
            name = getattr(node, "name", None)
            if name == "img":
                self.flush_text()
                self.specs.append(image_spec(node))
            elif name == "figure":
                self.add_figure(node)
            elif name == "iframe":
                self.add_video(node.get("src", ""), alt="")
            elif name == "video":
                self.keep_video_as_text(node)
            elif name == "pre":
                self.flush_text()
                self.specs.append(("code", {"code": node.get_text()}))
            elif name in CONTAINER_TAGS and node.find("figure") is not None:
                # A layout wrapper (a group, a media-and-text pair) holding a figure: step inside
                # so the image is imported rather than left hotlinked in a text block. The
                # wrapper's own prose keeps its place in the surrounding text.
                self.process(node.contents)
            else:
                self.keep_as_text(node)

    def warn(self, kind, message):
        self.warnings.append((kind, message))

    def flush_text(self):
        """Close off the prose collected so far as a text spec."""
        joined = "".join(str(node) for node in self.text_buffer).strip()
        self.text_buffer.clear()
        if joined:
            self.specs.append(("text", joined))

    def keep_as_text(self, node):
        """Buffer a node as rich text, reporting any caption that goes down with it.

        A caption only survives as an Image + Caption block when it sits on a figure holding a
        single image. Anything else keeps its caption inline in the text, which the operator
        should hear about.
        """
        figcaptions = node.find_all("figcaption") if isinstance(node, HtmlTag) else []
        for figcaption in figcaptions:
            text = figcaption.get_text(strip=True)
            if text:
                self.warn(WARNING_CAPTION, f"caption {text!r} could not be attached to a single image - left inline in a text block")
        self.text_buffer.append(node)

    def keep_video_as_text(self, node):
        """Leave a self-hosted video where it is, and say so.

        The video block only accepts YouTube and assets.mozilla.net URLs, so an mp4 served from
        the blog itself has nowhere to go. It stays inline, still pointing at blog.mozilla.org,
        which needs handling separately - hence the warning rather than a silent pass.
        """
        video = node if node.name == "video" else node.find("video")
        self.warn(
            WARNING_VIDEO,
            f"self-hosted video {video.get('src', '')} cannot be imported into a video block - left inline in a text block",
        )
        self.text_buffer.append(node)

    def add_video(self, url, alt):
        """Add a video block spec for a YouTube URL, or a labelled link for any other provider.

        The video block only accepts YouTube and assets.mozilla.net URLs. A rich text <embed> is
        no use for the rest: providers outside Wagtail's oEmbed list (e.g. TikTok) resolve to
        nothing, and their players are blocked by the site's CSP anyway.
        """
        self.flush_text()
        video_id = youtube_video_id(url)
        if video_id is None:
            self.warn(WARNING_EMBED, f"{url} is not a YouTube video - linked as plain text instead of a video block")
            self.specs.append(("text", video_link(url)))
        else:
            self.specs.append(("video", {"url": youtube_watch_url(video_id), "alt": alt}))

    def add_figure(self, figure):
        """Map a figure onto whichever block fits: a gallery, one image, a video, or plain text."""
        if figure.find("video") is not None:
            # The figure's caption travels inline with the video, so it needs no separate warning.
            self.keep_video_as_text(figure)
            return

        if figure.find("figure") is not None:
            self.add_gallery(figure)
            return

        images = figure.find_all("img")
        if len(images) == 1:
            self.flush_text()
            self.specs.append(image_spec(images[0], figure.find("figcaption", recursive=False)))
            return

        embed_url = embed_block_url(figure)
        if embed_url:
            own_caption = figure.find("figcaption", recursive=False)
            self.add_video(embed_url, alt=own_caption.get_text(strip=True) if own_caption else "")
            return

        self.keep_as_text(figure)

    def add_gallery(self, gallery):
        """Turn each figure nested in a gallery into an image spec of its own.

        We have no gallery block, so the images become a run of individual ones. The gallery's own
        caption describes the whole set, so it only maps onto a block when the set turns out to
        hold a single image that has no caption already.
        """
        own_caption = gallery.find("figcaption", recursive=False)
        first_spec = len(self.specs)
        self.process([child for child in gallery.contents if child is not own_caption])
        if own_caption is None:
            return

        produced = [spec for spec in self.specs[first_spec:] if spec[0] == "image"]
        if len(produced) == 1 and not produced[0][1]["caption"]:
            produced[0][1]["caption"] = caption_html(own_caption)
            return

        text = own_caption.get_text(strip=True)
        if text:
            self.warn(WARNING_CAPTION, f"caption {text!r} describes a gallery of {len(produced)} images - dropped")


def parse_content(raw_html):
    """Convert a post's WordPress HTML body into ordered block specs, plus any warnings.

    Specs are ("text", html), ("image", {"src", "alt", "caption"}), ("video", {"url", "alt"}) or
    ("code", {"code": ...}); warnings are (kind, message) pairs so the caller can group them.
    Only the markup this export actually uses is recognised - everything else stays as rich text.
    """
    return ContentParser().parse(raw_html)


# ---------------------------------------------------------------------------
# Block specs -> pages, images and CSVs (all the I/O)
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Imports blog posts from the flat WordPress export XML (mozilla-blog-posts.xml) into a "
        "BlogIndexPage, creating BlogArticlePage children plus any Tag/Author snippets and images "
        "they reference. Writes a CSV mapping each post's old blog.mozilla.org URL to its new URL "
        "on this site, to hand to the blog.mozilla.org team so they can set up redirects on their end, "
        "and a second CSV listing every content warning against the post it came from."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Warnings raised while importing the current post, and how many of its images arrived
        # without alt text worth keeping.
        self.post_warnings = []
        self.images_without_alt = 0

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
        parser.add_argument(
            "--warnings-out",
            default="wordpress_import_warnings.csv",
            help="Path to write the per-post content warnings CSV (default: wordpress_import_warnings.csv). "
            "Warnings are easy to lose in the command output, so each one is also recorded here against "
            "the post it came from. An existing file at this path is overwritten, not appended to.",
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

        self.url_map_csv = IncrementalCsv(options["url_map_out"], ["wp_id", "old_url", "new_url"])
        self.warnings_csv = IncrementalCsv(options["warnings_out"], ["wp_id", "title", "old_url", "new_url", "type", "warning"])
        imported = skipped = failed = 0

        try:
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

                # Reset here rather than inside import_post, so a post that fails early cannot
                # inherit the previous post's warnings.
                self.post_warnings = []
                self.images_without_alt = 0
                try:
                    url_map_row = self.import_post(post, index_page, locale)
                except Exception as exc:
                    self.stderr.write(f"    ! failed to import {slug!r}: {exc}")
                    # A failed post is the most important thing to record: it has no page to
                    # inspect, so the CSV is the only trace of what went wrong.
                    self.record_warnings(post, new_url="", failure=(WARNING_FAILURE, f"post failed to import: {exc}"))
                    failed += 1
                    continue

                if url_map_row is not None:
                    self.url_map_csv.write(url_map_row)
                    self.record_warnings(post, new_url=url_map_row[2])
                imported += 1
        finally:
            self.url_map_csv.close()
            self.warnings_csv.close()

        if self.warnings_csv.count:
            self.stdout.write(f"Wrote {self.warnings_csv.count} warnings to {self.warnings_csv.path}")
        if self.url_map_csv.count:
            self.stdout.write(f"Wrote {self.url_map_csv.count} URL mappings to {self.url_map_csv.path}")

        self.stdout.write(f"Done. {imported} imported, {skipped} skipped, {failed} failed.")

    @transaction.atomic
    def import_post(self, post, index_page, locale):
        """Import one post in its own transaction, so a failure (e.g. a dead image URL)
        rolls back cleanly instead of leaving a half-written page behind."""
        slug = element_text(post, "Slug")
        title = element_text(post, "Title")

        content_specs, warnings = parse_content(element_text(post, "Content"))
        for kind, message in warnings:
            self.warn(kind, message)

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
        # ImageURL lists every image attached to the post, pipe-separated, with ImageTitle and the
        # other Image* fields as parallel lists. The hero image is the single URL in ImageFeatured,
        # which is the first of those, so its title is the first ImageTitle. A post whose
        # ImageFeatured is blank is imported without a hero image.
        image_title = element_text(post, "ImageTitle").split("|")[0].strip() or title
        # ImageAltText is the export's own alt text, and is often blank; the title occasionally
        # describes the image rather than naming the file, so it stands in as a second choice.
        image_alt = element_text(post, "ImageAltText").split("|")[0].strip()
        image = self.get_or_create_image(
            element_text(post, "ImageFeatured"),
            image_title,
            description=image_description(image_alt) or image_description(image_title),
        )
        content = self.materialize_content(content_specs, title)

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

        if self.images_without_alt:
            plural = "s" if self.images_without_alt > 1 else ""
            self.warn(
                WARNING_ALT_TEXT,
                f"{self.images_without_alt} image{plural} imported without alt text - add descriptions in the image library",
            )

        return (element_text(post, "ID"), element_text(post, "Permalink"), page.full_url)

    def materialize_content(self, specs, title):
        """Build the StreamField `content` from block specs, downloading the images they need.

        A captioned image becomes an Image + Caption block and an uncaptioned one a plain media
        image. A video becomes a media video block, whose required poster is the YouTube
        thumbnail and whose alt text is the caption, falling back to the post `title`. Images
        left inline in a text block become Wagtail image embeds.

        An image or poster that fails to download is skipped, so one dead URL doesn't lose the
        whole post.
        """
        blocks = []
        for block_type, value in specs:
            if block_type == "text":
                blocks.append(("text", self.import_inline_images(value, title)))
            elif block_type == "image":
                image = self.get_or_create_image(value["src"], value["alt"], description=value["alt"])
                if image is None:
                    continue
                image_value = {"image": image, "settings": {}}
                if value.get("caption"):
                    blocks.append(("image_caption", {"image": image_value, "caption": value["caption"]}))
                else:
                    blocks.append(("media", [("image", image_value)]))
            elif block_type == "video":
                alt = value["alt"] or title
                poster = self.get_or_create_image(youtube_poster_url(youtube_video_id(value["url"])), alt, description=alt)
                if poster is None:
                    # The block requires a poster, so there is nothing valid to write without one.
                    continue
                blocks.append(("media", [("video", {"video_url": value["url"], "alt": alt, "poster": poster})]))
            else:
                blocks.append((block_type, value))
        return blocks

    def import_inline_images(self, text_html, title):
        """Swap hotlinked <img> tags in rich text for Wagtail image embeds.

        An image inside prose - a list item, a sentence, a link - can't become a block of its own
        without breaking the text around it, so it stays in the rich text. Stored as an embed it
        is a managed image rather than a link back to blog.mozilla.org, and the 'image' rich text
        feature keeps it intact when an editor saves the page.
        """
        soup = BeautifulSoup(text_html, "html.parser")
        images = soup.find_all("img")
        if not images:
            return text_html

        for img in images:
            alt = image_description(img.get("alt", ""))
            image = self.get_or_create_image(img.get("src", ""), img.get("alt", "") or title, description=alt)
            if image is None:
                # Already warned. Leave the original tag: a hotlink still renders while the
                # source is up, which beats dropping the image outright.
                continue
            embed = soup.new_tag("embed")
            embed.attrs = {
                "embedtype": "image",
                "id": str(image.pk),
                "alt": alt,
                "format": "fullwidth",
            }
            img.replace_with(embed)

        return str(soup)

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

    def get_or_create_image(self, url, title, description=""):
        """Download `url` into an image, reusing one already stored under the same filename.

        `description` is Wagtail's alt text. It is only kept when it actually describes the
        image - see image_description - so a file name never ends up being read out.
        """
        url = url.strip()
        if not url:
            return None

        # Identify an asset by its source filename, not its title: titles are free WordPress
        # text that unrelated images often share, while the media URL's filename is reliable.
        filename = Path(urlparse(url).path).name or "image.jpg"
        title = title.strip() or filename

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

        response = self.download(url)
        if response is None:
            return None

        alt_text = image_description(description)
        if not alt_text:
            # Reported per post once the whole post is imported, so it is one line to act on
            # rather than one per image.
            self.images_without_alt += 1
        try:
            image = SpringfieldImage.objects.create(
                title=title,
                description=alt_text,
                file=ContentFile(response.content, name=filename),
            )
        except Exception as exc:
            # Saving computes the image's dimensions through ImageMagick, which gives up on some
            # files - a large animated GIF exhausts its pixel cache. One unusable image is worth
            # a warning, not the loss of the whole post.
            self.warn(WARNING_PROCESSING, f"could not process image {url} ({filesizeformat(len(response.content))}): {exc}")
            return None

        self.image_cache[filename] = image
        return image

    def download(self, url):
        """Fetch `url`, retrying with a widening gap, or warn and return None if it never answers."""
        last_exc = None
        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            try:
                response = requests.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < DOWNLOAD_ATTEMPTS:
                    time.sleep(2**attempt)  # 2s, then 4s

        self.warn(WARNING_DOWNLOAD, f"could not download image {url} after {DOWNLOAD_ATTEMPTS} attempts: {last_exc}")
        return None

    def parse_wp_date(self, text):
        """Parse a WordPress export Date (no timezone info) as wall-clock time in
        settings.TIME_ZONE (America/Los_Angeles), since that's where these dates originated."""
        parsed = parse_datetime(text)
        if parsed is None:
            return None
        return make_aware(parsed, get_default_timezone())

    def warn(self, kind, message):
        """Report a content warning: to stderr as the import runs, and to the warnings CSV."""
        self.stderr.write(f"    ! [{kind}] {message}")
        self.post_warnings.append((kind, message))

    def record_warnings(self, post, new_url, failure=None):
        """Write the current post's warnings to the CSV, paired with its URLs."""
        if self.dry_run:
            return
        wp_id = element_text(post, "ID")
        title = element_text(post, "Title")
        old_url = element_text(post, "Permalink")
        for kind, message in [*self.post_warnings, *([failure] if failure else [])]:
            self.warnings_csv.write((wp_id, title, old_url, new_url, kind, message))
