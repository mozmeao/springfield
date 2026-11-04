# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import json

import pytest

from springfield.blog.wordpress_sync import SyncFileError, read_sync_file, validate

ASSETS = "https://assets.mozilla.net/blog"

VALID = {
    "format": 1,
    "sync": "2026-11-03",
    "wordpress_url": "https://blog.mozilla.org",
    "placeholder": {"webm_url": f"{ASSETS}/placeholder.webm", "poster_url": f"{ASSETS}/placeholder.jpg"},
    "posts": [
        {
            "import": True,
            "wp_id": 101,
            "wp_slug": "first-post",
            "slug": "first-post",
            "topic": "ai",
            "tags": ["switching", "campaigns"],
            "seo_title": "",
            "search_description": "A first post.",
            "authors": [{"slug": "bobby-holley"}, {"new": "New Person"}],
            "hero": {"image": "featured", "hash": "aaa", "alt": "A hero", "style": "standard_image", "drop_body_duplicate": False},
            "image_alt": [{"position": 1, "hash": "aaa", "alt": "In the body"}],
            "videos": [{"video_url": "https://www.youtube.com/watch?v=abc", "alt": "A video"}],
            "media": [{"src": "https://blog.mozilla.org/x.mp4", "kind": "video", "alt": "A clip"}],
            "links": [{"url": "https://example.com/", "action": "unlink"}],
            "exclude_from_rss": False,
            "translations": [{"locale": "de", "import": True, "wp_id": 102, "wp_slug": "erster", "hero": {"hash": "bbb", "alt": "Ein Bild"}}],
        },
        {"import": False, "wp_id": 103, "wp_slug": "a-mozilla-post", "note": "Mozilla, not Firefox"},
    ],
    "images": [{"hash": "aaa", "title": "Hero", "description": "A hero"}, {"hash": "bbb", "title": "Decor", "decorative": True}],
    "hero_fixes": [{"en_slug": "built-in-vpn", "locale": "de", "wp_id": 9, "hash": "ccc", "alt": "Ein VPN"}],
}


def changed(change):
    data = copy.deepcopy(VALID)
    change(data)
    return data


def first_post(data):
    return data["posts"][0]


def test_a_valid_file_has_no_errors():
    assert validate(VALID) == []


def test_read_sync_file_raises_with_every_error(tmp_path):
    path = tmp_path / "sync.json"
    path.write_text(json.dumps(changed(lambda data: first_post(data).update(topic="firefox", search_description=""))))

    with pytest.raises(SyncFileError) as raised:
        read_sync_file(path)

    assert len(raised.value.errors) == 2


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda data: data.update(format=2), "format: must be 1"),
        (lambda data: data["posts"][1].update(wp_id=101), "post a-mozilla-post: wp_id 101 is used by another post"),
        (lambda data: first_post(data).update(slug="Not A Slug"), "post first-post: slug 'Not A Slug' is not a valid slug"),
        (lambda data: first_post(data).update(slug="feed"), "post first-post: slug 'feed' is reserved"),
        (
            lambda data: data["posts"].append({**first_post(data), "wp_id": 104, "wp_slug": "copy"}),
            "post copy: slug 'first-post' is used by another post",
        ),
        (lambda data: first_post(data).update(topic="firefox"), "post first-post: topic 'firefox' is not one of"),
        (lambda data: first_post(data).update(tags=["kit", "vpn", "tabs", "search", "mobile"]), "post first-post: tags: at most 4"),
        (lambda data: first_post(data).update(tags=["kit", "kit"]), "post first-post: tags: repeated"),
        (lambda data: first_post(data).update(tags=["firefox-features"]), "post first-post: tags: 'firefox-features' is not on the tag list"),
        (lambda data: first_post(data).update(search_description=""), "post first-post: search_description is missing"),
        (lambda data: first_post(data).update(seo_title="x" * 256), "post first-post: seo_title is longer than 255"),
        (lambda data: first_post(data).update(authors=[{}]), "post first-post: authors: each entry needs a slug or a new name"),
        (lambda data: first_post(data)["hero"].update(image="first"), "post first-post: hero.image must be one of"),
        (lambda data: first_post(data)["hero"].update(hash=""), "post first-post: hero.hash is missing"),
        (lambda data: first_post(data)["hero"].update(hash="zzz"), "post first-post: hero.hash zzz has no images entry"),
        (lambda data: first_post(data)["hero"].update(style="large_image"), "post first-post: hero.style must be one of"),
        (lambda data: first_post(data)["hero"].update(alt="x" * 256), "post first-post: hero.alt is longer than 255"),
        (lambda data: first_post(data)["image_alt"][0].update(alt="x" * 256), "post first-post: image_alt position 1: alt is longer than 255"),
        (lambda data: first_post(data)["image_alt"][0].update(position=0), "post first-post: image_alt: each entry needs a position"),
        (lambda data: data["images"][0].update(title=""), "images entry 1 (aaa): title is missing"),
        (lambda data: data["images"][0].update(title="x" * 256), "images entry 1 (aaa): title is longer than 255"),
        (lambda data: data["images"][0].update(description=""), "images entry 1 (aaa): description is missing"),
        (lambda data: first_post(data)["media"][0].update(alt=""), "post first-post: media https://blog.mozilla.org/x.mp4: alt is missing"),
        (lambda data: first_post(data)["media"][0].update(webm_url=f"{ASSETS}/x.webm"), "webm_url and poster_url come together"),
        (
            lambda data: first_post(data)["media"][0].update(webm_url="https://example.com/x.webm", poster_url="https://example.com/x.jpg"),
            "webm_url and poster_url must be on assets.mozilla.net",
        ),
        (lambda data: data.pop("placeholder"), "placeholder: webm_url and poster_url on assets.mozilla.net are needed"),
        (lambda data: first_post(data)["links"][0].update(action="replace"), "post first-post: links: each entry needs a url and action"),
        (lambda data: data["posts"][1].update(translations=[{"locale": "de"}]), "post a-mozilla-post: translations: only imported posts"),
        (lambda data: first_post(data)["translations"][0].update(locale="es"), "post first-post: translations: locale must be one of de, fr"),
        (lambda data: first_post(data)["translations"][0]["hero"].update(alt=""), "post first-post de: hero.alt is missing"),
        (lambda data: data["posts"][1].update(note=""), "post a-mozilla-post: note is missing"),
        (lambda data: data["hero_fixes"][0].update(wp_id=0), "hero_fixes entry 1 (built-in-vpn de): wp_id must be"),
        (lambda data: data["hero_fixes"][0].update(alt=""), "hero_fixes entry 1 (built-in-vpn de): alt is missing"),
    ],
)
def test_each_rule_names_the_post_and_field(change, message):
    errors = validate(changed(change))

    assert any(message in error for error in errors), errors


def test_a_translation_with_the_english_hero_needs_no_alt():
    errors = validate(changed(lambda data: first_post(data)["translations"][0].update(hero={"hash": "aaa"})))

    assert errors == []


def test_a_not_imported_post_needs_only_its_ids_and_note():
    assert validate(changed(lambda data: data["posts"].__setitem__(1, {"import": False, "wp_id": 103, "wp_slug": "x", "note": "later"}))) == []
