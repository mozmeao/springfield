# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Bulk fixes for the blog posts imported from blog.mozilla.org by import_wordpress_blog_posts.

Each fix has a name and only runs when asked for with `--fix`:

- youtube-posters: a YouTube video block whose poster is the 4:3 `hqdefault.jpg` thumbnail the
  importer used gets YouTube's widescreen `maxresdefault.jpg` instead. A video with no widescreen
  thumbnail gets a 16:9 centre crop of the largest 4:3 one, which cuts away its black bars. A
  video that really is 4:3 keeps its poster.
- mozilla-byline: a post whose only author is "Mozilla" loses it, so the page shows no byline.
- author-names: authors named after a WordPress login (`bryan-johns`) are renamed from a
  slug,name CSV. Only the name changes: the importer matches authors on slug.
- seo-text: sets a post's Title tag (seo_title) and Meta description (search_description) from
  the "pages" list of a `--decisions` JSON file, as a page draft. An empty Title tag means the
  post's own title is used.
- link-fixes: replaces a link's address, or removes the link and keeps its text, from the "links"
  list of a `--decisions` JSON file, in body text and captions, as a page draft.
- image-text, video-alt, inline-alt: apply reviewed text from a `--decisions` JSON file. image-text
  sets an image's title, description (its alt text) and decorative flag in the image library,
  matched by file hash so one file works on every environment. video-alt sets a video block's alt
  text, which is what screen readers hear for a video. inline-alt copies an image's reviewed
  description into the alt text of each inline image in a post's rich text, which keeps its own.
  Images have no draft state, so image-text applies at once; the other two save page drafts.

Page fixes never publish. All the fixes a run makes to one page go into a single new draft
revision, built on the page's latest revision so earlier draft edits are kept, and that one
revision is what to revert from the page history to undo the run for that page. A live page is
left alone unless `--include-live` is passed, and even then only gets a draft. Authors are
snippets with draft state, and a rename is published straight away, since a draft name shows
nowhere.

