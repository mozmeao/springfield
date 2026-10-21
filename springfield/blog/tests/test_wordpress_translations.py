# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.blog.wordpress_translations import (
    Alignment,
    Media,
    Paragraph,
    align,
    apply_corrections,
    file_stem,
    first_words,
    keep_links,
    media,
    normalise,
    paragraphs,
    same_in_every_language,
    tidy,
)

pytestmark = [pytest.mark.django_db]


def linked(text, href, link_text="here"):
    """A paragraph with one link, as wagtail-localize cuts it."""
    return Paragraph(f'{text} <a id="a1">{link_text}</a>.', {"a1": {"href": href}})


def test_normalise_folds_curly_quotes_dashes_and_non_breaking_spaces():
    assert normalise("<p>It’s “quoted” – and — ‘done’…\xa0Now</p>") == "it's \"quoted\" - and - 'done'... now"


def test_normalise_unescapes_entities_and_collapses_whitespace():
    assert normalise("<p>Fish &amp;\n   <b>chips</b></p>") == "fish & chips"


def test_paragraphs_cuts_one_string_per_paragraph_with_its_links():
    found = paragraphs('<p>First paragraph.</p><p>Read <a href="https://example.com/">this</a>.</p><p>&nbsp;</p>')

    assert [paragraph.html for paragraph in found] == ["First paragraph.", 'Read <a id="a1">this</a>.']
    assert found[1].attrs == {"a1": {"href": "https://example.com/"}}


def test_align_pairs_paragraphs_one_to_one():
    english = [
        linked("Firefox 130 is out today with new features", "https://www.mozilla.org/en-US/firefox/130.0/releasenotes/"),
        Paragraph("Mozilla has been building Firefox for 20 years, and we keep going."),
        linked("Download Firefox", "https://www.mozilla.org/en-US/firefox/new/"),
    ]
    translated = [
        linked("Firefox 130 erscheint heute mit neuen Funktionen", "https://www.mozilla.org/de/firefox/130.0/releasenotes/"),
        Paragraph("Mozilla entwickelt Firefox seit 20 Jahren, und wir machen weiter."),
        linked("Firefox herunterladen", "https://www.mozilla.org/de/firefox/new/"),
    ]

    result = align(english, translated)

    assert result.translations == {
        english_paragraph.key: translated_paragraph.html for english_paragraph, translated_paragraph in zip(english, translated)
    }
    assert result.doubtful == set()


def test_align_joins_two_translated_paragraphs_when_the_translation_splits_one():
    english = [
        linked("Firefox 130 is out", "https://www.mozilla.org/en-US/firefox/130.0/releasenotes/"),
        linked(
            "Translations now work offline in every language we support, and they never leave your device, so your pages stay private",
            "https://support.mozilla.org/en-US/kb/website-translation",
        ),
        linked("Download Firefox", "https://www.mozilla.org/en-US/firefox/new/"),
    ]
    translated = [
        linked("Firefox 130 ist da", "https://www.mozilla.org/de/firefox/130.0/releasenotes/"),
        linked("Übersetzungen funktionieren jetzt offline in jeder unterstützten Sprache", "https://support.mozilla.org/de/kb/website-translation"),
        Paragraph("Sie verlassen nie Ihr Gerät, sodass Ihre Seiten privat bleiben."),
        linked("Firefox herunterladen", "https://www.mozilla.org/de/firefox/new/"),
    ]

    result = align(english, translated)

    assert result.translations[english[1].key] == translated[1].html + "<br/>" + translated[2].html
    assert result.translations[english[0].key] == translated[0].html
    assert result.translations[english[2].key] == translated[3].html
    assert english[1].key in result.doubtful


def test_align_leaves_a_gap_for_a_paragraph_only_english_has_and_doubts_its_neighbours():
    english = [
        linked("Firefox 130 is out", "https://www.mozilla.org/en-US/firefox/130.0/releasenotes/"),
        linked("Read more about it on our community forum", "https://discourse.mozilla.org/"),
        linked("Download Firefox", "https://www.mozilla.org/en-US/firefox/new/"),
    ]
    translated = [
        linked("Firefox 130 ist da", "https://www.mozilla.org/de/firefox/130.0/releasenotes/"),
        linked("Firefox herunterladen", "https://www.mozilla.org/de/firefox/new/"),
    ]

    result = align(english, translated)

    assert english[1].key not in result.translations
    assert result.translations[english[0].key] == translated[0].html
    assert result.translations[english[2].key] == translated[1].html
    assert {english[0].key, english[2].key} <= result.doubtful


def test_align_ignores_capitalised_words_only_the_translation_uses():
    # German capitalises every noun. Counted as names, they would sink this pair below the
    # cost of leaving both paragraphs unmatched; only names both versions use count.
    english = [Paragraph("We counted 1, 2 and 3 of them.")]
    translated = [
        Paragraph(
            "Wir haben 1, 4, 5 und 6 Stück davon gezählt, Datenschutz Einstellungen Browser Lesezeichen Passwörter Erweiterungen "
            "Fenster Tabs Verlauf Suchmaschine Startseite Downloads und Sicherheit in der Übersicht."
        )
    ]

    result = align(english, translated)

    assert result.translations == {english[0].key: translated[0].html}
    assert result.doubtful == set()


