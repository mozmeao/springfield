# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Read and validate the reviewed sync file for sync_wordpress_blog_posts. No database access."""

import json
import re

from django.utils.text import slugify

from springfield.blog.management.commands.fix_imported_blog_posts import IMAGE_TITLE_MAX_LENGTH, SEO_TITLE_MAX_LENGTH, TAGS, TOPICS
from springfield.blog.models.pages import RESERVED_ARTICLE_SLUGS

FORMAT = 1
TRANSLATION_LOCALES = ("de", "fr")
HERO_IMAGES = ("featured", "body", "none")
HERO_STYLES = ("standard_image", "video")
MEDIA_KINDS = ("video", "gif")
LINK_ACTIONS = ("keep", "replace", "unlink")
MAX_TAGS = 4
ALT_MAX_LENGTH = 255
ASSETS_HOST = "assets.mozilla.net"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
SLUG_RE = re.compile(r"^[-a-z0-9_]+$")

TOPIC_SLUGS = {term.slug for term in TOPICS}
TAG_SLUGS = {term.slug for term in TAGS}


class SyncFileError(ValueError):
    """The sync file can't be used; `errors` lists every problem found."""

    def __init__(self, errors):
        super().__init__("\n".join(errors))
        self.errors = errors


def read_sync_file(path):
    """Load and validate the sync file at `path`, raising SyncFileError on any problem."""
    try:
        with open(path) as sync_file:
            data = json.load(sync_file)
    except (OSError, ValueError) as exc:
        raise SyncFileError([f"could not read {path}: {exc}"]) from exc
    errors = validate(data)
    if errors:
        raise SyncFileError(errors)
    return data


def imported_posts(data):
    return [post for post in data["posts"] if post.get("import")]


def text(value):
    return (value or "").strip() if isinstance(value, str) else ""


def on_assets_host(url):
    return ASSETS_HOST in text(url)


def is_local_image(path):
    """A path relative to the sync file, for an image that travels with it."""
    return "://" not in text(path) and text(path).lower().endswith(IMAGE_EXTENSIONS)


