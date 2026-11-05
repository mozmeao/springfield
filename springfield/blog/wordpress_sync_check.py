# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Read-only checks of synced blog pages against what the sync expected; image hashes come from the database.

Each result carries a `step`: what an editor does to fix it, in plain words.
"""

import html
from datetime import UTC
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from springfield.blog.management.commands.fix_imported_blog_posts import EMBED_ALT_RE, EMBED_ID_RE, IMAGE_EMBED_RE
from springfield.blog.management.commands.import_wordpress_blog_posts import youtube_video_id
from springfield.cms.models import SpringfieldImage

PASS = "pass"
FAIL = "fail"
WARNING = "warning"
ANIMATION = "animation"


def result(check, passed, expected, found, failure=FAIL, step=""):
    return {"check": check, "result": PASS if passed else failure, "expected": str(expected), "found": str(found), "step": step}


def shown(value):
    if isinstance(value, (list, tuple)):
        return ", ".join(shown(item) for item in value if item) or "(none)"
    return str(value) if value not in (None, "") else "(none)"


def hero_step(expected_hash, link):
    if expected_hash is None:
        return "The page should have no hero"
    image = SpringfieldImage.objects.filter(file_hash=expected_hash).first()
    if image:
        return f"The hero isn't the reviewed image: use “{image.title}” from the image library"
    return f"The hero isn't the featured image on [WordPress]({link})"


def youtube_step(expected, found, link):
    def linked(videos):
        return ", ".join(f"[{video}](https://www.youtube.com/watch?v={video})" for video in videos)

    missing = [video for video in expected if video not in found]
    extra = [video for video in found if video not in expected]
    if missing and extra:
        return f"Replace the YouTube video {linked(extra)} with {linked(missing)}"
    if missing:
        return f"Add the YouTube video {linked(missing)}"
    return f"The YouTube videos don't match [WordPress]({link})"


def body_step(expected, found, link):
    return f"The body images don't match [WordPress]({link}) ({len(expected)} there, {len(found)} here). Swap them in the editor"


def page_media(page):
    """The page's body images, animations and videos in order, as dicts of kind, hash, alt and URL."""
    items = []
    for block in page.content.raw_data:
        value = block["value"]
        if block["type"] == "text":
            for tag in IMAGE_EMBED_RE.findall(value):
                image_id, alt = EMBED_ID_RE.search(tag), EMBED_ALT_RE.search(tag)
                items.append({"kind": "image", "id": int(image_id.group(1)) if image_id else None, "alt": html.unescape(alt.group(1)) if alt else ""})
        elif block["type"] == "image_caption":
            items.append({"kind": "image", "id": value["image"]["image"], "alt": value["image"].get("image_alt", "")})
        elif block["type"] == "media":
            for child in value:
                child_value = child["value"]
                if child["type"] == "image":
                    items.append({"kind": "image", "id": child_value["image"], "alt": child_value.get("image_alt", "")})
                elif child["type"] in (ANIMATION, "video"):
                    items.append({"kind": child["type"], "url": child_value.get("video_url", ""), "alt": child_value.get("alt", "")})
    images = SpringfieldImage.objects.in_bulk([item["id"] for item in items if item.get("id")])
    for item in items:
        image = images.get(item.get("id"))
        item["hash"] = image.file_hash if image else None
        item["decorative"] = bool(image and image.is_decorative)
    return items


def rich_text(page):
    """The HTML of each text block and image caption."""
    for block in page.content.raw_data:
        if block["type"] == "text":
            yield block["value"]
        elif block["type"] == "image_caption":
            yield block["value"].get("caption") or ""


def body_tokens(items):
    return [item["hash"] if item["kind"] == "image" else ANIMATION for item in items if item["kind"] != "video"]


