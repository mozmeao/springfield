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
    join_paragraphs,
    link_target,
    media,
    normalise,
    paragraphs,
    same_in_every_language,
    with_english_links,
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

    assert result.translations == dict(enumerate(translated))
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

    assert result.translations[1] == join_paragraphs([translated[1], translated[2]])
    assert result.translations[0] == translated[0]
    assert result.translations[2] == translated[3]
    assert 1 in result.doubtful


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

    assert 1 not in result.translations
    assert result.translations[0] == translated[0]
    assert result.translations[2] == translated[1]
    assert {0, 2} <= result.doubtful


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

    assert result.translations == {0: translated[0]}


def test_align_reports_a_pair_whose_clues_disagree_as_doubtful():
    # The English links where the translation doesn't; pairing still beats two gaps.
    english = [
        linked("Firefox keeps your passwords safe and fills them in on every site you visit", "https://support.mozilla.org/en-US/kb/passwords")
    ]
    translated = [Paragraph("Firefox schützt Ihre Passwörter und füllt sie auf jeder Website für Sie aus.")]

    result = align(english, translated)

    assert result.translations == {0: translated[0]}
    assert result.doubtful == {0}


def test_align_marks_an_english_paragraph_absorbed_into_the_previous_translation_as_nothing():
    english = [
        linked("Firefox 130 is out today with new features for everyone", "https://www.mozilla.org/en-US/firefox/130.0/releasenotes/"),
        linked("Get it", "https://www.mozilla.org/en-US/firefox/new/"),
    ]
    translated = [
        Paragraph(
            'Firefox 130 erscheint heute mit neuen Funktionen für alle, <a id="a1">hier</a> die Versionshinweise, und <a id="a2">hier</a> laden.',
            {"a1": {"href": "https://www.mozilla.org/de/firefox/130.0/releasenotes/"}, "a2": {"href": "https://www.mozilla.org/de/firefox/new/"}},
        )
    ]

    result = align(english, translated)

    assert result.translations == {0: translated[0], 1: None}


def test_align_keeps_repeated_english_paragraphs_apart():
    english = [
        linked("Learn more", "https://www.mozilla.org/en-US/firefox/features/"),
        Paragraph("Firefox keeps your passwords safe and fills them in for you on every site."),
        linked("Learn more", "https://support.mozilla.org/en-US/kb/passwords"),
    ]
    translated = [
        linked("Mehr erfahren", "https://www.mozilla.org/de/firefox/features/"),
        Paragraph("Firefox schützt Ihre Passwörter und füllt sie auf jeder Website für Sie aus."),
        linked("Mehr erfahren", "https://support.mozilla.org/de/kb/passwords"),
    ]

    result = align(english, translated)

    assert result.translations == dict(enumerate(translated))
    assert result.claim(english[0].key) == 0
    assert result.claim(english[0].key) == 2
    assert result.claim(english[0].key) is None
    assert result.find(english[0].key) == 0


def test_join_paragraphs_keeps_each_link_its_own_target():
    joined = join_paragraphs([linked("Erstens", "https://example.com/one"), linked("Zweitens", "https://example.com/two")])

    assert joined.html == 'Erstens <a id="a1">here</a>.<br/>Zweitens <a id="a2">here</a>.'
    assert joined.attrs == {"a1": {"href": "https://example.com/one"}, "a2": {"href": "https://example.com/two"}}


@pytest.fixture
def corrected():
    english = [Paragraph("First English paragraph."), Paragraph("Second English paragraph."), Paragraph("Third English paragraph.")]
    translated = [Paragraph("Erster Absatz."), Paragraph("Zweiter Absatz, Teil eins."), Paragraph("Zweiter Absatz, Teil zwei.")]
    alignment = Alignment(english, {0: Paragraph("<b>wrong</b>")}, {0, 1, 2})
    return alignment, english, translated


def test_apply_corrections_sets_a_paragraph(corrected):
    alignment, english, translated = corrected

    unmatched = apply_corrections(alignment, english, translated, [{"en": "First English", "tr": "Erster"}])

    assert unmatched == []
    assert alignment.translations[0] == translated[0]
    assert 0 not in alignment.doubtful


def test_apply_corrections_joins_a_list_of_paragraphs(corrected):
    alignment, english, translated = corrected

    apply_corrections(alignment, english, translated, [{"en": "Second", "tr": ["Zweiter Absatz, Teil eins", "Zweiter Absatz, Teil zwei"]}])

    assert alignment.translations[1].html == "Zweiter Absatz, Teil eins.<br/>Zweiter Absatz, Teil zwei."
    assert 1 not in alignment.doubtful


def test_apply_corrections_null_leaves_a_paragraph_without_translation(corrected):
    alignment, english, translated = corrected

    apply_corrections(alignment, english, translated, [{"en": "Third", "tr": None}])

    assert 2 in alignment.translations
    assert alignment.translations[2] is None
    assert 2 not in alignment.doubtful