def validate(data):
    """Every rule the file breaks, as messages naming the post and field."""
    if not isinstance(data, dict):
        return ["the sync file must be a JSON object"]
    if data.get("format") != FORMAT:
        return [f"format: must be {FORMAT}, got {data.get('format')!r}"]
    errors = []
    posts = data.get("posts")
    if not isinstance(posts, list):
        return ["posts: must be a list"]

    images = {}
    for number, image in enumerate(data.get("images") or [], start=1):
        where = f"images entry {number}"
        file_hash = text(image.get("hash"))
        if not file_hash:
            errors.append(f"{where}: hash is missing")
            continue
        if not text(image.get("title")):
            errors.append(f"{where} ({file_hash}): title is missing")
        elif len(text(image.get("title"))) > IMAGE_TITLE_MAX_LENGTH:
            errors.append(f"{where} ({file_hash}): title is longer than {IMAGE_TITLE_MAX_LENGTH} characters")
        if not image.get("decorative") and not text(image.get("description")):
            errors.append(f"{where} ({file_hash}): description is missing (or mark it decorative)")
        images[file_hash] = image

    wp_ids, slugs, new_authors = set(), set(), {}
    needs_placeholder = False
    for number, post in enumerate(posts, start=1):
        name = text(post.get("wp_slug")) or f"entry {number}"
        where = f"post {name}"
        wp_id = post.get("wp_id")
        if not isinstance(wp_id, int) or wp_id <= 0:
            errors.append(f"{where}: wp_id must be a WordPress post ID")
        elif wp_id in wp_ids:
            errors.append(f"{where}: wp_id {wp_id} is used by another post")
        wp_ids.add(wp_id)
        if not text(post.get("wp_slug")):
            errors.append(f"{where}: wp_slug is missing")
        if not post.get("import"):
            if not text(post.get("note")):
                errors.append(f"{where}: note is missing (say why it isn't imported)")
            if post.get("translations"):
                errors.append(f"{where}: translations: only imported posts can have translations")
            continue

        slug = text(post.get("slug"))
        if not SLUG_RE.match(slug):
            errors.append(f"{where}: slug {slug!r} is not a valid slug")
        elif slug in RESERVED_ARTICLE_SLUGS:
            errors.append(f"{where}: slug {slug!r} is reserved by the blog")
        elif slug in slugs:
            errors.append(f"{where}: slug {slug!r} is used by another post")
        slugs.add(slug)

        if post.get("topic") not in TOPIC_SLUGS:
            errors.append(f"{where}: topic {post.get('topic')!r} is not one of {', '.join(sorted(TOPIC_SLUGS))}")
        tags = post.get("tags") or []
        if len(tags) > MAX_TAGS:
            errors.append(f"{where}: tags: at most {MAX_TAGS}")
        if len(set(tags)) != len(tags):
            errors.append(f"{where}: tags: repeated")
        errors += [f"{where}: tags: {tag!r} is not on the tag list" for tag in tags if tag not in TAG_SLUGS]

        if not text(post.get("search_description")):
            errors.append(f"{where}: search_description is missing")
        if len(text(post.get("seo_title"))) > SEO_TITLE_MAX_LENGTH:
            errors.append(f"{where}: seo_title is longer than {SEO_TITLE_MAX_LENGTH} characters")
        for author in post.get("authors") or []:
            if not (text(author.get("slug")) or text(author.get("new"))):
                errors.append(f"{where}: authors: each entry needs a slug or a new name")
            elif text(author.get("new")):
                name = new_authors.setdefault(slugify(author["new"]), text(author["new"]))
                if name != text(author["new"]):
                    errors.append(f"{where}: authors: {author['new']!r} and {name!r} would share a slug: use one name")

        hero = post.get("hero") or {}
        if hero.get("image") not in HERO_IMAGES:
            errors.append(f"{where}: hero.image must be one of {', '.join(HERO_IMAGES)}")
        elif hero["image"] != "none":
            if not text(hero.get("hash")):
                errors.append(f"{where}: hero.hash is missing")
            elif text(hero.get("hash")) not in images:
                errors.append(f"{where}: hero.hash {hero['hash']} has no images entry")
        if hero.get("style", "standard_image") not in HERO_STYLES:
            errors.append(f"{where}: hero.style must be one of {', '.join(HERO_STYLES)}")
        if len(text(hero.get("alt"))) > ALT_MAX_LENGTH:
            errors.append(f"{where}: hero.alt is longer than {ALT_MAX_LENGTH} characters")

        for alt in post.get("image_alt") or []:
            if not isinstance(alt.get("position"), int) or alt["position"] < 1 or not text(alt.get("hash")):
                errors.append(f"{where}: image_alt: each entry needs a position and a hash")
            elif len(text(alt.get("alt"))) > ALT_MAX_LENGTH:
                errors.append(f"{where}: image_alt position {alt['position']}: alt is longer than {ALT_MAX_LENGTH} characters")

        for video in post.get("videos") or []:
            if not text(video.get("video_url")) or not text(video.get("alt")):
                errors.append(f"{where}: videos: each entry needs a video_url and alt")
            elif len(text(video["alt"])) > ALT_MAX_LENGTH:
                errors.append(f"{where}: videos {video['video_url']}: alt is longer than {ALT_MAX_LENGTH} characters")

        for item in post.get("media") or []:
            label = f"{where}: media {text(item.get('src')) or '(no src)'}"
            if not text(item.get("src")) or item.get("kind") not in MEDIA_KINDS:
                errors.append(f"{label}: needs a src and a kind ({', '.join(MEDIA_KINDS)})")
            if not text(item.get("alt")):
                errors.append(f"{label}: alt is missing")
            elif len(text(item["alt"])) > ALT_MAX_LENGTH:
                errors.append(f"{label}: alt is longer than {ALT_MAX_LENGTH} characters")
            if bool(text(item.get("webm_url"))) != bool(text(item.get("poster_url"))):
                errors.append(f"{label}: webm_url and poster_url come together")
            elif text(item.get("webm_url")) and not (on_assets_host(item["webm_url"]) and on_assets_host(item["poster_url"])):
                errors.append(f"{label}: webm_url and poster_url must be on {ASSETS_HOST}")
            needs_placeholder = needs_placeholder or not text(item.get("webm_url"))

        for link in post.get("links") or []:
            action = link.get("action")
            if not text(link.get("url")) or action not in LINK_ACTIONS or (action == "replace" and not text(link.get("new_url"))):
                errors.append(f"{where}: links: each entry needs a url and action keep, replace (with new_url) or unlink")

        for translation in post.get("translations") or []:
            locale = translation.get("locale")
            label = f"{where} {locale}"
            if locale not in TRANSLATION_LOCALES:
                errors.append(f"{where}: translations: locale must be one of {', '.join(TRANSLATION_LOCALES)}")
                continue
            if not translation.get("import"):
                continue
            if not isinstance(translation.get("wp_id"), int) or not text(translation.get("wp_slug")):
                errors.append(f"{label}: translation needs a wp_id and wp_slug")
            translation_hero = translation.get("hero") or {}
            if text(translation_hero.get("hash")) and text(translation_hero.get("hash")) != text(hero.get("hash")):
                if not text(translation_hero.get("alt")):
                    errors.append(f"{label}: hero.alt is missing (the hero differs from the English one)")
                elif len(text(translation_hero.get("alt"))) > ALT_MAX_LENGTH:
                    errors.append(f"{label}: hero.alt is longer than {ALT_MAX_LENGTH} characters")

    if needs_placeholder:
        placeholder = data.get("placeholder") or {}
        poster = placeholder.get("poster_url")
        if not (on_assets_host(placeholder.get("webm_url")) and (on_assets_host(poster) or is_local_image(poster))):
            errors.append(
                f"placeholder: a webm_url on {ASSETS_HOST} and a poster_url (on {ASSETS_HOST}, or an image file beside the sync file) "
                "are needed for media with no webm_url"
            )

    for number, fix in enumerate(data.get("hero_fixes") or [], start=1):
        where = f"hero_fixes entry {number} ({text(fix.get('en_slug'))} {fix.get('locale')})"
        if not text(fix.get("en_slug")) or fix.get("locale") not in TRANSLATION_LOCALES:
            errors.append(f"{where}: needs an en_slug and a locale ({', '.join(TRANSLATION_LOCALES)})")
        if not isinstance(fix.get("wp_id"), int) or fix["wp_id"] <= 0:
            errors.append(f"{where}: wp_id must be the translation's WordPress post ID")
        if not text(fix.get("hash")):
            errors.append(f"{where}: hash is missing")
        if not text(fix.get("alt")):
            errors.append(f"{where}: alt is missing")
        elif len(text(fix.get("alt"))) > ALT_MAX_LENGTH:
            errors.append(f"{where}: alt is longer than {ALT_MAX_LENGTH} characters")
    return errors
