# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pairing the paragraphs of a blog.mozilla.org post with those of its WPML translation.

The English page on this site was imported from the English WordPress post, so its text
segments (as wagtail-localize cuts them) match that post's paragraphs. The translation was
written separately and rarely lines up one to one: translators join, split, add and drop
paragraphs. These functions line the two WordPress versions up on clues that survive
translation (link targets, numbers, names both versions use, length) and return, for each
English segment, the translated text to put in its place, or None where the translation has
nothing.

Used by the import_wordpress_blog_translations command.
"""

import html
import math
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from wagtail_localize.strings import extract_strings

from springfield.blog.management.commands.import_wordpress_blog_posts import parse_content

# Typography WordPress applies when it renders a post (wptexturize), folded away so the rendered
# translation and the imported English text compare equal.
TYPOGRAPHY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "\xa0": " "})

# Language directories in a URL, removed so a link to /de/kb/x and /en-US/kb/x compare equal.
LOCALE_PATH_RE = re.compile(r"/(?:en|en-us|de|fr|de-de|fr-fr)(?=/)", re.IGNORECASE)

# Words capitalised in every language, which carry no information about which paragraph is which.
COMMON_CAPITALISED = {"the", "die", "der", "das", "les", "des", "une", "und", "pour", "with"}

YOUTUBE_ID_RE = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{11})")

# Alignment costs: skipping a paragraph on one side, letting two translated paragraphs stand for
# one English one, and the reverse. A split costs more than a join because translators join
# paragraphs far more often than they drop one.
GAP_COST = 0.6
JOIN_COST = 0.3
SPLIT_COST = 1.0
# A paired paragraph scoring below this is reported as a guess.
WEAK_MATCH = -1.2


def normalise(text_or_html):
    """Plain, lower-case text with WordPress's typography folded away, for comparing paragraphs."""
    text = BeautifulSoup(text_or_html, "html.parser").get_text(" ") if "<" in text_or_html else text_or_html
    return re.sub(r"\s+", " ", html.unescape(text).translate(TYPOGRAPHY)).strip().lower()


@dataclass
class Paragraph:
    """One translatable string of a WordPress post, as wagtail-localize would cut it."""

    html: str
    attrs: dict = field(default_factory=dict)

    @property
    def key(self):
        return normalise(self.html)


def paragraphs(post_html):
    """The text of a WordPress post as wagtail-localize segments, in order: body text and image
    captions, cut the way the importer and wagtail-localize cut the English post."""
    specs, _ = parse_content(post_html)
    found = []
    for kind, value in specs:
        block_html = value if kind == "text" else (value.get("caption") or "") if kind == "image" else ""
        if not block_html:
            continue
        _, strings = extract_strings(block_html)
        found += [Paragraph(string.data, attrs) for string, attrs in strings if normalise(string.data)]
    return found


@dataclass
class Media:
    kind: str  # "image" or "video"
    source: str  # image URL or YouTube video id
    alt: str = ""

    @property
    def stem(self):
        return file_stem(self.source) if self.kind == "image" else self.source


def media(post_html):
    """Images and YouTube videos of a WordPress post, in document order."""
    found = []
    for element in BeautifulSoup(post_html, "html.parser").find_all(["img", "iframe", "a"]):
        if element.name == "img" and element.get("src"):
            found.append(Media("image", element["src"], element.get("alt", "")))
            continue
        url = element.get("src") or element.get("href") or ""
        video = YOUTUBE_ID_RE.search(url)
        if video and (element.name == "iframe" or element.get_text(strip=True) == url):
            found.append(Media("video", video.group(1)))
    return found


def file_stem(url_or_name):
    """A file name without its folder, extension, WordPress size suffix or storage suffix, so the
    same image compares equal across WordPress and the image library."""
    name = url_or_name.split("?")[0].rsplit("/", 1)[-1]
    name = re.sub(r"\.\w+$", "", name)
    name = re.sub(r"-\d+x\d+$", "", name)
    return re.sub(r"_[A-Za-z0-9]{7}$", "", name).lower()


def anchors(paragraph):
    """Clues that survive translation: link targets, numbers, capitalised words, length."""
    text = BeautifulSoup(paragraph.html, "html.parser").get_text(" ")
    links = {
        LOCALE_PATH_RE.sub("", attrs["href"]).split("?")[0].rstrip("/").replace("://www.", "://")
        for attrs in paragraph.attrs.values()
        if attrs.get("href")
    }
    numbers = set(re.findall(r"\d+", text))
    names = {word for word in re.findall(r"\b[A-Z][A-Za-z0-9+]{2,}\b", text) if word.lower() not in COMMON_CAPITALISED}
    return links, numbers, names, len(paragraph.key)


def joined(first, second):
    return (first[0] | second[0], first[1] | second[1], first[2] | second[2], first[3] + second[3])


def score(english, translated):
    """How likely two paragraphs say the same thing; higher is more likely."""
    total = 0.0
    for english_set, translated_set, weight in ((english[0], translated[0], 3.0), (english[1], translated[1], 1.5), (english[2], translated[2], 1.0)):
        if english_set or translated_set:
            total += weight * (2 * len(english_set & translated_set) / (len(english_set) + len(translated_set)) - 0.5)
    if english[3] and translated[3]:
        total += 1.0 - min(1.5, abs(math.log(translated[3] / english[3])))
    return total


@dataclass
class Alignment:
    """For each English paragraph key: the translated HTML, and the keys matched only weakly."""

    translations: dict
    doubtful: set