Every fix checks the current state before changing anything, so a second run finds nothing left
to do. `--dry-run` reports the same changes, and downloads the same thumbnails to check them,
without writing to the database. Either way, one CSV row is written per change or skip.
"""

import csv
import html
import json
import re
import time
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import requests
from PIL import Image
from wagtail.models import Locale
from wagtail.rich_text import RichText
from wagtail.search import index as search_index
from wagtail.utils.file import hash_filelike

from springfield.blog.management.commands.import_wordpress_blog_posts import (
    DOWNLOAD_TIMEOUT_SECONDS,
    youtube_video_id,
    youtube_watch_url,
)
from springfield.blog.models import BlogArticlePage, BlogAuthor
from springfield.cms.models import SpringfieldImage

FIX_YOUTUBE_POSTERS = "youtube-posters"
FIX_MOZILLA_BYLINE = "mozilla-byline"
FIX_AUTHOR_NAMES = "author-names"
FIX_IMAGE_TEXT = "image-text"
FIX_VIDEO_ALT = "video-alt"
FIX_INLINE_ALT = "inline-alt"
FIX_SEO_TEXT = "seo-text"
FIX_LINKS = "link-fixes"
PAGE_FIXES = (FIX_YOUTUBE_POSTERS, FIX_MOZILLA_BYLINE, FIX_VIDEO_ALT, FIX_INLINE_ALT, FIX_SEO_TEXT, FIX_LINKS)
DECISION_FIXES = (FIX_IMAGE_TEXT, FIX_VIDEO_ALT, FIX_INLINE_ALT, FIX_SEO_TEXT, FIX_LINKS)
FIXES = (*PAGE_FIXES, FIX_AUTHOR_NAMES, FIX_IMAGE_TEXT)

# A link in rich text, with its attributes and its contents.
LINK_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.DOTALL)
HREF_RE = re.compile(r'\bhref="([^"]*)"')

# Wagtail's seo_title column. Search results show far fewer characters, but this is the hard
# limit Postgres enforces.
SEO_TITLE_MAX_LENGTH = 255

# An image embed in rich text, as Wagtail stores it: <embed alt="…" embedtype="image" … id="12"/>.
IMAGE_EMBED_RE = re.compile(r'<embed\b[^>]*\bembedtype="image"[^>]*>')
EMBED_ID_RE = re.compile(r'\bid="(\d+)"')
EMBED_ALT_RE = re.compile(r'\balt="([^"]*)"')

# Report actions.
CHANGED = "changed"
WOULD_CHANGE = "would change"
SKIPPED = "skipped"
FAILED = "failed"

# The thumbnail the importer used as every YouTube poster: '<id>-hqdefault.jpg', or with the
# suffix storage adds to a taken name ('…-hqdefault_AbC123.jpg'). Anchored to the end, so this
# command's own 16:9 crops ('<id>-hqdefault-16x9.jpg') don't match on a second run.
HQDEFAULT_RE = re.compile(r"hqdefault(_[A-Za-z0-9]+)?\.jpg$", re.IGNORECASE)

# Largest first. maxresdefault is the only widescreen one, and older videos lack it; sddefault and
# hqdefault are 4:3, with a 16:9 video letterboxed inside them.
YOUTUBE_THUMBNAILS = ("maxresdefault", "sddefault", "hqdefault")
WIDESCREEN_THUMBNAIL = YOUTUBE_THUMBNAILS[0]

# oEmbed reports the player's size, which follows the video's shape: 200x113 for 16:9, 200x150
# for 4:3. Anything taller than halfway between the two is treated as 4:3.
OEMBED_URL = "https://www.youtube.com/oembed"
FOUR_THREE_MIN_RATIO = (9 / 16 + 3 / 4) / 2

# A thumbnail whose brightest pixel is this dark is a black frame, which YouTube serves for a
# livestream that has ended. Swapping one black poster for another helps no one.
BLANK_THUMBNAIL_MAX_LUMINANCE = 40

# Wagtail's title column is 255 characters. SQLite doesn't enforce that, Postgres does.
IMAGE_TITLE_MAX_LENGTH = 255

# The BlogAuthor that stands for "no particular person". Matched on slug, like the importer.
MOZILLA_AUTHOR_SLUG = "mozilla"

REPORT_HEADER = ["fix", "slug", "page_id", "live", "action", "detail", "old", "new", "revision_id"]


def youtube_thumbnail_url(video_id, name):
    return f"https://img.youtube.com/vi/{video_id}/{name}.jpg"


def is_hqdefault_poster(image):
    return image is not None and bool(HQDEFAULT_RE.search(Path(image.file.name).name))


def rewrite_rich_text(draft, transform, include_captions=False):
    """Pass the HTML of each text block, and optionally each image caption, through `transform`,
    writing back only the ones it changed."""
    for index, block in enumerate(draft.content):
        if block.block_type == "text":
            source = block.value.source
            new_source = transform(source)
            if new_source != source:
                draft.content[index] = ("text", RichText(new_source))
        elif include_captions and block.block_type == "image_caption" and block.value.get("caption"):
            source = block.value["caption"].source
            new_source = transform(source)
            if new_source != source:
                block.value["caption"] = RichText(new_source)


def is_blank(content):
    with Image.open(BytesIO(content)) as image:
        return image.convert("L").getextrema()[1] <= BLANK_THUMBNAIL_MAX_LUMINANCE


def crop_to_widescreen(content):
    """Return the 16:9 centre of a 4:3 YouTube thumbnail as JPEG bytes, with its size.

    YouTube letterboxes a 16:9 video inside its 4:3 thumbnails, so the centre band is the picture
    and the bars above and below it are what gets cut.
    """
    with Image.open(BytesIO(content)) as image:
        width, height = image.size
        crop_height = round(width * 9 / 16)
        top = (height - crop_height) // 2
        cropped = image.convert("RGB").crop((0, top, width, top + crop_height))
        buffer = BytesIO()
        cropped.save(buffer, "JPEG", quality=90)
    return buffer.getvalue(), cropped.size


def clean_video_title(title):
    """YouTube titles separate a series name with a pipe, which reads badly as alt text, so it
    becomes a colon."""
    return " ".join(title.replace(" | ", ": ").split())[:IMAGE_TITLE_MAX_LENGTH]


class PosterPlan:
    """What to do about one video's poster, worked out once per video and shared by every block
    that shows it."""

    def __init__(self, video_id, *, image=None, content=None, filename="", title="", size=None, note=""):
        self.video_id = video_id
        # An image already in the library, or the bytes and name of one to create.
        self.image = image
        self.content = content
        self.filename = filename
        self.title = title
        self.size = size
        self.note = note

    @property
    def usable(self):
        return self.image is not None or self.content is not None

    def describe(self):
        if self.image is not None:
            return f"image {self.image.pk} ({self.image.title})"
        width, height = self.size
        return f"new image {self.filename} ({width}x{height}, {self.title!r})"


class Command(BaseCommand):
    help = (
        "Bulk fixes for blog posts imported from blog.mozilla.org: widescreen YouTube posters, the "
        "'Mozilla' byline, author names, image and video alt text, Title tags and Meta descriptions, "
        "and links. Post changes are saved as one draft per post and never published. Author renames "
        "are published, and image titles and alt text apply at once, since neither has drafts. Writes "
        "a CSV report. Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="append",
            choices=FIXES,
            required=True,
            dest="fixes",
            help="A fix to run. Repeat to run several in one pass.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing to the database.")
        parser.add_argument("--locale", default="en-US", help="Locale of the posts and authors to fix (default: en-US).")
        parser.add_argument(
            "--slug",
            action="append",
            dest="slugs",
            default=[],
            help="Only fix the post with this slug. Repeat for several. Default: every blog post in the locale.",
        )
        parser.add_argument(
            "--include-live",
            action="store_true",
            help="Also fix live pages. They still only get a draft revision, which someone then has to publish.",
        )
        parser.add_argument("--author-names", help="CSV with slug,name columns, for the author-names fix.")
        parser.add_argument(
            "--decisions",
            help="JSON file of reviewed changes, for the image-text, video-alt, inline-alt, seo-text and link-fixes fixes: "
            '{"images": [{"hash", "title", "description", "decorative"}], "videos": [{"slug", "video_url", "alt"}], '
            '"pages": [{"slug", "seo_title", "search_description"}], "links": [{"slug", "url", "action", "new_url"}]}.',
        )
        parser.add_argument(
            "--report-out",
            default="blog_fixes_report.csv",
            help="Path to write the per-change CSV report (default: blog_fixes_report.csv). An existing file is overwritten.",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.include_live = options["include_live"]
        fixes = list(dict.fromkeys(options["fixes"]))

        self.locale = Locale.objects.filter(language_code=options["locale"]).first()
        if self.locale is None:
            raise CommandError(f"No Locale found for language code {options['locale']!r}")

        author_names = None
        if FIX_AUTHOR_NAMES in fixes:
            if not options["author_names"]:
                raise CommandError(f"--fix {FIX_AUTHOR_NAMES} needs --author-names <csv>")
            author_names = self.read_author_names(options["author_names"])

        self.image_decisions, self.video_decisions, self.page_decisions, self.link_decisions = {}, {}, {}, {}
        if any(fix in DECISION_FIXES for fix in fixes):
            if not options["decisions"]:
                raise CommandError(f"--fix {'/'.join(fix for fix in fixes if fix in DECISION_FIXES)} needs --decisions <json>")
            self.read_decisions(options["decisions"])

        pages = BlogArticlePage.objects.filter(locale=self.locale).order_by("path")
        if options["slugs"]:
            pages = pages.filter(slug__in=options["slugs"])
            missing = set(options["slugs"]) - set(pages.values_list("slug", flat=True))
            if missing:
                raise CommandError(f"No {self.locale.language_code} blog post with slug {', '.join(sorted(missing))}")

        self.poster_plans = {}
        self.counts = {}
        # Written even when there is nothing to report, so a stale report from an earlier run is
        # never mistaken for this one. Flushed row by row, like the importer's CSVs.
        self.report_path = options["report_out"]
        self.report_rows = 0
        self.report_file = open(self.report_path, "w", newline="")
        self.report = csv.writer(self.report_file)
        self.report.writerow(REPORT_HEADER)
        prefix = "[dry-run] " if self.dry_run else ""
        try:
            page_fixes = [fix for fix in fixes if fix in PAGE_FIXES]
            if page_fixes:
                self.stdout.write(f"{prefix}Checking {pages.count()} {self.locale.language_code} blog posts for: {', '.join(page_fixes)}")
                pages_changed = sum(self.fix_page(page, page_fixes) for page in pages)
                saved = "would get" if self.dry_run else "got"
                self.stdout.write(f"{pages_changed} posts {saved} a new draft revision.")
            if author_names is not None:
                self.stdout.write(f"{prefix}Renaming authors from {options['author_names']}")
                for slug, name in author_names:
                    self.isolated(FIX_AUTHOR_NAMES, slug, self.rename_author, slug, name)
            # After the page fixes, so the posters youtube-posters just created are there to find.
            if FIX_IMAGE_TEXT in fixes:
                self.stdout.write(f"{prefix}Setting image text for {len(self.image_decisions)} images from {options['decisions']}")
                for file_hash, decision in self.image_decisions.items():
                    self.isolated(FIX_IMAGE_TEXT, "", self.set_image_text, file_hash, decision, detail=f"image with hash {file_hash}")
        finally:
            self.report_file.close()

        summary = ", ".join(f"{fix} {action}: {count}" for (fix, action), count in sorted(self.counts.items())) or "nothing to do"
        self.stdout.write(f"Done. {summary}.")
        self.stdout.write(f"Wrote {self.report_rows} rows to {self.report_path}")

    def isolated(self, fix, slug, function, *args, detail=""):
        """Run one author or image change in its own transaction, so a failure is reported and
        rolled back without stopping the rest of the run."""
        try:
            with transaction.atomic():
                function(*args)
        except Exception as exc:
            self.record(None, {"fix": fix, "slug": slug, "action": FAILED, "detail": f"{detail + ': ' if detail else ''}{type(exc).__name__}: {exc}"})

    # -----------------------------------------------------------------------
    # Pages
    # -----------------------------------------------------------------------

    def fix_page(self, page, fixes):
        """Run `fixes` on one page and save them together as one draft revision.

        Returns whether the page changed (or, in a dry run, would have).
        """
        draft = page.get_latest_revision_as_object()
        skip_live = page.live and not self.include_live
        # Whether this page will actually be saved, so a poster image is only created for a
        # revision that will use it.
        self.writing = not self.dry_run and not skip_live
        self.created_plans = []
        rows = []
        try:
            with transaction.atomic():
                for fix in fixes:
                    if fix == FIX_YOUTUBE_POSTERS:
                        rows += self.fix_youtube_posters(draft)
                    elif fix == FIX_MOZILLA_BYLINE:
                        rows += self.fix_mozilla_byline(draft)
                    elif fix == FIX_VIDEO_ALT:
                        rows += self.fix_video_alt(draft)
                    elif fix == FIX_INLINE_ALT:
                        rows += self.fix_inline_alt(draft)
                    elif fix == FIX_SEO_TEXT:
                        rows += self.fix_seo_text(draft)
                    elif fix == FIX_LINKS:
                        rows += self.fix_links(draft)

                changes = [row for row in rows if row["action"] == CHANGED]
                if not changes:
                    pass
                elif skip_live:
                    for row in changes:
                        row["action"] = SKIPPED
                        row["detail"] = f"live page, not changed (rerun with --include-live for a draft): {row['detail']}"
                    changes = []
                elif self.dry_run:
                    for row in changes:
                        row["action"] = WOULD_CHANGE
                    # Nothing has been written, but the in-memory draft has been edited; it is
                    # thrown away with the transaction.
                    transaction.set_rollback(True)
                else:
                    revision = draft.save_revision(log_action=True)
                    for row in changes:
                        row["revision_id"] = revision.pk
        except Exception as exc:
            # The images created for this page were rolled back with it.
            for plan in self.created_plans:
                plan.image = None
            rows = [{"fix": ",".join(fixes), "action": FAILED, "detail": f"{type(exc).__name__}: {exc}"}]
            changes = []

        for row in rows:
            self.record(page, row)
        return bool(changes) or any(row["action"] == WOULD_CHANGE for row in rows)

    def fix_youtube_posters(self, draft):
        rows = []
        for block in draft.content:
            if block.block_type != "media":
                continue
            for child in block.value:
                if child.block_type != "video":
                    continue
                video = child.value
                old_poster = video.get("poster")
                video_id = youtube_video_id(video.get("video_url") or "")
                if video_id is None or not is_hqdefault_poster(old_poster):
                    continue

                row = {"fix": FIX_YOUTUBE_POSTERS, "old": f"image {old_poster.pk} ({Path(old_poster.file.name).name})"}
                try:
                    plan = self.plan_poster(video_id)
                except requests.RequestException as exc:
                    # Not cached, so a later run tries again. The post's other fixes still apply.
                    rows.append({**row, "action": SKIPPED, "detail": f"{video_id}: couldn't get it from YouTube, rerun later ({exc})"})
                    continue
                if not plan.usable:
                    rows.append({**row, "action": SKIPPED, "detail": f"{video_id}: {plan.note}"})
                    continue
                if self.writing and plan.image is None:
                    plan.image = self.create_poster_image(plan)
                    self.created_plans.append(plan)
                row["new"] = plan.describe()
                row["detail"] = f"{video_id}: {plan.note}"
                rows.append({**row, "action": CHANGED})
                if plan.image is not None:
                    video["poster"] = plan.image
        return rows

    def fix_mozilla_byline(self, draft):
        authors = list(draft.article_authors.all())
        if [placement.author.slug for placement in authors] != [MOZILLA_AUTHOR_SLUG]:
            return []
        draft.article_authors = []
        return [{"fix": FIX_MOZILLA_BYLINE, "action": CHANGED, "detail": "removed the only author", "old": authors[0].author.name, "new": ""}]

    def fix_video_alt(self, draft):
        rows = []
        wanted = self.video_decisions.get(draft.slug, {})
        for block in draft.content:
            if block.block_type != "media":
                continue
            for child in block.value:
                video = child.value
                if child.block_type != "video" or video.get("video_url") not in wanted:
                    continue
                alt = wanted[video["video_url"]]
                if video.get("alt") == alt:
                    continue
                rows.append({"fix": FIX_VIDEO_ALT, "action": CHANGED, "detail": video["video_url"], "old": video.get("alt", ""), "new": alt})
                video["alt"] = alt
        return rows

    def fix_seo_text(self, draft):
        decision = self.page_decisions.get(draft.slug)
        if decision is None:
            return []
        rows = []
        for field, label in (("seo_title", "Title tag"), ("search_description", "Meta description")):
            old = getattr(draft, field) or ""
            if old == decision[field]:
                continue
            rows.append({"fix": FIX_SEO_TEXT, "action": CHANGED, "detail": label, "old": old, "new": decision[field] or "(use the post title)"})
            setattr(draft, field, decision[field])
        return rows

    def fix_links(self, draft):
        """Replace or remove the links reviewed for this post, in body text and image captions.

        Links are matched on their exact address, as stored, so a link the editor has already
        changed is left alone.
        """
        wanted = self.link_decisions.get(draft.slug)
        if not wanted:
            return []
        rows = []

        def replace(match):
            attrs, inner = match.groups()
            href = HREF_RE.search(attrs)
            url = html.unescape(href.group(1)) if href else None
            if url not in wanted:
                return match.group(0)
            action, new_url = wanted[url]
            if action == "unlink":
                rows.append({"fix": FIX_LINKS, "action": CHANGED, "detail": "removed the link, kept its text", "old": url, "new": ""})
                return inner
            rows.append({"fix": FIX_LINKS, "action": CHANGED, "detail": "new address", "old": url, "new": new_url})
            new_attrs = attrs[: href.start(1)] + html.escape(new_url, quote=True) + attrs[href.end(1) :]
            return f"<a{new_attrs}>{inner}</a>"

        rewrite_rich_text(draft, lambda source: LINK_RE.sub(replace, source), include_captions=True)
        return rows

    def fix_inline_alt(self, draft):
        """Give each inline image the alt text reviewed for it.

        Rich text keeps an inline image's alt text on the embed itself, not on the image, so the
        reviewed description has to be copied into the post. A decorative image gets empty alt.
        """
        rows = []

        def rewrite(source):
            ids = {int(found.group(1)) for tag in IMAGE_EMBED_RE.findall(source) if (found := EMBED_ID_RE.search(tag))}
            hashes = dict(SpringfieldImage.objects.filter(pk__in=ids).values_list("pk", "file_hash"))

            def replace(match):
                tag = match.group(0)
                image_id = EMBED_ID_RE.search(tag)
                decision = image_id and self.image_decisions.get(hashes.get(int(image_id.group(1))))
                if not decision:
                    return tag
                alt = "" if decision["decorative"] else decision["description"]
                old = EMBED_ALT_RE.search(tag)
                if old is not None and html.unescape(old.group(1)) == alt:
                    return tag
                new_attr = f'alt="{html.escape(alt, quote=True)}"'
                rows.append(
                    {
                        "fix": FIX_INLINE_ALT,
                        "action": CHANGED,
                        "detail": f"inline image {image_id.group(1)}",
                        "old": html.unescape(old.group(1)) if old else "",
                        "new": alt,
                    }
                )
                # Spliced in rather than passed to re.sub as a template, so a backslash in the text
                # stays a backslash.
                if old is None:
                    return tag.replace("<embed", f"<embed {new_attr}", 1)
                return tag[: old.start()] + new_attr + tag[old.end() :]

            return IMAGE_EMBED_RE.sub(replace, source)

        rewrite_rich_text(draft, rewrite)
        return rows

    # -----------------------------------------------------------------------
    # Image text
    # -----------------------------------------------------------------------

    def read_decisions(self, path):
        try:
            with open(path) as decisions_file:
                data = json.load(decisions_file)
        except (OSError, ValueError) as exc:
            raise CommandError(f"Could not read {path}: {exc}") from exc
        for number, entry in enumerate(data.get("images", []), start=1):
            file_hash = (entry.get("hash") or "").strip()
            title = (entry.get("title") or "").strip()
            description = (entry.get("description") or "").strip()
            decorative = bool(entry.get("decorative"))
            if not file_hash or not title or not (description or decorative):
                raise CommandError(f"{path} images entry {number}: needs a hash, a title, and a description unless decorative")
            if len(title) > IMAGE_TITLE_MAX_LENGTH:
                raise CommandError(f"{path} images entry {number}: title is longer than {IMAGE_TITLE_MAX_LENGTH} characters")
            self.image_decisions[file_hash] = {"title": title, "description": "" if decorative else description, "decorative": decorative}
        for number, entry in enumerate(data.get("videos", []), start=1):
            slug, url, alt = (entry.get("slug") or "").strip(), (entry.get("video_url") or "").strip(), (entry.get("alt") or "").strip()
            if not slug or not url or not alt:
                raise CommandError(f"{path} videos entry {number}: needs a slug, a video_url and alt text")
            self.video_decisions.setdefault(slug, {})[url] = alt
        for number, entry in enumerate(data.get("pages", []), start=1):
            slug = (entry.get("slug") or "").strip()
            seo_title = (entry.get("seo_title") or "").strip()
            description = (entry.get("search_description") or "").strip()
            if not slug or not description:
                raise CommandError(f"{path} pages entry {number}: needs a slug and a search_description")
            if len(seo_title) > SEO_TITLE_MAX_LENGTH:
                raise CommandError(f"{path} pages entry {number}: seo_title is longer than {SEO_TITLE_MAX_LENGTH} characters")
            self.page_decisions[slug] = {"seo_title": seo_title, "search_description": description}
        for number, entry in enumerate(data.get("links", []), start=1):
            slug, url, action = (entry.get("slug") or "").strip(), entry.get("url") or "", entry.get("action")
            new_url = (entry.get("new_url") or "").strip()
            if not slug or not url or action not in ("replace", "unlink") or (action == "replace" and not new_url):
                raise CommandError(f"{path} links entry {number}: needs a slug, a url, and action replace (with new_url) or unlink")
            self.link_decisions.setdefault(slug, {})[url] = (action, new_url)

    def planned_posters_by_hash(self):
        """The new posters this run planned, keyed by the hash of their bytes. Built once, after the
        page fixes have planned every poster."""
        if not hasattr(self, "_planned_posters_by_hash"):
            self._planned_posters_by_hash = {hash_filelike(BytesIO(plan.content)): plan for plan in self.poster_plans.values() if plan.content}
        return self._planned_posters_by_hash

    def set_image_text(self, file_hash, decision):
        row = {"fix": FIX_IMAGE_TEXT, "slug": "", "new": f"{decision['title']} | {decision['description'] or '(decorative)'}"}
        images = list(SpringfieldImage.objects.filter(file_hash=file_hash))
        if not images:
            # In a dry run the posters youtube-posters would create don't exist yet, but their
            # bytes are known, so the report can still say they will get this text.
            planned = self.planned_posters_by_hash().get(file_hash)
            if self.dry_run and planned is not None:
                self.record(None, {**row, "action": WOULD_CHANGE, "detail": f"new poster {planned.filename}", "old": "(new image)"})
                return
            detail = f"no image with hash {file_hash} (a new poster needs youtube-posters in the same run)"
            self.record(None, {**row, "action": SKIPPED, "detail": detail})
            return
        for image in images:
            current = (image.title, image.description, image.is_decorative)
            wanted = (decision["title"], decision["description"], decision["decorative"])
            if current == wanted:
                continue
            old = f"{image.title} | {image.description or '(none)'}"
            image_row = {**row, "detail": f"image {image.pk} ({Path(image.file.name).name})", "old": old}
            if self.dry_run:
                self.record(None, {**image_row, "action": WOULD_CHANGE})
                continue
            # A queryset update, because SpringfieldImage.save() regenerates every rendition and
            # none of them depend on the text. The search index is updated by hand instead.
            SpringfieldImage.objects.filter(pk=image.pk).update(title=wanted[0], description=wanted[1], is_decorative=wanted[2])
            image.title, image.description, image.is_decorative = wanted
            search_index.insert_or_update_object(image)
            self.record(None, {**image_row, "action": CHANGED})

    # -----------------------------------------------------------------------
    # YouTube posters
    # -----------------------------------------------------------------------

    def plan_poster(self, video_id):
        if video_id not in self.poster_plans:
            self.poster_plans[video_id] = self.build_poster_plan(video_id)
        return self.poster_plans[video_id]

    def build_poster_plan(self, video_id):
        """Pick the poster for one video: the widescreen thumbnail, else a 16:9 crop of a 4:3 one.

        Downloads in a dry run too, so the report says which videos have no widescreen thumbnail
        before anything is written.
        """
        oembed = self.fetch_oembed(video_id)
        if oembed is None:
            return PosterPlan(video_id, note="YouTube has no details for this video (deleted or private?), kept the current poster")
        if oembed["height"] / oembed["width"] >= FOUR_THREE_MIN_RATIO:
            return PosterPlan(video_id, note="4:3 video, kept the current poster")
        title = clean_video_title(oembed["title"])

        for name in YOUTUBE_THUMBNAILS:
            content = self.fetch(youtube_thumbnail_url(video_id, name))
            if content is None:
                continue
            if is_blank(content):
                return PosterPlan(video_id, note=f"YouTube's {name} is blank, kept the current poster: pick one by hand")
            if name == WIDESCREEN_THUMBNAIL:
                with Image.open(BytesIO(content)) as image:
                    size = image.size
                filename, note = f"{video_id}-{name}.jpg", f"widescreen {name}"
            else:
                content, size = crop_to_widescreen(content)
                filename, note = f"{video_id}-{name}-16x9.jpg", f"no widescreen thumbnail, 16:9 crop of {name}"

            # Reuse a file the library already holds, such as a poster uploaded by hand.
            existing = SpringfieldImage.objects.filter(file_hash=hash_filelike(BytesIO(content))).first()
            if existing is not None:
                return PosterPlan(video_id, image=existing, title=title, note=f"{note}, already in the library")
            return PosterPlan(video_id, content=content, filename=filename, title=title, size=size, note=note)

        return PosterPlan(video_id, note="YouTube has no thumbnails for this video, kept the current poster")

    def create_poster_image(self, plan):
        with transaction.atomic():
            return SpringfieldImage.objects.create(
                title=plan.title,
                # Wagtail's alt text. The video's own title is the best description of its poster.
                description=plan.title,
                file=ContentFile(plan.content, name=plan.filename),
                # Wagtail only fills this in for admin uploads, and it is what a later run matches on.
                file_hash=hash_filelike(BytesIO(plan.content)),
            )

    def fetch_oembed(self, video_id):
        # oEmbed answers 401 for a private video or one that can't be embedded, and 404 for one
        # that's gone: both mean there are no details to use.
        response = self.get(OEMBED_URL, params={"url": youtube_watch_url(video_id), "format": "json"}, missing=(401, 404))
        if response is None:
            return None
        data = response.json()
        if not data.get("width") or not data.get("height"):
            return None
        return data

    def fetch(self, url):
        response = self.get(url)
        return response.content if response is not None else None

    def get(self, url, params=None, missing=(404,)):
        """GET `url`, or None if it answers with one of the `missing` statuses.

        A missing thumbnail is a 404, which is an answer rather than a failure. Any other error,
        such as a 403 or 429 when YouTube is blocking or rate-limiting the server, raises, so the
        video is skipped for a later run instead of falling back to a worse thumbnail. Only a
        connection problem is retried.
        """
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)  # 1s, then 2s
                continue
            if response.status_code in missing:
                return None
            response.raise_for_status()
            return response

    # -----------------------------------------------------------------------
    # Authors
    # -----------------------------------------------------------------------

    def read_author_names(self, path):
        try:
            with open(path, newline="") as names_file:
                rows = list(csv.DictReader(names_file))
        except OSError as exc:
            raise CommandError(f"Could not read {path}: {exc}") from exc
        names = []
        for number, row in enumerate(rows, start=2):
            slug, name = (row.get("slug") or "").strip(), (row.get("name") or "").strip()
            if not slug or not name:
                raise CommandError(f"{path} line {number}: needs both a slug and a name")
            if len(name) > 255:
                raise CommandError(f"{path} line {number}: name is longer than 255 characters")
            names.append((slug, name))
        return names

    def rename_author(self, slug, name):
        row = {"fix": FIX_AUTHOR_NAMES, "slug": slug, "new": name}
        author = BlogAuthor.objects.filter(slug=slug, locale=self.locale).first()
        if author is None:
            self.record(None, {**row, "action": SKIPPED, "detail": f"no {self.locale.language_code} author with this slug"})
            return
        row["old"] = author.name
        if author.has_unpublished_changes:
            # Publishing the rename would publish someone's unfinished edit along with it.
            self.record(None, {**row, "action": SKIPPED, "detail": "author has an unpublished draft, rename it by hand"})
            return
        if author.name == name:
            return

        if self.dry_run:
            self.record(None, {**row, "action": WOULD_CHANGE, "detail": "rename and publish"})
            return
        with transaction.atomic():
            author.name = name
            revision = author.save_revision(log_action=True)
            revision.publish(log_action=True)
        self.record(None, {**row, "action": CHANGED, "detail": "renamed and published", "revision_id": revision.pk})

    # -----------------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------------

    def record(self, page, row):
        row = {key: "" for key in REPORT_HEADER} | row
        if page is not None:
            row.update(slug=page.slug, page_id=page.pk, live="yes" if page.live else "no")
        self.counts[(row["fix"], row["action"])] = self.counts.get((row["fix"], row["action"]), 0) + 1
        self.report.writerow([row[key] for key in REPORT_HEADER])
        self.report_file.flush()
        self.report_rows += 1

        change = f"{row['old']} -> {row['new']}" if row["new"] or row["old"] else ""
        line = f"  {row['action']}: {row['fix']} {row['slug']}: {row['detail']}"
        (self.stderr if row["action"] == FAILED else self.stdout).write(f"{line}{f' [{change}]' if change else ''}")