@pytest.fixture
def corrected():
    english = [Paragraph("First English paragraph."), Paragraph("Second English paragraph."), Paragraph("Third English paragraph.")]
    translated = [Paragraph("Erster Absatz."), Paragraph("Zweiter Absatz, Teil eins."), Paragraph("Zweiter Absatz, Teil zwei.")]
    alignment = Alignment({english[0].key: "<b>wrong</b>"}, {english[0].key, english[1].key, english[2].key})
    return alignment, english, translated


def test_apply_corrections_sets_a_paragraph(corrected):
    alignment, english, translated = corrected

    unmatched = apply_corrections(alignment, english, translated, [{"en": "First English", "tr": "Erster"}])

    assert unmatched == []
    assert alignment.translations[english[0].key] == "Erster Absatz."
    assert english[0].key not in alignment.doubtful


def test_apply_corrections_joins_a_list_of_paragraphs(corrected):
    alignment, english, translated = corrected

    apply_corrections(alignment, english, translated, [{"en": "Second", "tr": ["Zweiter Absatz, Teil eins", "Zweiter Absatz, Teil zwei"]}])

    assert alignment.translations[english[1].key] == "Zweiter Absatz, Teil eins.<br/>Zweiter Absatz, Teil zwei."
    assert english[1].key not in alignment.doubtful


def test_apply_corrections_null_leaves_a_paragraph_without_translation(corrected):
    alignment, english, translated = corrected

    apply_corrections(alignment, english, translated, [{"en": "Third", "tr": None}])

    assert english[2].key in alignment.translations
    assert alignment.translations[english[2].key] is None
    assert english[2].key not in alignment.doubtful


def test_apply_corrections_returns_the_corrections_that_match_nothing(corrected):
    alignment, english, translated = corrected
    no_english = {"en": "Not in the post", "tr": "Erster"}
    no_translation = {"en": "First", "tr": ["Erster", "Nicht im Beitrag"]}

    unmatched = apply_corrections(alignment, english, translated, [no_english, no_translation])

    assert unmatched == [no_english, no_translation]
    assert alignment.translations[english[0].key] == "<b>wrong</b>"


def test_tidy_unwraps_nested_links_and_renumbers_them_in_order():
    translated = '<a id="a4" href="x"><a id="a7">Firefox</a> holen</a> und <a id="a2" class="y">mehr</a> <strong><strong>lesen</strong></strong>'

    assert tidy(translated) == '<a id="a1">Firefox holen</a> und <a id="a2">mehr</a> <strong>lesen</strong>'


def test_keep_links_unwraps_links_the_english_string_does_not_have():
    assert keep_links('<a id="a1">Firefox</a> und <a id="a2">mehr</a>', {"a1"}) == '<a id="a1">Firefox</a> und mehr'


def test_media_finds_images_and_youtube_videos_in_document_order():
    post = (
        '<figure><img src="https://blog.mozilla.org/wp-content/uploads/one.png" alt="First"></figure>'
        '<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk?rel=0"></iframe>'
        '<p><a href="https://youtu.be/ABCDEFGHIJK">https://youtu.be/ABCDEFGHIJK</a></p>'
        '<p><a href="https://youtu.be/zzzzzzzzzzz">a link that names the video</a></p>'
        '<img src="https://blog.mozilla.org/wp-content/uploads/two.png">'
    )

    assert media(post) == [
        Media("image", "https://blog.mozilla.org/wp-content/uploads/one.png", "First"),
        Media("video", "abcdefghijk"),
        Media("video", "ABCDEFGHIJK"),
        Media("image", "https://blog.mozilla.org/wp-content/uploads/two.png", ""),
    ]


@pytest.mark.parametrize(
    "url_or_name",
    [
        "https://blog.mozilla.org/wp-content/uploads/2024/01/Privacy-Settings-1024x576.png?resize=2",
        "https://blog.mozilla.org/wp-content/uploads/2024/01/privacy-settings.jpg",
        "original_images/privacy-settings_AbC1234.png",
    ],
)
def test_file_stem_strips_folder_size_suffix_extension_and_storage_suffix(url_or_name):
    assert file_stem(url_or_name) == "privacy-settings"


def test_same_in_every_language_is_short_or_letterless_text():
    assert same_in_every_language("<p>Firefox Focus</p>")
    assert same_in_every_language("<p>* 1, 2</p>")
    assert not same_in_every_language("<p>This paragraph has words in it.</p>")
    assert not same_in_every_language("https://www.mozilla.org/en-US/firefox/")


def test_first_words_cuts_at_a_word_boundary():
    assert first_words("<p>One two three</p>") == "One two three"
    assert first_words("<p>Alpha beta gamma</p>", limit=13) == "Alpha beta"
