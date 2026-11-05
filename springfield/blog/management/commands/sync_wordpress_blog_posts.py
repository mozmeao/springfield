# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Import new blog.mozilla.org posts from a reviewed sync file: check everything first, then build each page complete."""

import copy
import csv
import hashlib
from datetime import UTC
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

import requests
from bs4 import BeautifulSoup
from defusedxml import ElementTree
from wagtail.models import Locale, Site
from wagtail.utils.file import hash_filelike

from springfield.blog import wordpress_sync_check as checks, wordpress_translations as alignment
from springfield.blog.management.commands import (
    fix_imported_blog_posts as fixer,
    import_wordpress_blog_posts as importer,
    import_wordpress_blog_translations as translations,
)
from springfield.blog.models import BlogArticleAuthor, BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTag, BlogTopic, HeroStyle
from springfield.blog.wordpress_sync import SyncFileError, imported_posts, is_local_image, read_sync_file, text
from springfield.cms.models import SpringfieldImage

PUBLIC_HOST = "https://www.firefox.com"

CREATED = "created"
WOULD_CREATE = "would create"
SKIPPED = "skipped"
FAILED = "failed"
NOT_IMPORTED = "not imported"
CHANGED = "changed"
WOULD_CHANGE = "would change"

REPORT_HEADER = ["slug", "locale", "action", "page_id", "url", "wordpress_url", "detail"]
WARNINGS_HEADER = ["slug", "locale", "type", "warning"]
CHECK_HEADER = ["slug", "locale", "check", "result", "expected", "found"]
REDIRECTS_HEADER = [
    "old_url",
    "title",
    "publish_date",
    "author",
    "categories",
    "tags",
    "locale",
    "is_firefox_related",
    "migrated",
    "new_url",
    "firefox_signal",
    "wp_id",
    "slug",
    "has_export_tag",
    "in_rest_api",
]


class StopRun(Exception):
    """A problem found before any write: the whole run stops."""


def file_hash(content):
    return hash_filelike(BytesIO(content))


def image_text(decision):
    """The library title, description and decorative flag a sync file images entry asks for."""
    decorative = bool(decision.get("decorative"))
    return {"title": text(decision["title"]), "description": "" if decorative else text(decision.get("description")), "decorative": decorative}


def page_path(page):
    return page.get_url_parts()[2]


class Output:
    """The run's output folder; every file is written, even empty, so an old one is never mistaken for this run."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.files = []
        self.report = self.open_csv("report.csv", REPORT_HEADER)
        self.warnings = self.open_csv("warnings.csv", WARNINGS_HEADER)
        self.checks = self.open_csv("check.csv", CHECK_HEADER)
        self.redirects = self.open_csv("redirects.csv", REDIRECTS_HEADER)
        self.hand_steps = []

    def open_csv(self, name, header):
        csv_file = open(self.folder / name, "w", newline="")
        self.files.append(csv_file)
        writer = csv.DictWriter(csv_file, fieldnames=header, restval="")
        writer.writeheader()
        csv_file.flush()
        return writer, csv_file

    def write(self, target, row):
        writer, csv_file = target
        writer.writerow({key: value for key, value in row.items() if key in writer.fieldnames})
        csv_file.flush()

    def close(self, summary, dry_run):
        for csv_file in self.files:
            csv_file.close()
        marker = "**Dry run: nothing was written.**\n\n" if dry_run else ""
        (self.folder / "summary.md").write_text(f"# Blog sync summary\n\n{marker}{summary}\n")
        pages = {}
        for slug, step in self.hand_steps:
            pages.setdefault(slug, []).append(step)
        pages["All pages"] = ["Add the rows in `redirects.csv` to the redirects list and open a PR", "Spot check each new page"]
        sections = "\n\n".join(f"## {slug}\n\n" + "\n".join(f"- [ ] {step}" for step in steps) for slug, steps in pages.items())
        (self.folder / "hand-steps.md").write_text(f"# Hand steps\n\n{marker}{sections}\n")


class SyncFixer(fixer.Command):
    """The fixer's page and image code, with its report rows kept for the sync's own report."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []

    def record(self, page, row):
        self.rows.append(row)


