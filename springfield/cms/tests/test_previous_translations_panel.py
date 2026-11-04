# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.cms.previous_translations import PreviousTranslation
from springfield.cms.side_panels import PreviousTranslationsSidePanel


def previous_translation(translation):
    return PreviousTranslation(
        source_then="Get Firefox",
        source_now="Get Firefox!",
        translation=translation,
        comment="Translated manually on 1 January 2026",
        translated_by="Jo Bloggs",
    )


@pytest.fixture
def entries():
    return [previous_translation("Obtenez Firefox"), previous_translation("Téléchargez Firefox")]


@pytest.fixture
def panel(rf, entries):
    """A panel built around a stand-in object, which it only ever hands to Wagtail."""
    return PreviousTranslationsSidePanel(object(), rf.get("/"), entries=entries, source_locale="en-US", target_locale="fr")


def test_toggle_counts_the_entries(panel, entries):
    assert panel.toggle.get_context_data({})["count"] == len(entries)


def test_toggle_keeps_the_context_its_template_reads(panel):
    """
    side_panel_toggle.html reads toggle.aria_label, toggle.icon_name, panel.name and
    panel.title from this context. Replacing it rather than extending it renders a
    nameless, iconless button that the side panel JS cannot bind to.
    """
    context = panel.toggle.get_context_data({})

    assert context["toggle"] is panel.toggle
    assert context["panel"] is panel


def test_panel_passes_the_entries_and_locale_codes_to_its_template(panel, entries):
    context = panel.get_context_data({})

    assert context["entries"] == entries
    assert context["source_locale"] == "en-US"
    assert context["target_locale"] == "fr"


def test_panel_keeps_the_context_its_template_reads(panel):
    """side_panel.html reads panel.title to label the panel for screen readers."""
    assert panel.get_context_data({})["panel"] is panel