def check_english(page, expected):
    """One result per check of an English page."""
    items = page_media(page)
    images = [item for item in items if item["kind"] == "image"]
    hero_hash = page.image.file_hash if page.image else None
    link = expected["wordpress_url"]
    body = body_tokens(items)
    rows = [
        result(
            "hero",
            hero_hash == expected["hero_hash"],
            expected["hero_hash"] or "(no hero)",
            hero_hash or "(no hero)",
            step=hero_step(expected["hero_hash"], link),
        ),
        result(
            "body images",
            body == expected["body"],
            " ".join(map(str, expected["body"])),
            " ".join(map(str, body)),
            step=body_step(expected["body"], body, link),
        ),
    ]
    leading_ids = []
    for block in page.content.raw_data:
        if block["type"] == "text":
            break
        if block["type"] == "image_caption":
            leading_ids.append(block["value"]["image"]["image"])
        elif block["type"] == "media":
            leading_ids += [child["value"]["image"] for child in block["value"] if child["type"] == "image"]
    duplicate = hero_hash is not None and SpringfieldImage.objects.filter(pk__in=leading_ids, file_hash=hero_hash).exists()
    rows.append(
        result(
            "hero duplicate",
            not duplicate,
            "no body image before the first text repeats the hero",
            hero_hash if duplicate else "none",
            WARNING,
            step="The first image in the body repeats the hero. Remove it if it isn't wanted",
        )
    )

    videos = [youtube_video_id(item["url"]) for item in items if item["kind"] == "video"]
    hero_video = [youtube_video_id(block.value["video_url"]) for block in page.hero_video or []]
    rows.append(
        result(
            "youtube",
            (hero_video, videos) == (expected["hero_video"], expected["youtube"]),
            (expected["hero_video"], expected["youtube"]),
            (hero_video, videos),
            step=youtube_step(expected["hero_video"] + expected["youtube"], hero_video + videos, link),
        )
    )

    placeholders = [item["url"] for item in items if item["kind"] == ANIMATION and item["url"] == expected["placeholder_url"]]
    rows.append(
        result(
            "placeholders",
            not placeholders,
            "no Animation block on the placeholder",
            f"{len(placeholders)} on the placeholder",
            WARNING,
            step="Replace the placeholder animation with its webm"
            if len(placeholders) == 1
            else f"Replace the {len(placeholders)} placeholder animations with their webms",
        )
    )

    found_fields = {
        "date": page.first_published_at.astimezone(UTC).isoformat() if page.first_published_at else None,
        "topic": page.topic.slug if page.topic else None,
        "tags": sorted(tag.slug for tag in page.tags.all()),
        "search text": (page.seo_title, page.search_description),
        "byline": [placement.author.slug for placement in page.article_authors.all().order_by("sort_order")],
        "rss": "excluded" if page.exclude_from_rss else "included",
    }
    rows += [
        result(
            name,
            found_fields[name] == expected[name],
            expected[name],
            found_fields[name],
            step=f"The {name} should be {shown(expected[name])}, but it's {shown(found_fields[name])}",
        )
        for name in found_fields
    ]

    found_alts = [item["alt"] for item in images]
    missing = [item["hash"] for item in images if not item["decorative"] and not item["alt"].strip()]
    if page.image and not page.image.is_decorative and not page.image_alt.strip():
        missing.append(hero_hash)
    alts_match = (page.image_alt, found_alts) == (expected["hero_alt"], expected["alts"])
    rows.append(
        result(
            "alt text",
            alts_match and not missing,
            (expected["hero_alt"], expected["alts"]),
            (page.image_alt, found_alts),
            step="The alt text doesn't match the review. Compare each image's alt with `check.csv`",
        )
    )

    stale = [
        anchor["href"]
        for source in rich_text(page)
        for anchor in BeautifulSoup(source, "html.parser").find_all("a", href=True)
        if urlparse(anchor["href"]).netloc.endswith("blog.mozilla.org")
        and urlparse(anchor["href"]).path.rstrip("/").rsplit("/", 1)[-1] in expected["migrated_slugs"]
    ]
    rows.append(
        result(
            "links",
            not stale,
            "no link to a blog.mozilla.org post that is on this site",
            ", ".join(stale) or "none",
            step=f"Point these links at the posts on this site: {', '.join(stale)}",
        )
    )
    return rows


def check_translation(page, expected):
    """One result per check of a translation; `page` is None when it doesn't exist."""
    if page is None:
        return [result("translation", False, "exists and is live", "missing", step="The translation is missing. Rerun the sync")]
    if not page.live:
        return [result("translation", False, "exists and is live", "not live", step="The translation isn't live. Publish it")]
    link = expected["wordpress_url"]
    hero_hash = page.image.file_hash if page.image else None
    items = page_media(page)
    images = [item["hash"] for item in items if item["kind"] == "image"]
    videos = [youtube_video_id(block.value["video_url"]) for block in page.hero_video or []]
    videos += [youtube_video_id(item["url"]) for item in items if item["kind"] == "video"]
    return [
        result("translation", True, "exists and is live", "live"),
        result(
            "translation hero",
            hero_hash == expected["hero_hash"],
            expected["hero_hash"],
            hero_hash,
            step=hero_step(expected["hero_hash"], link),
        ),
        result(
            "translation body images",
            images == expected["body"],
            " ".join(map(str, expected["body"])),
            " ".join(map(str, images)),
            step=body_step(expected["body"], images, link),
        ),
        result(
            "translation youtube",
            videos == expected["youtube"],
            " ".join(expected["youtube"]),
            " ".join(videos),
            step=youtube_step(expected["youtube"], videos, link),
        ),
    ]