def test_apply_corrections_returns_the_corrections_that_match_nothing(corrected):
    alignment, english, translated = corrected
    no_english = {"en": "Not in the post", "tr": "Erster"}
    no_translation = {"en": "First", "tr": ["Erster", "Nicht im Beitrag"]}

    unmatched = apply_corrections(alignment, english, translated, [no_english, no_translation])

    assert unmatched == [no_english, no_translation]
    assert alignment.translations[0] == Paragraph("<b>wrong</b>")


def test_link_target_keeps_query_parameters_that_pick_the_destination_and_drops_tracking():
    assert (
        link_target({"href": "https://www.mozilla.org/de/firefox/download/?os=mac&utm_source=blog"}) == "https://mozilla.org/firefox/download?os=mac"
    )
    assert (
        link_target({"href": "https://www.mozilla.org/en-US/firefox/download/?utm_source=blog&os=mac"})
        == "https://mozilla.org/firefox/download?os=mac"
    )
    assert link_target({"href": "https://mozilla.org/firefox/download/?os=win"}) != link_target(
        {"href": "https://mozilla.org/firefox/download/?os=mac"}
    )
    assert link_target({"class": ["x"]}) is None


def test_link_target_keeps_the_fragment():
    assert link_target({"href": "#note-1"}) == "#note-1"
    assert link_target({"href": "https://example.com/post/#note-1"}) != link_target({"href": "https://example.com/post/#note-2"})


def test_with_english_links_keeps_a_footnote_link():
    translated = Paragraph('Siehe <a id="a1">1</a>.', {"a1": {"href": "#note-1"}})

    html, dropped, guessed = with_english_links(translated, {"a1": {"href": "#note-1"}})

    assert html == 'Siehe <a id="a1">1</a>.'
    assert dropped == 0


def test_with_english_links_tells_links_apart_by_query_string_and_flags_a_tie():
    download = "https://www.mozilla.org/en-US/firefox/download/"
    english = {"a1": {"href": f"{download}?os=win"}, "a2": {"href": f"{download}?os=mac"}, "a3": {"href": f"{download}?os=mac&utm_source=x"}}
    translated = Paragraph('<a id="a1">Für Mac</a>', {"a1": {"href": "https://www.mozilla.org/de/firefox/download/?os=mac"}})

    html, dropped, guessed = with_english_links(translated, english)

    assert html == '<a id="a2">Für Mac</a>'
    assert guessed  # a2 and a3 both go to the Mac download


ENGLISH_LINKS = {"a1": {"href": "https://www.mozilla.org/en-US/firefox/130.0/releasenotes/"}, "a2": {"href": "https://support.mozilla.org/en-US/"}}


def test_with_english_links_pairs_links_by_target_not_position():
    # The translation links only Support; by position it would get the release notes URL.
    translated = Paragraph('Mehr in der <a id="a1">Hilfe</a>.', {"a1": {"href": "https://support.mozilla.org/de/"}})

    html, dropped, guessed = with_english_links(translated, ENGLISH_LINKS)

    assert html == 'Mehr in der <a id="a2">Hilfe</a>.'
    assert dropped == 0
    assert not guessed


def test_with_english_links_unwraps_links_it_cannot_place():
    # One target matches; two translated links are left for one English id, so neither is guessed.
    translated = Paragraph(
        '<a id="a1">Hilfe</a>, <a id="a2">mehr</a> und <a id="a3">noch mehr</a>',
        {"a1": {"href": "https://support.mozilla.org/de/"}, "a2": {"href": "https://example.com/"}, "a3": {"href": "https://example.org/"}},
    )

    html, dropped, guessed = with_english_links(translated, ENGLISH_LINKS)

    assert html == '<a id="a2">Hilfe</a>, mehr und noch mehr'
    assert dropped == 2
    assert not guessed


def test_with_english_links_pairs_leftover_links_by_position_and_says_so():
    translated = Paragraph(
        '<a id="a1">Versionshinweise</a> und <a id="a2">Hilfe</a>',
        {
            "a1": {"href": "https://www.mozilla.org/de/firefox/130.0/releasenotes/"},
            "a2": {"href": "https://support.mozilla.org/de/kb/hilfe-auf-deutsch"},
        },
    )

    html, dropped, guessed = with_english_links(translated, ENGLISH_LINKS)

    assert html == '<a id="a1">Versionshinweise</a> und <a id="a2">Hilfe</a>'
    assert dropped == 0
    assert guessed


def test_with_english_links_unwraps_nested_links_and_doubled_tags():
    translated = Paragraph(
        '<a id="a1"><a id="a2">Firefox</a> holen</a> <em><em>lesen</em></em>',
        {"a1": {"href": "https://support.mozilla.org/de/"}, "a2": {"href": "https://example.com/"}},
    )

    html, dropped, guessed = with_english_links(translated, ENGLISH_LINKS)

    assert html == '<a id="a2">Firefox holen</a> <em>lesen</em>'
    assert dropped == 0


def test_paragraphs_drops_the_attributes_wordpress_puts_on_inline_tags():
    found = paragraphs('<p>Mit <strong class="has-inline-color">Funktionen</strong>, die <a href="https://example.com/">helfen</a>.</p>')

    assert found[0].html == 'Mit <strong>Funktionen</strong>, die <a id="a1">helfen</a>.'
    assert found[0].attrs == {"a1": {"href": "https://example.com/"}}


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