def align(english, translated):
    """Pair English and translated WordPress paragraphs with a sequence alignment.

    One English paragraph may take two consecutive translated ones (joined with a line break, as
    English joins them), or one translated paragraph may stand for two English ones (it goes on
    the first; the second has nothing). Paragraphs next to any such difference are doubtful."""
    english_anchors = [anchors(paragraph) for paragraph in english]
    translated_anchors = [anchors(paragraph) for paragraph in translated]
    # Names that only one version uses are noise: German capitalises every noun.
    shared = set().union(*[found[2] for found in english_anchors]) & set().union(*[found[2] for found in translated_anchors])
    english_anchors = [(links, numbers, names & shared, length) for links, numbers, names, length in english_anchors]
    translated_anchors = [(links, numbers, names & shared, length) for links, numbers, names, length in translated_anchors]

    rows, columns = len(english), len(translated)
    best = [[0.0] * (columns + 1) for _ in range(rows + 1)]
    move = [[None] * (columns + 1) for _ in range(rows + 1)]
    for row in range(1, rows + 1):
        best[row][0], move[row][0] = best[row - 1][0] - GAP_COST, "skip_english"
    for column in range(1, columns + 1):
        best[0][column], move[0][column] = best[0][column - 1] - GAP_COST, "skip_translated"
    for row in range(1, rows + 1):
        for column in range(1, columns + 1):
            options = [
                (best[row - 1][column - 1] + score(english_anchors[row - 1], translated_anchors[column - 1]), "pair"),
                (best[row - 1][column] - GAP_COST, "skip_english"),
                (best[row][column - 1] - GAP_COST, "skip_translated"),
            ]
            if column > 1:
                both = joined(translated_anchors[column - 2], translated_anchors[column - 1])
                options.append((best[row - 1][column - 2] + score(english_anchors[row - 1], both) - JOIN_COST, "join"))
            if row > 1:
                both = joined(english_anchors[row - 2], english_anchors[row - 1])
                options.append((best[row - 2][column - 1] + score(both, translated_anchors[column - 1]) - SPLIT_COST, "split"))
            best[row][column], move[row][column] = max(options)

    translations, doubtful, path = {}, set(), []
    row, column = rows, columns
    while row > 0 or column > 0:
        step = move[row][column]
        path.append((step, row))
        if step == "pair":
            translations[english[row - 1].key] = translated[column - 1].html
            if score(english_anchors[row - 1], translated_anchors[column - 1]) < WEAK_MATCH:
                doubtful.add(english[row - 1].key)
            row, column = row - 1, column - 1
        elif step == "join":
            translations[english[row - 1].key] = translated[column - 2].html + "<br/>" + translated[column - 1].html
            doubtful.add(english[row - 1].key)
            row, column = row - 1, column - 2
        elif step == "split":
            translations[english[row - 2].key] = translated[column - 1].html
            doubtful.add(english[row - 2].key)
            row, column = row - 2, column - 1
        elif step == "skip_english":
            row -= 1
        else:
            column -= 1

    path.reverse()
    for position, (step, _) in enumerate(path):
        if step != "pair":
            for nearby_step, nearby_row in path[max(0, position - 1) : position + 2]:
                if nearby_step == "pair" and nearby_row > 0:
                    doubtful.add(english[nearby_row - 1].key)
    return Alignment(translations, doubtful)


def apply_corrections(alignment, english, translated, corrections):
    """Apply hand corrections: [{"en": start of an English paragraph, "tr": start of a translated
    one, a list of starts to join, or None for nothing}]. Returns the corrections that matched
    nothing, so they can be reported."""
    unmatched = []
    for correction in corrections:
        english_key = next((paragraph.key for paragraph in english if paragraph.key.startswith(normalise(correction["en"]))), None)
        if english_key is None:
            unmatched.append(correction)
            continue
        alignment.doubtful.discard(english_key)
        if correction["tr"] is None:
            alignment.translations[english_key] = None
            continue
        starts = correction["tr"] if isinstance(correction["tr"], list) else [correction["tr"]]
        parts = [next((paragraph.html for paragraph in translated if paragraph.key.startswith(normalise(start))), None) for start in starts]
        if None in parts:
            unmatched.append(correction)
            continue
        alignment.translations[english_key] = "<br/>".join(parts)
    return unmatched


def tidy(translated_html):
    """Unwrap links nested in links (seen in WPML copies) and number the links a1, a2… in order,
    the form wagtail-localize gives the English string."""
    soup = BeautifulSoup(translated_html, "html.parser")
    for link in soup.find_all("a"):
        if link.find_parent("a"):
            link.unwrap()
    for tag in soup.find_all(["strong", "em", "b", "i"]):
        if tag.parent is not None and tag.parent.name == tag.name and len(tag.parent.contents) == 1:
            tag.parent.unwrap()
    for number, link in enumerate(soup.find_all("a"), 1):
        link.attrs = {"id": f"a{number}"}
    return str(soup)


def same_in_every_language(english_html):
    """A product name, footnote mark or number: text WordPress leaves untranslated by design."""
    key = normalise(english_html)
    if re.match(r"https?://", key):
        return False
    return len(key.split()) <= 3 or not re.search(r"[a-z]{3}", key)


def first_words(post_html, limit=155):
    """The start of a post's text, as WordPress uses it when a post has no excerpt."""
    text = re.sub(r"\s+", " ", BeautifulSoup(post_html, "html.parser").get_text(" ")).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0]


def keep_links(translated_html, link_ids):
    """Unwrap the links whose id the English string doesn't have, keeping their text:
    wagtail-localize can only give a translated string the links of its English one."""
    soup = BeautifulSoup(translated_html, "html.parser")
    for link in soup.find_all("a"):
        if link.get("id") not in link_ids:
            link.unwrap()
    return str(soup)