class SyncImporter(importer.Command):
    """The importer's block and image code, with widescreen posters and reviewed alt text per image."""

    def __init__(self, *args, fixer_command, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixer = fixer_command
        self.fetched = {}
        self.created_plans = []

    def fetch_image(self, url):
        if url not in self.fetched:
            self.fetched[url] = super().fetch_image(url)
        return self.fetched[url]

    def get_or_create_youtube_poster(self, video_id, alt):
        try:
            plan = self.fixer.plan_poster(video_id)
        except requests.RequestException:
            plan = None
        if plan is None or not plan.usable:
            poster = super().get_or_create_youtube_poster(video_id, alt)
            if poster is None:
                raise ValueError(f"no poster from YouTube for video {video_id}: rerun, or take it out of the post if it was deleted")
            return poster
        if plan.image is None:
            plan.image = self.fixer.create_poster_image(plan)
            self.created_plans.append(plan)
        return plan.image

    def forget_post_images(self):
        super().forget_post_images()
        for plan in self.created_plans:
            plan.image = None
        self.created_plans = []

    def materialize_content(self, specs, title):
        blocks = []
        for block_type, value in specs:
            if block_type == "image":
                image = self.get_or_create_image(value["src"], value["title"], description=value["description"])
                if image is None:
                    continue
                image_value = {"image": image, "image_alt": value["image_alt"], "settings": {}}
                if value.get("caption"):
                    caption = importer.relink_imported_posts(value["caption"], self.new_paths)
                    blocks.append(("image_caption", {"image": image_value, "caption": caption}))
                else:
                    blocks.append(("media", [("image", image_value)]))
            elif block_type == "animation":
                if value.get("poster_file"):
                    poster = self.get_or_create_file_image(value["poster_file"], value["alt"])
                else:
                    poster = self.get_or_create_image(value["poster_url"], value["alt"], description=value["alt"])
                if poster is None:
                    raise ValueError(f"could not download the animation poster {value['poster_url']}")
                animation = {"video_url": value["video_url"], "poster": poster, "alt": value["alt"], "playback": "autoplay_loop"}
                blocks.append(("media", [("animation", animation)]))
            else:
                blocks += super().materialize_content([(block_type, value)], title)
        return blocks

    def get_or_create_file_image(self, path, title):
        """An image for a local file, reused by its hash."""
        if str(path) in self.image_cache:
            return self.image_cache[str(path)]
        content = Path(path).read_bytes()
        digest = file_hash(content)
        image = SpringfieldImage.objects.filter(file_hash=digest).first()
        if image is None:
            image = SpringfieldImage.objects.create(title=title, description=title, file=ContentFile(content, name=Path(path).name), file_hash=digest)
        self.cache_image(str(path), image)
        return image

    def import_inline_images(self, text_html, title):
        soup = BeautifulSoup(text_html, "html.parser")
        images = soup.find_all("img")
        if not images:
            return text_html
        for img in images:
            alt = img.get("data-alt", "")
            image = self.get_or_create_image(img.get("src", ""), img.get("data-title", "") or title, description=img.get("data-description", ""))
            if image is None:
                continue
            embed = soup.new_tag("embed")
            embed.attrs = {"embedtype": "image", "id": str(image.pk), "alt": alt, "format": "fullwidth"}
            img.replace_with(embed)
        return str(soup)


class SyncTranslator(translations.Command):
    """The translations code, with the WordPress hero swapped in before the translation is published."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heroes = {}

    def before_publish(self, translated_page, row, key):
        hero = self.heroes.get(key)
        if hero is None:
            return
        note = swap_translation_hero(translated_page, self, prefetched=hero["content"], expected_hash=hero["hash"], alt=hero["alt"])
        row["hero"] = note


def wordpress_translation(translator, language, wp_id):
    """A WordPress post's featured image bytes (None if it has none) and body HTML, read through the REST API."""
    base = f"{translator.wordpress_url}/{language}/wp-json/wp/v2"
    response = translator.get(f"{base}/posts/{wp_id}", params={"_fields": "featured_media,content"})
    post = response.json() if response is not None else {}
    body = (post.get("content") or {}).get("rendered", "")
    if not post.get("featured_media"):
        return None, body
    media = translator.get(f"{base}/media/{post['featured_media']}", params={"_fields": "source_url"})
    url = media.json().get("source_url") if media is not None else None
    content = translator.fetch(url) if url else None
    if content is None:
        raise requests.RequestException(f"could not download the featured image {url or '(no URL)'}")
    return content, body


def swap_translation_hero(page, translator, *, expected_hash, alt, prefetched=None, language="", wp_id=None):
    """Give `page` the WordPress translation's own featured image and reviewed alt, without saving it."""
    content = prefetched if prefetched is not None else wordpress_translation(translator, language, wp_id)[0]
    if content is None:
        raise ValueError("the WordPress translation has no featured image")
    found = file_hash(content)
    if found != expected_hash:
        raise ValueError(f"the WordPress featured image changed: expected hash {expected_hash}, found {found}")
    image = SpringfieldImage.objects.filter(file_hash=found, description=alt).first()
    if image is None and not translator.dry_run:
        collection = page.image.collection if page.image else None
        image = translator.create_image(alt[:255], alt, collection, content, f"hero-{found[:12]}.{image_extension(content)}")
        if image is None:
            raise ValueError("could not save the WordPress featured image")
    note = "hero swapped to the WordPress image" if image else "hero would be swapped to the WordPress image"
    if image is not None:
        page.image = image
        page.image_alt = alt
    if page.listing_image_id:
        note += "; its listing image is set and was left alone"
    return note


def image_extension(content):
    signatures = {b"\x89PNG": "png", b"GIF8": "gif", b"RIFF": "webp"}
    return next((extension for signature, extension in signatures.items() if content.startswith(signature)), "jpg")


class Command(BaseCommand):
    help = (
        "Imports new blog.mozilla.org posts from a reviewed sync file and the WordPress export XML: each English page "
        "is built complete and published once, then its de/fr translations, then reports go to the output folder. "
        "Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument("sync_file", help="The reviewed sync.json.")
        parser.add_argument("--export", help="The WordPress export XML holding the posts to import.")
        parser.add_argument("--dry-run", action="store_true", help="Read and check everything, and report what would happen, without writing.")
        parser.add_argument("--check-only", action="store_true", help="Only check the synced pages against the sync file and export.")
        parser.add_argument("--fix-translation-heroes", action="store_true", help="Only give existing translations their hero_fixes heroes.")
        parser.add_argument("--out", help="Output folder (default: blog-sync-<sync>/). Its files are overwritten.")
        parser.add_argument("--locale", default="en-US", help="Locale of the English posts (default: en-US).")
        parser.add_argument("--index-slug", default="blog", help="Slug of the blog index (default: blog).")
        parser.add_argument("--wordpress-url", help="WordPress site to read from (default: the sync file's wordpress_url).")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"] or options["check_only"]
        sync_path = Path(options["sync_file"])
        self.out = Output(options["out"] or f"blog-sync-{sync_path.stem}")
        self.counts = {}
        self.created = set()
        self.failed = 0
        self.failed_checks = 0
        self.stopped = []
        self.options = options
        try:
            try:
                self.run(sync_path)
            except (SyncFileError, StopRun) as exc:
                self.stopped = exc.errors if isinstance(exc, SyncFileError) else [str(exc)]
        finally:
            self.out.close(self.summary(sync_path), self.dry_run)
        if self.stopped:
            raise CommandError("Stopped before writing anything:\n" + "\n".join(self.stopped))
        if self.failed:
            raise CommandError(f"{self.failed} failed: see {self.out.folder / 'report.csv'}, then rerun")
        # Only --check-only exits non-zero on a failed check: a placeholder fails until it's replaced by hand.
        if self.options["check_only"] and self.failed_checks:
            raise CommandError(f"{self.failed_checks} checks failed: see {self.out.folder / 'check.csv'}")

    def run(self, sync_path):
        self.data = read_sync_file(sync_path)
        self.poster_file = None
        poster = (self.data.get("placeholder") or {}).get("poster_url")
        if is_local_image(poster):
            self.poster_file = sync_path.parent / poster
            if not self.poster_file.exists():
                raise StopRun(f"placeholder: poster file not found: {self.poster_file}")
        self.wordpress_url = (self.options["wordpress_url"] or self.data.get("wordpress_url") or translations.DEFAULT_WORDPRESS_URL).rstrip("/")
        self.fixer = SyncFixer(stdout=self.stdout, stderr=self.stderr)
        self.fixer.start_run(dry_run=self.dry_run, writing=not self.dry_run)
        self.importer = SyncImporter(stdout=self.stdout, stderr=self.stderr, fixer_command=self.fixer)
        self.importer.start_run(dry_run=self.dry_run, new_paths={})
        self.translator = SyncTranslator(stdout=self.stdout, stderr=self.stderr)
        self.translator.start_run(dry_run=self.dry_run, wordpress_url=self.wordpress_url, corrections={}, image_pairs={}, skip=set())
        self.check_environment()
        if self.options["fix_translation_heroes"]:
            self.fix_translation_heroes()
            return
        if not self.options["export"]:
            raise StopRun("--export is needed (only --fix-translation-heroes runs without it)")
        for post in self.data["posts"]:
            if not post.get("import") and not self.options["check_only"]:
                self.report(slug=post.get("wp_slug", ""), action=NOT_IMPORTED, detail=f"not imported: {post.get('note', '')}")
        self.plans = [self.plan_post(post) for post in imported_posts(self.data)]
        self.importer.new_paths = self.new_paths()
        if self.options["check_only"]:
            pages = [self.existing_page(plan["post"]) for plan in self.plans]
        else:
            pages = [self.sync_post(plan) for plan in self.plans]
            for plan, page in zip(self.plans, pages):
                self.sync_translations(plan, page)
        for plan, page in zip(self.plans, pages):
            self.check_post(plan, page)

    # -----------------------------------------------------------------------
    # Checking everything before writing
    # -----------------------------------------------------------------------

    def check_environment(self):
        self.locale = Locale.objects.filter(language_code=self.options["locale"]).first()
        if self.locale is None:
            raise StopRun(f"no Locale {self.options['locale']!r}")
        self.index = BlogIndexPage.objects.filter(locale=self.locale, slug=self.options["index_slug"]).first()
        if self.index is None:
            raise StopRun(f"no {self.locale.language_code} blog index with slug {self.options['index_slug']!r}")
        self.translation_locales = {locale.language_code: locale for locale in Locale.objects.filter(language_code__in=("de", "fr"))}
        errors = [f"no Locale {code!r}" for code in ("de", "fr") if code not in self.translation_locales]
        self.topics = {
            topic.slug: topic for topic in BlogTopic.objects.filter(locale=self.locale, live=True, slug__in=[term.slug for term in fixer.TOPICS])
        }
        self.tags = {tag.slug: tag for tag in BlogTag.objects.filter(locale=self.locale, live=True, slug__in=[term.slug for term in fixer.TAGS])}
        errors += [f"topic {term.slug!r} isn't published in {self.locale.language_code}" for term in fixer.TOPICS if term.slug not in self.topics]
        errors += [f"tag {term.slug!r} isn't published in {self.locale.language_code}" for term in fixer.TAGS if term.slug not in self.tags]
        self.authors = {author.slug: author for author in BlogAuthor.objects.filter(locale=self.locale)}
        for post in imported_posts(self.data):
            for author in post.get("authors") or []:
                if text(author.get("slug")) and author["slug"] not in self.authors:
                    errors.append(f"post {post['wp_slug']}: authors: no {self.locale.language_code} author {author['slug']!r}")
                existing = self.authors.get(slugify(text(author.get("new"))))
                if text(author.get("new")) and existing and existing.name.casefold() != text(author["new"]).casefold():
                    errors.append(f"post {post['wp_slug']}: authors: {author['new']!r} would take the slug of {existing.name!r}")
        if errors:
            raise StopRun("\n".join(errors))

    def read_export(self):
        if not hasattr(self, "export_posts"):
            path = Path(self.options["export"])
            if not path.exists():
                raise StopRun(f"export not found: {path}")
            posts = ElementTree.parse(path).getroot().findall("post")
            # The export labels its ID element "ID" or "id", depending on how the export is set up.
            self.export_posts = {importer.element_text(post, "ID") or importer.element_text(post, "id"): post for post in posts}
        return self.export_posts

    def plan_post(self, post):
        """Everything needed to build one post, after checking every image and translation against the sync file."""
        export_post = self.read_export().get(str(post["wp_id"]))
        where = f"post {post['wp_slug']}"
        if export_post is None:
            raise StopRun(f"{where} (wp_id {post['wp_id']}) is not in the export")
        images = {image["hash"]: image for image in self.data.get("images") or []}
        alt_by_position = {entry["position"]: entry for entry in post.get("image_alt") or []}
        media = {item["src"]: item for item in post.get("media") or []}
        placeholder = self.data.get("placeholder") or {}
        specs, warnings = importer.parse_content(importer.element_text(export_post, "Content"), video_blocks=True)
        body, used_media, errors, position = [], set(), [], 0

        def decide(src):
            """The decision for one body image, by its file's hash."""
            nonlocal position
            position += 1
            response, failure = self.importer.fetch_image(src)
            if response is None:
                errors.append(f"{where}: could not download image {src} (position {position}): {failure}")
                return None
            found = file_hash(response.content)
            decision = images.get(found)
            if decision is None:
                errors.append(f"{where}: image {src} (position {position}) has hash {found}, which the sync file has no images entry for")
                return None
            chosen = alt_by_position.get(position)
            if chosen and chosen["hash"] != found:
                errors.append(f"{where}: image_alt position {position} expects hash {chosen['hash']}, the export has {found} ({src})")
            library = image_text(decision)
            alt = text(chosen.get("alt")) if chosen and text(chosen.get("alt")) else library["description"]
            entry = {"position": position, "src": src, "hash": found, "alt": alt, **library}
            body.append(entry)
            return entry

        def animation(item):
            used_media.add(item["src"])
            webm = text(item.get("webm_url")) or placeholder.get("webm_url", "")
            poster = text(item.get("poster_url")) or placeholder.get("poster_url", "")
            value = {"video_url": webm, "poster_url": poster, "alt": item["alt"], "src": item["src"], "placeholder": not item.get("webm_url")}
            if value["placeholder"] and self.poster_file:
                value["poster_file"] = str(self.poster_file)
            return ("animation", value)

        planned = []
        for block_type, value in specs:
            if block_type == "image":
                item = media.get(value["src"]) or media.get(translations.Command.full_size_url(value["src"]))
                if item and item["kind"] == "gif":
                    position += 1
                    body.append({"position": position, "src": value["src"], "hash": None, "alt": item["alt"]})
                    planned.append(animation(item))
                    continue
                entry = decide(value["src"])
                if entry:
                    planned.append(("image", {**value, **entry, "image_alt": entry["alt"]}))
            elif block_type == "text":
                soup = BeautifulSoup(value, "html.parser")
                for img in soup.find_all("img"):
                    if media.get(img.get("src", "")):
                        errors.append(f"{where}: media {img['src']} sits inside text, so it can't become an Animation block: untick it")
                    entry = decide(img.get("src", ""))
                    if entry:
                        img["data-alt"], img["data-title"], img["data-description"] = entry["alt"], entry["title"], entry["description"]
                        img["data-hash"] = entry["hash"]
                planned.append(("text", str(soup) if soup.find("img") else value))
            elif block_type == "video_file":
                item = media.get(value["src"])
                if item is None:
                    errors.append(f"{where}: self-hosted video {value['src']} has no media entry")
                    continue
                planned.append(animation(item))
                if value["caption"]:
                    planned.append(("text", value["caption"]))
            else:
                planned.append((block_type, value))
        errors += [f"{where}: media {src} isn't in the post" for src in media if src not in used_media]
        errors += [f"{where}: image_alt position {number} has no image" for number in alt_by_position if number > position]

        hero = post["hero"]
        hero_entry = None
        if hero["image"] == "featured":
            url = importer.element_text(export_post, "ImageFeatured")
            response, failure = self.importer.fetch_image(url) if url else (None, "the export has no ImageFeatured")
            found = file_hash(response.content) if response is not None else None
            if found != hero["hash"]:
                errors.append(f"{where}: hero image changed: expected hash {hero['hash']}, found {found or failure} ({url})")
            hero_entry = {"src": url, "hash": hero["hash"]}
        elif hero["image"] == "body":
            hero_entry = next((entry for entry in body if entry["hash"] == hero["hash"]), None)
            if hero_entry is None:
                errors.append(f"{where}: hero.hash {hero['hash']} is not an image in the post")
        if hero.get("drop_body_duplicate"):
            first = next((spec for spec in planned if spec[0] == "image"), None)
            if first is None or first[1]["hash"] != hero.get("hash"):
                errors.append(
                    f"{where}: drop_body_duplicate is set, but the first image block isn't the hero ({first[1]['hash'] if first else 'none'})"
                )
            else:
                planned.remove(first)
        hero_video = None
        if hero.get("style") == "video":
            hero_video = next((spec for spec in planned if spec[0] == "video"), None)
            if hero_video is None:
                errors.append(f"{where}: hero.style is video, but the post has no YouTube video")
            else:
                planned.remove(hero_video)

        translations_plan = {}
        for translation in post.get("translations") or []:
            if translation.get("import"):
                translations_plan[translation["locale"]] = self.plan_translation(post, translation, errors)
        if errors:
            raise StopRun("\n".join(errors))
        return {
            "post": post,
            "export": export_post,
            "specs": planned,
            "warnings": warnings,
            "body": body,
            "hero": hero_entry,
            "hero_video": hero_video,
            "images": images,
            "translations": translations_plan,
            "hand_steps": self.placeholder_steps(post, planned),
            "expected": self.expected(post, planned, hero_entry, hero_video, images),
        }

    def expected(self, post, specs, hero_entry, hero_video, images):
        """What the check compares an English page with, from the sync file and the export."""
        body, alts = [], []
        for block_type, value in specs:
            if block_type == "image":
                body.append(value["hash"])
                alts.append(value["image_alt"])
            elif block_type == "animation":
                body.append(checks.ANIMATION)
            elif block_type == "text":
                for img in BeautifulSoup(value, "html.parser").find_all("img"):
                    body.append(img.get("data-hash"))
                    alts.append(img.get("data-alt", ""))
        hero_alt = ""
        if hero_entry is not None:
            hero_alt = text(post["hero"].get("alt")) or image_text(images[hero_entry["hash"]])["description"]
        return {
            "hero_hash": hero_entry["hash"] if hero_entry else None,
            "body": body,
            "hero_alt": hero_alt,
            "alts": alts,
            "youtube": [importer.youtube_video_id(value["url"]) for block_type, value in specs if block_type == "video"],
            "hero_video": [importer.youtube_video_id(hero_video[1]["url"])] if hero_video else [],
            "placeholder_url": (self.data.get("placeholder") or {}).get("webm_url"),
            "topic": post["topic"],
            "tags": sorted(post.get("tags") or []),
            "search text": (text(post.get("seo_title")), text(post["search_description"])),
            "byline": [text(author.get("slug")) or slugify(author["new"]) for author in post.get("authors") or []],
            "rss": "excluded" if post.get("exclude_from_rss") else "included",
        }

    def plan_translation(self, post, translation, errors):
        where = f"post {post['wp_slug']} {translation['locale']}"
        hero = translation.get("hero") or {}
        try:
            content, body_html = wordpress_translation(self.translator, translation["locale"], translation["wp_id"])
        except requests.RequestException as exc:
            errors.append(f"{where}: could not read the translation from WordPress: {exc}")
            return None
        found = file_hash(content) if content else None
        if text(hero.get("hash")) and found != hero["hash"]:
            errors.append(f"{where}: hero image changed: expected hash {hero['hash']}, found {found or 'no featured image'}")
        # With no hero of its own on WordPress, the translation keeps the English one.
        elif not text(hero.get("hash")) and found and post["hero"]["image"] == "featured" and found != post["hero"]["hash"]:
            english = post["hero"]["hash"]
            errors.append(f"{where}: the WordPress hero ({found}) differs from the English one ({english}): give the translation a hero")
        body = []
        for item in alignment.media(body_html):
            if item.kind == "image":
                image = self.translator.fetch(self.translator.full_size_url(item.source)) or self.translator.fetch(item.source)
                body.append(file_hash(image) if image else None)
        expected_hero = text(hero.get("hash")) or text(post["hero"].get("hash")) or None
        return {"entry": translation, "hero_content": content, "expected": {"hero_hash": expected_hero, "body": body}}

    def placeholder_steps(self, post, specs):
        steps, heading = [], ""
        for number, (block_type, value) in enumerate(specs, start=1):
            if block_type == "text":
                headings = BeautifulSoup(value, "html.parser").find_all(["h2", "h3", "h4", "h5", "h6"])
                heading = headings[-1].get_text(strip=True) if headings else heading
            if block_type == "animation" and value["placeholder"]:
                near = f" (“{heading.split(':')[0]}”)" if heading else ""
                name = value["src"].rstrip("/").rsplit("/", 1)[-1]
                steps.append((post["slug"], f"Block {number}{near}: replace the placeholder animation with a webm of [{name}]({value['src']})"))
        return steps

    def new_paths(self):
        """slug -> path for every English post here, plus this run's posts by their WordPress slug."""
        paths = {page.slug: page_path(page) for page in BlogArticlePage.objects.child_of(self.index).filter(locale=self.locale)}
        paths.update({plan["post"]["wp_slug"]: f"{self.index.url}{plan['post']['slug']}/" for plan in self.plans})
        return paths

    # -----------------------------------------------------------------------
    # The check
    # -----------------------------------------------------------------------

    def existing_page(self, post):
        page = BlogArticlePage.objects.child_of(self.index).filter(locale=self.locale, slug=post["slug"]).first()
        return page.specific if page else None

    def check_post(self, plan, page):
        """Check a page this run created or found, and its translations, writing every result and turning problems into hand steps."""
        slug = plan["post"]["slug"]
        if page is None:
            if self.options["check_only"]:
                self.write_check(
                    slug,
                    self.locale.language_code,
                    checks.result("page", False, "exists", "missing", step="The page is missing. Run the sync without --check-only"),
                )
            return
        published = self.importer.parse_wp_date(importer.element_text(plan["export"], "Date"))
        expected = {**plan["expected"], "date": published.astimezone(UTC).isoformat() if published else None}
        expected["migrated_slugs"] = set(self.importer.new_paths)
        expected["wordpress_url"] = importer.element_text(plan["export"], "Permalink")
        for row in checks.check_english(page, expected):
            self.write_check(slug, self.locale.language_code, row)
        for code, translation_plan in plan["translations"].items():
            translated = page.get_translation_or_none(self.translation_locales[code])
            # WordPress forwards ?p=<id> to the post, whatever its category.
            link = f"{self.wordpress_url}/{code}/?p={translation_plan['entry']['wp_id']}"
            for row in checks.check_translation(translated.specific if translated else None, {**translation_plan["expected"], "wordpress_url": link}):
                self.write_check(slug, code, row)

    def write_check(self, slug, locale, row):
        self.out.write(self.out.checks, {"slug": slug, "locale": locale, **row})
        if row["result"] == checks.FAIL:
            self.failed_checks += 1
        listed_already = row["check"] == "placeholders" and slug in self.created
        if row["result"] != checks.PASS and not listed_already:
            self.out.hand_steps.append((slug, row["step"] if locale == self.locale.language_code else f"{locale}: {row['step']}"))

    # -----------------------------------------------------------------------
    # English pages
    # -----------------------------------------------------------------------

    def sync_post(self, plan):
        """Create one English page complete and publish it, or report why not; returns the page when it's there."""
        post, export_post = plan["post"], plan["export"]
        title = importer.element_text(export_post, "Title")
        row = {"slug": post["slug"], "locale": self.locale.language_code, "wordpress_url": importer.element_text(export_post, "Permalink")}
        existing = BlogArticlePage.objects.child_of(self.index).filter(locale=self.locale, slug=post["slug"]).first()
        if existing is not None:
            existing = existing.specific
            published = self.importer.parse_wp_date(importer.element_text(export_post, "Date"))
            if existing.title != title or existing.first_published_at != published:
                self.report(**row, action=FAILED, page_id=existing.pk, detail="a different page has this slug (title or date differ): left alone")
                return None
            self.report(**row, action=SKIPPED, page_id=existing.pk, url=existing.full_url or "", detail="already there")
            return existing
        self.out.hand_steps += plan["hand_steps"]
        if self.dry_run:
            self.report(**row, action=WOULD_CREATE, detail=self.describe_plan(plan))
            return None

        self.importer.start_post()
        self.fixer.rows = []
        try:
            with transaction.atomic():
                page = self.build_page(plan, title)
        except Exception as exc:
            self.importer.forget_post_images()
            self.report(**row, action=FAILED, detail=f"{type(exc).__name__}: {exc}")
            self.record_warnings(post["slug"], [*plan["warnings"], *self.importer.post_warnings])
            return None
        self.importer.created_plans = []
        self.created.add(post["slug"])
        self.report(**row, action=CREATED, page_id=page.pk, url=page.full_url or "", detail=self.image_text_changes())
        self.record_warnings(post["slug"], [*plan["warnings"], *self.importer.post_warnings])
        self.redirect(wp_id=post["wp_id"], old_url=row["wordpress_url"], locale="en", slug=post["wp_slug"], page=page)
        return page

    def build_page(self, plan, title):
        post = plan["post"]
        hero = post["hero"]
        content = self.importer.materialize_content(copy.deepcopy(plan["specs"]), title)
        page = BlogArticlePage(
            title=title,
            slug=post["slug"],
            locale=self.locale,
            topic=self.topics[post["topic"]],
            seo_title=text(post.get("seo_title")),
            search_description=text(post["search_description"]),
            exclude_from_rss=bool(post.get("exclude_from_rss")),
            first_published_at=self.importer.parse_wp_date(importer.element_text(plan["export"], "Date")),
            hero_style=HeroStyle.TEXT_ONLY,
            content=content,
        )
        if plan["hero"] is not None:
            library = image_text(plan["images"][plan["hero"]["hash"]])
            page.image = self.importer.get_or_create_image(plan["hero"]["src"], library["title"], description=library["description"])
            if page.image is None:
                raise ValueError(f"could not import the hero image {plan['hero']['src']}")
            page.image_alt = text(hero.get("alt")) or library["description"]
            page.hero_style = HeroStyle.STANDARD_IMAGE
        if plan["hero_video"] is not None:
            [(_, [(_, video)])] = self.importer.materialize_content([plan["hero_video"]], title)
            page.hero_style = HeroStyle.VIDEO
            page.hero_video = [("video", video)]

        used_hashes = {entry["hash"] for entry in plan["body"] if entry["hash"]} | ({plan["hero"]["hash"]} if plan["hero"] else set())
        for used in sorted(used_hashes):
            self.fixer.set_image_text(used, image_text(plan["images"][used]))
        self.fixer.video_decisions = {post["slug"]: {video["video_url"]: video["alt"] for video in post.get("videos") or []}}
        self.fixer.link_decisions = {
            post["slug"]: {link["url"]: (link["action"], text(link.get("new_url"))) for link in post.get("links") or [] if link["action"] != "keep"}
        }
        self.fixer.fix_video_alt(page)
        if page.hero_video:
            for block in page.hero_video:
                block.value["alt"] = self.fixer.video_decisions[post["slug"]].get(block.value["video_url"], block.value["alt"])
        self.fixer.fix_links(page)

        page.article_authors = [BlogArticleAuthor(author=author, sort_order=order) for order, author in enumerate(self.byline(post))]
        self.index.add_child(instance=page)
        page.tags.set([self.tags[tag] for tag in post.get("tags") or []])
        page.save_revision().publish()
        return page

    def byline(self, post):
        authors = []
        for entry in post.get("authors") or []:
            if text(entry.get("slug")):
                authors.append(self.authors[entry["slug"]])
                continue
            # A new author is reused by later posts and reruns.
            author = BlogAuthor.objects.filter(slug=slugify(entry["new"]), locale=self.locale).first()
            if author is None:
                author = BlogAuthor(name=text(entry["new"]), slug=slugify(entry["new"]), locale=self.locale, live=False)
                author.save()
                author.save_revision().publish()
            authors.append(author)
        return authors

    def image_text_changes(self):
        changes = [
            f"image text {row['detail']}: {row['old']} -> {row['new']}"
            for row in self.fixer.rows
            if row["action"] in (fixer.CHANGED, fixer.WOULD_CHANGE)
        ]
        return "; ".join(changes)

    def describe_plan(self, plan):
        counts = {}
        for block_type, value in plan["specs"]:
            name = "image_caption" if block_type == "image" and value.get("caption") else block_type
            counts[name] = counts.get(name, 0) + 1
        hashes = {entry["hash"] for entry in plan["body"] if entry["hash"]} | ({plan["hero"]["hash"]} if plan["hero"] else set())
        reused = set(SpringfieldImage.objects.filter(file_hash__in=hashes).values_list("file_hash", flat=True))
        paths = self.importer.new_paths
        sources = [
            value if block_type == "text" else value.get("caption") or "" for block_type, value in plan["specs"] if block_type in ("text", "image")
        ]
        links = sum(
            1
            for source in sources
            for anchor in BeautifulSoup(source, "html.parser").find_all("a", href=True)
            if urlparse(anchor["href"]).netloc.endswith("blog.mozilla.org") and urlparse(anchor["href"]).path.rstrip("/").rsplit("/", 1)[-1] in paths
        )
        blocks = ", ".join(f"{count} {name}" for name, count in counts.items())
        images = f"{len(hashes - reused)} new, {len(reused)} reused"
        return f"blocks: {blocks}; images: {images}; links rewritten: {links}; hand steps: {len(plan['hand_steps'])}"

    # -----------------------------------------------------------------------
    # Translations
    # -----------------------------------------------------------------------

    def sync_translations(self, plan, page):
        post = plan["post"]
        for code, translation_plan in plan["translations"].items():
            entry = translation_plan["entry"]
            row = {"slug": post["slug"], "locale": code}
            if page is None:
                if self.dry_run:
                    self.report(**row, action=WOULD_CREATE, detail="after its English page")
                else:
                    self.report(**row, action=SKIPPED, detail="its English page wasn't created")
                continue
            key = f"{page.slug}-{code}"
            self.translator.corrections = {key: entry.get("corrections") or []}
            self.translator.image_pairs = {key: entry.get("image_pairs") or []}
            hero = entry.get("hero") or {}
            self.translator.heroes = {}
            if text(hero.get("hash")) and hero["hash"] != text(post["hero"].get("hash")):
                self.translator.heroes[key] = {"hash": hero["hash"], "alt": text(hero["alt"]), "content": translation_plan["hero_content"]}
            result = self.translator.translate(page, self.translation_locales[code], wordpress_slug=post["wp_slug"])
            detail = "; ".join(part for part in (result.get("hero", ""), result.get("detail", "")) if part)
            action = {translations.CREATED: CREATED, translations.WOULD_CREATE: WOULD_CREATE, translations.FAILED: FAILED}.get(
                result["action"], SKIPPED
            )
            self.report(
                **row,
                action=action,
                page_id=result.get("page_id", ""),
                url=result.get("url", ""),
                wordpress_url=result.get("wordpress_url", ""),
                detail=detail,
            )
            if action == CREATED:
                translated = BlogArticlePage.objects.get(pk=result["page_id"])
                self.redirect(wp_id=entry["wp_id"], old_url=result.get("wordpress_url", ""), locale=code, slug=entry["wp_slug"], page=translated)

    # -----------------------------------------------------------------------
    # --fix-translation-heroes
    # -----------------------------------------------------------------------

    def fix_translation_heroes(self):
        for fix in self.data.get("hero_fixes") or []:
            row = {"slug": fix["en_slug"], "locale": fix["locale"]}
            english = BlogArticlePage.objects.filter(locale=self.locale, slug=fix["en_slug"]).first()
            translated = english.get_translation_or_none(self.translation_locales[fix["locale"]]) if english else None
            if translated is None:
                self.report(**row, action=SKIPPED, detail=f"no {fix['locale']} translation of {fix['en_slug']}")
                continue
            translated = translated.specific
            row["page_id"] = translated.pk
            if not translated.live or translated.has_unpublished_changes:
                self.report(**row, action=SKIPPED, detail="not live, or has unpublished changes: publish or revert it, then rerun")
                continue
            if translated.image and translated.image.file_hash == fix["hash"] and translated.image_alt == fix["alt"]:
                self.report(**row, action=SKIPPED, detail="already has the hero")
                continue
            try:
                with transaction.atomic():
                    note = swap_translation_hero(
                        translated, self.translator, expected_hash=fix["hash"], alt=fix["alt"], language=fix["locale"], wp_id=fix["wp_id"]
                    )
                    if self.dry_run:
                        transaction.set_rollback(True)
                    else:
                        translated.save_revision(log_action=True).publish(log_action=True)
            except Exception as exc:
                self.report(**row, action=FAILED, detail=f"{type(exc).__name__}: {exc}")
                continue
            self.report(**row, action=WOULD_CHANGE if self.dry_run else CHANGED, url=translated.full_url or "", detail=note)

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------

    def report(self, **row):
        self.counts[row["action"]] = self.counts.get(row["action"], 0) + 1
        if row["action"] == FAILED:
            self.failed += 1
            prefix = f"{row['locale']}: " if row.get("locale") and row["locale"] != self.locale.language_code else ""
            self.out.hand_steps.append((row["slug"], f"{prefix}Failed: {row.get('detail', '')}. Fix the cause, then rerun"))
        self.out.write(self.out.report, row)
        line = f"  {row['action']}: {row['slug']} {row.get('locale', '')}{': ' + row['detail'] if row.get('detail') else ''}"
        (self.stderr if row["action"] == FAILED else self.stdout).write(line)

    def record_warnings(self, slug, warnings):
        for kind, message in warnings:
            self.out.write(self.out.warnings, {"slug": slug, "locale": self.locale.language_code, "type": kind, "warning": message})

    def redirect(self, *, wp_id, old_url, locale, slug, page):
        self.out.write(
            self.out.redirects,
            {"wp_id": wp_id, "old_url": old_url, "locale": locale, "slug": slug, "migrated": "yes", "new_url": f"{PUBLIC_HOST}{page_path(page)}"},
        )

    def mode(self):
        if self.options.get("check_only"):
            return "check only"
        name = "fix translation heroes" if self.options.get("fix_translation_heroes") else "sync"
        return f"{name}, dry run" if self.dry_run else name

    def summary(self, sync_path):
        try:
            digest = hashlib.sha256(sync_path.read_bytes()).hexdigest()
        except OSError:
            digest = "(unreadable)"
        site = Site.objects.filter(is_default_site=True).first()
        lines = [
            f"- Sync file: `{sync_path.name}` (sha256 `{digest}`)",
            f"- Export: `{self.options.get('export') or '(none)'}`",
            f"- Site: {site.hostname if site else '(none)'}",
            f"- Mode: {self.mode()}",
        ]
        lines += [f"- {action}: {count}" for action, count in sorted(self.counts.items())]
        if self.stopped:
            lines += ["", "**Stopped before writing anything:**", "", *[f"- {error}" for error in self.stopped]]
        elif self.failed:
            lines += ["", f"**{self.failed} failed.** See `report.csv`, fix the cause, then rerun the same file."]
        if self.failed_checks:
            lines += ["", f"**{self.failed_checks} checks failed.** See `check.csv` and `hand-steps.md`."]
        return "\n".join(lines)
