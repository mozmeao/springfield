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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from wagtail_localize.strings import extract_strings

from springfield.blog.management.commands.import_wordpress_blog_posts import parse_content

# Typography WordPress applies when it renders a post (wptexturize), folded away so the rendered
# translation and the imported English text compare equal.
TYPOGRAPHY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "\xa0": " "})

# Language directories in a URL, removed so a link to /de/kb/x and /en-US/kb/x compare equal.
LOCALE_PATH_RE = re.compile(r"/(?:en|en-us|de|fr|de-de|fr-fr)(?=/)", re.IGNORECASE)
# Query parameters that say where a link was clicked, not where it goes.
TRACKING_PARAMS_RE = re.compile(r"^(utm_|mtm_|pk_|fbclid$|gclid$)", re.IGNORECASE)

# Words capitalised in every language, which carry no information about which paragraph is which.
COMMON_CAPITALISED = {"the", "die", "der", "das", "les", "des", "une", "und", "pour", "with"}

YOUTUBE_ID_RE = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{11})")

# Alignment costs: skipping a paragraph on one side, letting two translated paragraphs stand for
# one English one, and the reverse. A split costs more than a join because translators join
# paragraphs far more often than they drop one.
GAP_COST = 0.6
JOIN_COST = 0.3
SPLIT_COST = 1.0
# A paired paragraph scoring below this is reported as a guess: the clues disagree more than
# they agree, yet pairing still beat leaving both paragraphs out (which costs two gaps).
WEAK_MATCH = 0.0


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
        _, strings = extract_strings(without_inline_attributes(block_html))
        found += [Paragraph(string.data, attrs) for string, attrs in strings if normalise(string.data)]
    return found


