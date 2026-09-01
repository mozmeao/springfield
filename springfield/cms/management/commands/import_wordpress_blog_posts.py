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
- wordpress_url_map.csv: the old-URL -> new-URL map, to hand to the blog.mozilla.org team for
  redirects.
- wordpress_import_warnings.csv: the warnings, as a worklist of what needs a human afterward.
"""

import csv
import html
import re
import time
from io import BytesIO
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
from bs4 import BeautifulSoup, Comment, NavigableString, Tag as HtmlTag
from wagtail.models import Locale
from wagtail.utils.file import hash_filelike

from springfield.cms.models import (
    BlogArticleAuthor,
    BlogArticlePage,
    BlogAuthor,
    BlogIndexPage,
    BlogTag,
    BlogTopic,
    HeroStyle,
    SpringfieldImage,
)

# Older WordPress posts wrap inline images with a `[caption ...]<img ...> caption text[/caption]`
# shortcode, while newer (Gutenberg) ones use `<figure><img ...><figcaption>...</figcaption></figure>`.
# The shortcode is rewritten into the figure form so both take the same path through the parser.
CAPTION_SHORTCODE_RE = re.compile(r"\[caption[^\]]*\](.*?)\[/caption\]", re.DOTALL)
IMG_TAG_RE = re.compile(r"<img[^>]*>")

# The same split for videos: older posts wrap a bare video URL in an `[embed]` shortcode, newer
# ones in `<figure class="wp-block-embed">`.
EMBED_SHORTCODE_RE = re.compile(r"\[embed[^\]]*\](.*?)\[/embed\]", re.DOTALL)

# Layout wrappers WordPress puts around blocks (groups, media-and-text pairs, columns). They
# carry no meaning we keep, so the parser steps inside them to reach the figures they hold.
CONTAINER_TAGS = {"div", "section"}

# Elements that stand on their own in a post body. Everything else is inline, and a run of inline
# nodes is what wrap_bare_paragraphs collects into a paragraph.
BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "iframe",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
    "video",
}

BLANK_LINE_RE = re.compile(r"\n\s*\n")

# Media URLs go down often enough that one attempt isn't enough, with a widening gap between tries.
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_TIMEOUT_SECONDS = 60

# Hosts serving YouTube's generated thumbnails, whose file names carry no distinguishing part.
YOUTUBE_THUMBNAIL_HOSTS = {"img.youtube.com", "i.ytimg.com"}

# Warning kinds, recorded alongside each message so the CSV can be filtered by them.
WARNING_CAPTION = "caption"
WARNING_VIDEO = "video"
WARNING_EMBED = "embed"
WARNING_DOWNLOAD = "download"
WARNING_PROCESSING = "processing"
WARNING_ALT_TEXT = "alt-text"
WARNING_FAILURE = "failure"
WARNING_INLINE_IMAGE = "inline-image"
WARNING_AUTHOR = "author"

# WordPress bookkeeping that rides along in the Tags field: the export tool's own marker, a
# placement flag and WordPress's fallback bucket. None of them means anything to a reader, and
# every one of them would show on the article cards.
IGNORED_TAG_NAMES = {"export", "homepage", "uncategorized"}

# Hostnames that mean the URL map was generated somewhere only this machine can reach.
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "testserver"}

# Media files WordPress links an image to when "link to media file" is set. Such a link points at
# the copy on blog.mozilla.org and carries nothing once the image is ours, so it is dropped.
MEDIA_FILE_SUFFIXES = (".avif", ".gif", ".jpg", ".jpeg", ".png", ".svg", ".webp")

# Elements that hold an image somewhere a block can't go. The nearest of these around an image is
# what the inline-image warning names, rather than whatever layout wrapper is furthest out.
INLINE_IMAGE_CONTAINERS = ("a", "li", "p", "h2", "h3", "h4", "h5", "h6", "blockquote", "td")

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


def image_filename(url):
    """The name to store the download from `url` under.

    Normally the file's own name. Every YouTube thumbnail is called 'hqdefault.jpg', so the video
    id - the directory holding it - goes in front, which keeps posters apart in the image library.
    """
    path = Path(urlparse(url).path)
    name = path.name or "image.jpg"
    if urlparse(url).netloc.lower() in YOUTUBE_THUMBNAIL_HOSTS and path.parent.name:
        return f"{path.parent.name}-{name}"
    return name


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

    A YouTube watch URL keeps its query string, which is where the video id lives. Every other
    provider loses it: WordPress captured those from share links, so the query carries tracking -
    session ids, checksums, timestamps - rather than anything needed to reach the video.
    """
    parsed = urlparse(url)._replace(fragment="")
    if youtube_video_id(url) is None:
        parsed = parsed._replace(query="")
    return f'<p><a href="{html.escape(urlunparse(parsed), quote=True)}">Watch video</a></p>'


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