def without_inline_attributes(block_html):
    """`block_html` with attributes kept only on links: WordPress styles inline tags with classes
    (`<strong class="has-inline-color">`), which wagtail-localize refuses to cut into strings."""
    soup = BeautifulSoup(block_html, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in ("a", "img", "iframe"):
            tag.attrs = {}
    return str(soup)


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
    name = re.sub(r"_[A-Za-z0-9]{7}$", "", name)
    return re.sub(r"-\d+x\d+$", "", name).lower()


def link_target(attrs):
    """A link's destination with the differences a translation makes folded away (the language
    directory, tracking parameters, www), or None for an element that is not a link. Other
    query parameters and the fragment stay: `?os=win` and `?os=mac`, or `#note-1` and
    `#note-2`, are different destinations."""
    if not attrs.get("href"):
        return None
    scheme, host, path, query, fragment = urlsplit(attrs["href"].replace("://www.", "://"))
    kept = sorted((name, value) for name, value in parse_qsl(query, keep_blank_values=True) if not TRACKING_PARAMS_RE.match(name))
    return urlunsplit((scheme, host, LOCALE_PATH_RE.sub("", path).rstrip("/"), urlencode(kept), fragment))


def anchors(paragraph):
    """Clues that survive translation: link targets, numbers, capitalised words, length."""
    text = BeautifulSoup(paragraph.html, "html.parser").get_text(" ")
    links = {target for target in map(link_target, paragraph.attrs.values()) if target}
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
    """What the alignment found, by the position of each English paragraph: the translated
    paragraph it lines up with (None where the translation has nothing for it: a hand correction
    says so, or the previous paragraph's translation covers it; absent where the alignment found
    nothing), and the positions matched only weakly.

    Positions, not text, so two English paragraphs that read the same (a repeated "Learn more"
    with different links) each keep their own translation."""

    english: list
    translations: dict
    doubtful: set
    claimed: set = field(default_factory=set)

    def claim(self, key):
        """The position of the next English paragraph reading `key` that no page string has
        taken yet, or None. The page's strings and the WordPress paragraphs run in the same
        order, so repeated text goes to its own occurrence."""
        for position, paragraph in enumerate(self.english):
            if position not in self.claimed and paragraph.key == key:
                self.claimed.add(position)
                return position
        return None

    def find(self, key):
        """The position of the first English paragraph reading `key`, or None, without claiming
        it: for a page field outside the body (a description, alt text) that repeats a paragraph."""
        return next((position for position, paragraph in enumerate(self.english) if paragraph.key == key), None)


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
            translations[row - 1] = translated[column - 1]
            if score(english_anchors[row - 1], translated_anchors[column - 1]) < WEAK_MATCH:
                doubtful.add(row - 1)
            row, column = row - 1, column - 1
        elif step == "join":
            translations[row - 1] = join_paragraphs([translated[column - 2], translated[column - 1]])
            doubtful.add(row - 1)
            row, column = row - 1, column - 2
        elif step == "split":
            translations[row - 2] = translated[column - 1]
            translations[row - 1] = None
            doubtful.add(row - 2)
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
                    doubtful.add(nearby_row - 1)
    return Alignment(english, translations, doubtful)


def join_paragraphs(parts):
    """One paragraph from several, as English joins them: a line break between, and the links
    renumbered so each keeps its own target."""
    pieces, attrs, number = [], {}, 0
    for part in parts:
        soup = BeautifulSoup(part.html, "html.parser")
        for link in soup.find_all("a"):
            number += 1
            attrs[f"a{number}"] = part.attrs.get(link.get("id"), {})
            link.attrs = {"id": f"a{number}"}
        pieces.append(str(soup))
    return Paragraph("<br/>".join(pieces), attrs)


def apply_corrections(alignment, english, translated, corrections):
    """Apply hand corrections: [{"en": start of an English paragraph, "tr": start of a translated
    one, a list of starts to join, or None for nothing}]. Returns the corrections that matched
    nothing, so they can be reported."""
    unmatched = []
    for correction in corrections:
        position = next((position for position, paragraph in enumerate(english) if paragraph.key.startswith(normalise(correction["en"]))), None)
        if position is None:
            unmatched.append(correction)
            continue
        alignment.doubtful.discard(position)
        if correction["tr"] is None:
            alignment.translations[position] = None
            continue
        starts = correction["tr"] if isinstance(correction["tr"], list) else [correction["tr"]]
        parts = [next((paragraph for paragraph in translated if paragraph.key.startswith(normalise(start))), None) for start in starts]
        if None in parts:
            unmatched.append(correction)
            continue
        alignment.translations[position] = parts[0] if len(parts) == 1 else join_paragraphs(parts)
    return unmatched


def with_english_links(translated, english_attrs, wordpress_attrs=None):
    """The translated paragraph's HTML in the form wagtail-localize ingests: each link carries
    the id of the English link to the same target, the only links a translated string can have.

    `wordpress_attrs` are the links of the same English paragraph as WordPress has it. The
    importer rewrote links between imported posts to this site's paths, so a translated link
    is compared with the WordPress address of the English link instead, link for link, when
    the two versions of the paragraph have the same number of links.

    Links to targets the English has are paired by target. Those left over are paired by
    position when the two sides have the same number left, and otherwise unwrapped, keeping
    their text. Returns the HTML, how many links were unwrapped, and whether any pairing was
    a guess worth checking (by position, or between English links to the same target)."""
    soup = BeautifulSoup(translated.html, "html.parser")
    for link in soup.find_all("a"):
        if link.find_parent("a"):
            link.unwrap()
    for tag in soup.find_all(["strong", "em", "b", "i"]):
        if tag.parent is not None and tag.parent.name == tag.name and len(tag.parent.contents) == 1:
            tag.parent.unwrap()

    english_targets = {link_id: link_target(attrs) for link_id, attrs in english_attrs.items() if link_target(attrs)}
    wordpress_targets = [target for target in map(link_target, (wordpress_attrs or {}).values()) if target]
    if len(wordpress_targets) == len(english_targets):
        english_targets = dict(zip(english_targets, wordpress_targets))
    links = soup.find_all("a")
    english_ids = [None] * len(links)
    guessed = False
    for number, link in enumerate(links):
        target = link_target(translated.attrs.get(link.get("id"), {}))
        candidates = [link_id for link_id, english_target in english_targets.items() if english_target == target and link_id not in english_ids]
        if candidates:
            english_ids[number] = candidates[0]
            # Two English links to one target: either could be the right one.
            guessed = guessed or len(candidates) > 1
    unpaired_links = [number for number, link_id in enumerate(english_ids) if link_id is None]
    unpaired_ids = [link_id for link_id in english_targets if link_id not in english_ids]
    if unpaired_links and len(unpaired_links) == len(unpaired_ids):
        guessed = True
        for number, link_id in zip(unpaired_links, unpaired_ids):
            english_ids[number] = link_id

    dropped = 0
    for link, link_id in zip(links, english_ids):
        if link_id is None:
            link.unwrap()
            dropped += 1
        else:
            link.attrs = {"id": link_id}
    return str(soup), dropped, guessed


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