def rewrite_embed_shortcodes(raw_html):
    """Rewrite every `[embed]` shortcode as the embed figure Gutenberg would have produced.

    Older posts wrap a bare video URL in the shortcode where newer ones use
    `<figure class="wp-block-embed">`, so rewriting leaves the parser one shape to understand.
    Anything other than a URL keeps its place as plain text rather than being thrown away.
    """

    def replace(match):
        url = match.group(1).strip()
        if not url.startswith("http"):
            return url
        return f'<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">{url}</div></figure>'

    return EMBED_SHORTCODE_RE.sub(replace, raw_html)


def demote_h1_headings(raw_html):
    """Turn any `<h1>` in a post body into an `<h2>`.

    The page renders its title as the only h1 it should have, and h1 isn't one of the rich text
    features, so Draftail doesn't move such a heading down a level - it drops it to plain text
    the first time an editor saves. A few posts use h1 for every section heading they have.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    headings = soup.find_all("h1")
    if not headings:
        return raw_html
    for heading in headings:
        heading.name = "h2"
    return str(soup)


def wrap_bare_paragraphs(raw_html):
    """Wrap runs of bare text in `<p>`, the way WordPress does when it renders a classic post.

    Pre-Gutenberg posts carry no paragraph markup at all: paragraphs are separated by blank lines
    and WordPress adds the tags at render time (its `wpautop`). Rich text has no such step, so
    without this a third of these posts render as one unbroken block of text - and the first
    editor save fuses them for good, because Draftail keeps the words and drops the newlines.
    """
    soup = BeautifulSoup(f"<div>{raw_html}</div>", "html.parser")
    pieces = []
    paragraph = []

    def close_paragraph():
        joined = "".join(paragraph).strip()
        paragraph.clear()
        if joined:
            pieces.append(f"<p>{joined}</p>")

    for node in soup.div.contents:
        if isinstance(node, HtmlTag) and node.name in BLOCK_TAGS:
            close_paragraph()
            pieces.append(str(node))
        elif isinstance(node, NavigableString) and BLANK_LINE_RE.search(str(node)):
            # A blank line in bare text ends the paragraph being collected and starts the next.
            head, *rest = BLANK_LINE_RE.split(str(node))
            paragraph.append(head)
            close_paragraph()
            for between in rest[:-1]:
                paragraph.append(between)
                close_paragraph()
            paragraph.append(rest[-1])
        else:
            paragraph.append(str(node))

    close_paragraph()
    return "".join(pieces)


def relink_imported_posts(text_html, new_paths):
    """Point links at the imported copy of any post that is part of this same import.

    These posts cross-link heavily. A link left as it is sends the reader back to WordPress for a
    post that now lives here, so every blog.mozilla.org link whose last path segment matches an
    imported slug is rewritten. `new_paths` maps slug -> path on this site. Links to anything not
    in the import are left alone: that content isn't moving.
    """
    soup = BeautifulSoup(text_html, "html.parser")
    changed = False
    for anchor in soup.find_all("a", href=True):
        parsed = urlparse(anchor["href"])
        if not parsed.netloc.lower().endswith("blog.mozilla.org"):
            continue
        path = new_paths.get(parsed.path.rstrip("/").rsplit("/", 1)[-1])
        if path:
            anchor["href"] = path
            changed = True
    return str(soup) if changed else text_html


def unwrap_media_file_links(soup):
    """Drop every `<a>` that wraps an image only to link to the image's own file.

    That's WordPress's "link to media file" setting: a lightbox link to the full-size upload on
    blog.mozilla.org. Once the image is ours the link leads back to the old site, and an image
    inside a link cannot be represented in rich text - the editor pulls it out on the first save
    and leaves the link empty. Links that go somewhere real are left alone.
    """
    for anchor in soup.find_all("a", href=True):
        images = anchor.find_all("img")
        if len(images) != 1 or anchor.get_text(strip=True):
            continue
        if urlparse(anchor["href"]).path.lower().endswith(MEDIA_FILE_SUFFIXES):
            anchor.replace_with(images[0])


def image_only_paragraph(node):
    """Return the `<img>` a paragraph holds on its own, or None if it holds anything else.

    WordPress renders such a paragraph as a block-level image, so it becomes a real image block:
    that keeps the layout and, unlike an image embedded in rich text, survives an editor save.
    """
    if not isinstance(node, HtmlTag) or node.name != "p" or node.get_text(strip=True):
        return None
    images = node.find_all("img")
    if len(images) != 1 or node.find("a") is not None:
        return None
    return images[0]


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
        rewritten = rewrite_embed_shortcodes(rewrite_caption_shortcodes(raw_html))
        soup = BeautifulSoup(f"<div>{rewritten}</div>", "html.parser")
        unwrap_media_file_links(soup)
        self.process(soup.div.contents)
        self.flush_text()
        return self.specs, self.warnings

    def process(self, nodes):
        """Walk a run of sibling nodes, turning the ones we have blocks for into specs."""
        for node in nodes:
            if isinstance(node, Comment):
                continue
            name = getattr(node, "name", None)
            paragraph_image = image_only_paragraph(node)
            if name == "img":
                self.flush_text()
                self.specs.append(image_spec(node))
            elif paragraph_image is not None:
                self.flush_text()
                self.specs.append(image_spec(paragraph_image))
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
        """Close off the prose collected so far as a text spec, in paragraphs."""
        joined = "".join(str(node) for node in self.text_buffer).strip()
        self.text_buffer.clear()
        if joined:
            self.specs.append(("text", demote_h1_headings(wrap_bare_paragraphs(joined))))

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
        for img in node.find_all("img") if isinstance(node, HtmlTag) else []:
            # An image sharing a paragraph with prose, or sitting in a list item, a heading or a
            # link, can't become a block of its own without breaking what surrounds it. It is
            # imported as a rich text embed, which renders correctly but which the editor lifts
            # out of its container the first time someone saves the page.
            container = img.find_parent(INLINE_IMAGE_CONTAINERS)
            self.warn(
                WARNING_INLINE_IMAGE,
                f"image {img.get('src', '')} sits inside a <{container.name if container else node.name}> - "
                "kept in the text block, but editing the page will move it out of it",
            )
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
            f"self-hosted video {video.get('src', '')} cannot be imported into a video block - left inline in a text "
            "block, but <video> is not a rich text feature, so editing the page will drop it and leave only its caption. "
            "Re-host it on assets.mozilla.net to keep it",
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
        "BlogIndexPage, creating BlogArticlePage children plus any BlogTopic/BlogTag/BlogAuthor snippets and images "
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
        # slug -> path on this site, for every post in the export, so a link to one of them can be
        # rewritten whether or not it has been imported yet. Filled in by handle().
        self.new_paths = {}
        # Every person the export names, keyed by each form a byline takes. Filled in by handle().
        self.known_authors = {}

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

        # Built before importing anything, so a post can link to one that comes later in the file.
        self.new_paths = {
            element_text(post, "Slug"): f"{index_page.url}{element_text(post, 'Slug')}/" for post in posts if element_text(post, "Slug")
        }

        # Built before importing anything, so a byline on one post can be named by another's
        # owner record.
        self.known_authors = self.build_known_authors(posts)

        self.url_map_csv = IncrementalCsv(options["url_map_out"], ["wp_id", "old_url", "new_url"])
        self.warnings_csv = IncrementalCsv(options["warnings_out"], ["wp_id", "title", "old_url", "new_url", "type", "warning"])
        imported = skipped = failed = 0
        local_hostname = ""

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
                    hostname = urlparse(url_map_row[2]).hostname or ""
                    if hostname in LOCAL_HOSTNAMES:
                        local_hostname = hostname
                imported += 1
        finally:
            self.url_map_csv.close()
            self.warnings_csv.close()

        if self.warnings_csv.count:
            self.stdout.write(f"Wrote {self.warnings_csv.count} warnings to {self.warnings_csv.path}")
        if self.url_map_csv.count:
            self.stdout.write(f"Wrote {self.url_map_csv.count} URL mappings to {self.url_map_csv.path}")
            if local_hostname:
                # The map exists for the blog.mozilla.org team's redirects, and new_url comes from
                # the Wagtail Site record, so one generated here sends them to a machine of ours.
                self.stdout.write(
                    f"CAUTION: the new URLs point at {local_hostname!r}, which is only reachable locally. "
                    "Regenerate the map where the Site record holds the production hostname before handing it over."
                )

        counted = f"{imported} would be imported" if self.dry_run else f"{imported} imported"
        self.stdout.write(f"Done. {counted}, {skipped} skipped, {failed} failed.")

    @transaction.atomic
    def import_post(self, post, index_page, locale):
        """Import one post in its own transaction, so a failure (e.g. a dead image URL)
        rolls back cleanly instead of leaving a half-written page behind."""
        slug = element_text(post, "Slug")
        title = element_text(post, "Title")

        content_specs, warnings = parse_content(element_text(post, "Content"))
        for kind, message in warnings:
            self.warn(kind, message)

        categories = parse_categories(element_text(post, "Categories"))
        if not categories:
            raise ValueError(f"post {slug!r} has no Category - BlogArticlePage.topic is required and cannot be blank")

        # Everything past here writes or downloads. The checks above run in a dry run too, so a
        # preview reports the posts that would fail rather than only the content warnings.
        if self.dry_run:
            return None

        # topic is a single required BlogTopic; the first (most specific) category becomes the
        # topic and the rest join the post's tags, which are BlogTags.
        topic = self.get_or_create_snippet(BlogTopic, categories[0], locale)
        exported_tags = [name for name in element_text(post, "Tags").split("|") if name.strip() and name.strip().lower() not in IGNORED_TAG_NAMES]
        tags = [self.get_or_create_snippet(BlogTag, name, locale) for name in exported_tags + categories[1:]]
        authors = self.get_or_create_authors(post, locale)
        # ImageURL lists every image attached to the post, pipe-separated, with ImageTitle and the
        # other Image* fields as parallel lists. The hero image is the single URL in ImageFeatured,
        # which is the first of those, so its title is the first ImageTitle. Some posts leave
        # ImageFeatured blank while still attaching their header image, so the first ImageURL entry
        # stands in - it is the same entry the parallel lists describe. A post with neither is
        # imported without a hero image.
        hero_url = element_text(post, "ImageFeatured") or element_text(post, "ImageURL").split("|")[0].strip()
        image_title = element_text(post, "ImageTitle").split("|")[0].strip() or title
        # ImageAltText is the export's own alt text and is often blank. ImageDescription describes
        # the image by definition, so it comes next; the title only occasionally describes it
        # rather than naming the file, so it comes last.
        hero_fields = [element_text(post, field).split("|")[0].strip() for field in ("ImageAltText", "ImageDescription")]
        image = self.get_or_create_image(
            hero_url,
            image_title,
            description=next((image_description(value) for value in [*hero_fields, image_title] if image_description(value)), ""),
        )
        # The hero has no caption field on the page, so a caption in the export has nowhere to go.
        hero_caption = element_text(post, "ImageCaption").split("|")[0].strip()
        if hero_caption:
            self.warn(WARNING_CAPTION, f"hero image caption {hero_caption!r} has no field on the page - dropped")
        content = self.materialize_content(content_specs, title)

        page = BlogArticlePage(
            title=title,
            slug=slug,
            locale=locale,
            topic=topic,
            image=image,
            # An image hero style would fail validation for a post the export gave no featured image.
            hero_style=HeroStyle.STANDARD_IMAGE if image else HeroStyle.TEXT_ONLY,
            content=content,
            first_published_at=self.parse_wp_date(element_text(post, "Date")),
        )
        # sort_order is set here rather than left to modelcluster: export order is byline order.
        page.article_authors = [BlogArticleAuthor(author=author, sort_order=order) for order, author in enumerate(authors)]
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
                blocks.append(("text", self.import_inline_images(relink_imported_posts(value, self.new_paths), title)))
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
                    # The block requires a poster, and YouTube serves no thumbnail at all for a
                    # video that has since been deleted. Keep the reference as a link rather than
                    # letting the video fall out of the post.
                    blocks.append(("text", video_link(value["url"])))
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

    def build_known_authors(self, posts):
        """Map every byline form the export uses to the person's real name and email.

        `Authors` holds the published byline as either an email or a bare name-slug, never a
        display name, and the Author* fields describe the post's owner rather than its byline.
        One post's owner record is therefore what names that same person's byline on another
        post - so this is built from every post before any of them is imported.
        """
        known = {}
        for post in posts:
            name = f"{element_text(post, 'AuthorFirstName')} {element_text(post, 'AuthorLastName')}".strip()
            email = element_text(post, "AuthorUsername").strip()
            if not name:
                continue
            if email:
                known[email.lower()] = (name, email)
            known[slugify(name)] = (name, email)
        return known

    def get_or_create_author(self, name, email="", *, locale):
        """Fetch or create the BlogAuthor for `name`, keyed on the slug of that name.

        Keying on the slug is what lets a byline like `kim-bryant` and an owner record naming
        "Kim Bryant" land on one snippet, whichever the import meets first. BlogAuthor is
        translatable and unique per (slug, locale), so `locale` is required rather than
        defaulted - an author is only ever created in the locale being imported into.
        """
        name = name.strip()
        if not name:
            return None

        author, _ = BlogAuthor.objects.get_or_create(slug=slugify(name), locale=locale, defaults={"name": name, "email": email})
        return author

    def get_or_create_authors(self, post, locale):
        """Resolve the post's byline into BlogAuthors, in the order the export lists them.

        A byline no owner record names is someone the export describes nowhere: all it carries is
        a slug or an address, so that raw string becomes the snippet's name and a warning asks for
        a real one. A post with no byline at all falls back to its owner, the only person it names.
        """
        bylines = [byline.strip() for byline in element_text(post, "Authors").split("|") if byline.strip()]
        if not bylines:
            email = element_text(post, "AuthorUsername").strip()
            name = f"{element_text(post, 'AuthorFirstName')} {element_text(post, 'AuthorLastName')}".strip() or email
            owner = self.get_or_create_author(name, email, locale=locale)
            return [owner] if owner else []

        authors = []
        unnamed = []
        for byline in bylines:
            entry = self.known_authors.get(byline.lower()) or self.known_authors.get(slugify(byline))
            if entry is None:
                unnamed.append(byline)
                entry = (byline, "")
            author = self.get_or_create_author(*entry, locale=locale)
            if author:
                authors.append(author)

        if unnamed:
            self.warn(
                WARNING_AUTHOR,
                f"the export names no one for {'|'.join(unnamed)} - imported under that byline, "
                "so fill in the real name and email on the author snippet",
            )
        return authors

    def get_or_create_image(self, url, title, description=""):
        """Download `url` into an image, reusing one the library already holds.

        An asset is identified by its source URL, not its file name: WordPress names uploads per
        month, so unrelated posts routinely hold a different `image.png`, and every YouTube
        thumbnail is called `hqdefault.jpg`. Matching on the name collapsed those into one image.

        `description` is Wagtail's alt text. It is only kept when it actually describes the
        image - see image_description - so a file name never ends up being read out.
        """
        url = url.strip()
        if not url:
            return None

        if url in self.image_cache:
            return self.image_cache[url]

        filename = image_filename(url)
        title = title.strip() or filename

        response = self.download(url)
        if response is None:
            return None

        # Reuse a file the library already holds rather than storing the same bytes twice - the
        # same image served from two URLs, or a resumed run. The stored name is no guide: Django's
        # storage renames a file whose name is taken, so 'hero.jpg' becomes 'hero_A1b2c3.jpg' and
        # never matches again. The contents are what identify it, and Wagtail indexes their hash.
        existing = SpringfieldImage.objects.filter(file_hash=hash_filelike(BytesIO(response.content))).first()
        if existing is not None:
            self.image_cache[url] = existing
            return existing

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
                # Wagtail only fills this in for admin uploads, and it is what the lookup above
                # matches on, so a later run can recognise this file.
                file_hash=hash_filelike(BytesIO(response.content)),
            )
        except Exception as exc:
            # Saving computes the image's dimensions through ImageMagick, which gives up on some
            # files - a large animated GIF exhausts its pixel cache. One unusable image is worth
            # a warning, not the loss of the whole post.
            self.warn(WARNING_PROCESSING, f"could not process image {url} ({filesizeformat(len(response.content))}): {exc}")
            return None

        self.image_cache[url] = image
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
