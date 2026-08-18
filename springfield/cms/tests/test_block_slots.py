# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from springfield.cms.block_slots import are_alternatives, build_slots, has_heading, is_conditional
from springfield.cms.fixtures.conditional_display_fixtures import make_show_to
from springfield.cms.models import FreeFormPage2026, ReferralHubPage


def block(block_type="banner", heading=True, headline=None, condition=None, **conditions):
    """A stand-in for a BoundBlock, carrying only what the slot logic reads."""
    value = {}
    if heading:
        value["heading"] = {"heading_text": "<p>A heading</p>"}
    if headline:
        value["headline"] = headline
    value["settings"] = {"show_to": _show_to(firefox=condition, **conditions)}
    return SimpleNamespace(block_type=block_type, value=value)


def _show_to(firefox=None, platforms=None, geo=None, auth_state="", min_version=None):
    return {
        "platforms": platforms or [],
        "firefox": firefox or "",
        "auth_state": auth_state,
        "default_browser": "",
        "min_version": min_version,
        "max_version": None,
        "geo": geo or [],
        "ai_controls": "",
        "bind_to_uitour": False,
    }


def levels(slots):
    return [slot.heading_level for slot in slots]


def positions(slots):
    return [slot.position for slot in slots]


# Heading detection


def test_has_heading_finds_nested_and_flat_forms():
    assert has_heading(block()) is True
    assert has_heading(block(heading=False, headline="<p>Flat</p>")) is True
    assert has_heading(block(heading=False)) is False


def test_has_heading_tolerates_values_without_get():
    # rich_text blocks hold a RichText, list blocks hold a list — neither has .get
    assert has_heading(SimpleNamespace(block_type="rich_text", value="<p>text</p>")) is False
    assert has_heading(SimpleNamespace(block_type="cards", value=[])) is False


def test_is_conditional_only_when_a_condition_is_set():
    assert is_conditional(block()) is False
    assert is_conditional(block(condition="is-firefox")) is True
    # stored JSON predating a field, and values that aren't structs at all
    assert is_conditional(SimpleNamespace(block_type="rich_text", value="<p>text</p>")) is False
    assert is_conditional(SimpleNamespace(block_type="banner", value={"settings": {}})) is False


# Heading levels


def test_first_heading_block_takes_the_start_level():
    slots, seen = build_slots([block(), block(), block()], start_level=1, seen_headings=0)
    assert levels(slots) == [1, 2, 2]
    assert seen == 3


def test_headingless_blocks_get_no_level_and_do_not_consume_one():
    """A block with no heading of its own has nothing to anchor to, so the block
    template picks its own default rather than inheriting the page's h1."""
    slots, _ = build_slots(
        [block(heading=False), block(), block()],
        start_level=1,
        seen_headings=0,
    )
    assert levels(slots) == [None, 1, 2]


def test_start_level_is_configurable():
    slots, _ = build_slots([block(), block()], start_level=2, seen_headings=0)
    assert levels(slots) == [2, 3]


def test_counter_carries_in_from_an_earlier_region():
    slots, _ = build_slots([block(), block()], start_level=1, seen_headings=1)
    assert levels(slots) == [2, 2]


def test_flat_level_overrides_order_and_consumes_the_counter():
    slots, seen = build_slots([block(), block()], start_level=1, seen_headings=0, flat_level=1)
    assert levels(slots) == [1, 1]
    assert seen == 1


def test_flat_region_that_is_empty_does_not_consume_the_counter():
    slots, seen = build_slots([], start_level=1, seen_headings=0, flat_level=1)
    assert slots == []
    assert seen == 0


# Conditional variants share a position


def test_consecutive_conditional_blocks_share_a_position_and_a_level():
    slots, seen = build_slots(
        [block(condition="is-firefox"), block(condition="not-firefox"), block()],
        start_level=1,
        seen_headings=0,
    )
    assert positions(slots) == [0, 0, 1]
    # whichever variant is visible is the page's h1; the block after them is h2
    assert levels(slots) == [1, 1, 2]
    assert seen == 2


def test_a_conditional_block_after_an_unconditional_one_starts_its_own_position():
    slots, _ = build_slots(
        [block(), block(condition="is-firefox"), block(condition="not-firefox")],
        start_level=1,
        seen_headings=0,
    )
    assert positions(slots) == [0, 1, 1]
    assert levels(slots) == [1, 2, 2]


def test_unconditional_block_between_variants_breaks_the_run():
    slots, _ = build_slots(
        [block(condition="is-firefox"), block(), block(condition="not-firefox")],
        start_level=1,
        seen_headings=0,
    )
    assert positions(slots) == [0, 1, 2]


def test_index_stays_raw_for_analytics():
    slots, _ = build_slots(
        [block(condition="is-firefox"), block(condition="not-firefox")],
        start_level=1,
        seen_headings=0,
    )
    # positions collapse, but analytics still needs to tell the variants apart
    assert [slot.index for slot in slots] == [1, 2]
    assert positions(slots) == [0, 0]


# Only genuine alternatives share a position


def test_opposite_values_of_one_condition_are_alternatives():
    assert are_alternatives(block(condition="is-firefox"), block(condition="not-firefox")) is True
    assert are_alternatives(block(platforms=["windows"]), block(platforms=["osx", "linux"])) is True
    assert are_alternatives(block(geo=["US"]), block(geo=["CA"])) is True


def test_blocks_differing_on_two_conditions_are_not_alternatives():
    # a Windows visitor running Firefox matches both, so they are sequential
    assert are_alternatives(block(platforms=["windows"]), block(condition="is-firefox")) is False


def test_overlapping_values_are_not_alternatives():
    assert are_alternatives(block(platforms=["windows"]), block(platforms=["windows", "osx"])) is False


def test_an_open_condition_is_not_an_alternative():
    # an empty value means "no restriction", so it also matches the other's audience
    assert are_alternatives(block(condition="is-firefox"), block(auth_state="state-fxa-supported-signed-in")) is False


def test_unconditional_blocks_are_never_alternatives():
    assert are_alternatives(block(), block()) is False
    assert are_alternatives(block(condition="is-firefox"), block()) is False


def test_compatible_adjacent_conditionals_keep_separate_positions():
    """The regression this rule exists for: both are visible to a Windows Firefox user,
    so collapsing them would put two h1s on the page."""
    slots, _ = build_slots(
        [block(platforms=["windows"]), block(condition="is-firefox")],
        start_level=1,
        seen_headings=0,
    )
    assert positions(slots) == [0, 1]
    assert levels(slots) == [1, 2]


def test_a_third_variant_joins_only_if_it_excludes_the_whole_run():
    exclusive = [block(platforms=["windows"]), block(platforms=["osx"]), block(platforms=["linux"])]
    assert positions(build_slots(exclusive, start_level=1, seen_headings=0)[0]) == [0, 0, 0]

    # the third overlaps the first, so it starts a new position
    overlapping = [block(platforms=["windows"]), block(platforms=["osx"]), block(platforms=["windows", "linux"])]
    assert positions(build_slots(overlapping, start_level=1, seen_headings=0)[0]) == [0, 0, 1]


# How it renders


def banner_block(block_id, heading, condition=None):
    return {
        "type": "banner",
        "value": {
            "settings": {
                "theme": "default",
                "media_after": False,
                "show_to": make_show_to(firefox=condition or ""),
                "anchor_id": "",
            },
            "media": [],
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="{block_id}">{heading}</p>',
                "subheading_text": "",
            },
            "content": [],
        },
        "id": f"{block_id}-0000-0000-0000-000000000001",
    }


def heading_tags(soup, region_class):
    region = soup.find("div", class_=region_class)
    return [el.name for el in region.find_all(["h1", "h2", "h3"], class_="fl-heading")]


@pytest.mark.django_db
def test_conditional_variants_of_the_hero_all_render_as_h1(minimal_site, rf):
    """Only one variant is ever visible, so each must be the page's h1 in its own right.

    By document order the second variant would be an h2, leaving a visitor who sees it
    on a page whose top heading is an h2 and whose h1 is in a hidden div.
    """
    page = FreeFormPage2026(slug="variant-headings", title="Variant headings")
    minimal_site.root_page.add_child(instance=page)
    page.upper_content = [
        banner_block("varfx001", "Firefox only", condition="is-firefox"),
        banner_block("varnfx01", "Everyone else", condition="not-firefox"),
        banner_block("varplain", "Not a variant"),
    ]
    page.save_revision().publish()

    soup = BeautifulSoup(page.serve(rf.get(page.get_full_url())).content, "html.parser")
    assert heading_tags(soup, "fl-split-page-upper") == ["h1", "h1", "h2"]


@pytest.mark.django_db
def test_unconditional_blocks_still_get_sequential_levels(minimal_site, rf):
    page = FreeFormPage2026(slug="plain-headings", title="Plain headings")
    minimal_site.root_page.add_child(instance=page)
    page.upper_content = [
        banner_block("plain001", "First"),
        banner_block("plain002", "Second"),
    ]
    page.save_revision().publish()

    soup = BeautifulSoup(page.serve(rf.get(page.get_full_url())).content, "html.parser")
    assert heading_tags(soup, "fl-split-page-upper") == ["h1", "h2"]


def showcase_block(block_id, headline):
    return {
        "type": "showcase",
        "value": {
            "settings": {"layout": "expanded"},
            "headline": f'<p data-block-key="{block_id}">{headline}</p>',
            "media": [],
        },
        "id": f"{block_id}-0000-0000-0000-000000000001",
    }


@pytest.mark.django_db
def test_referral_hub_keeps_its_separate_heading_counters(minimal_site, rf):
    """extra_content restarts the count, so the hub still renders two h1s.

    That is a pre-existing bug with its own cause — the template opened a second Jinja
    namespace, nothing to do with conditional variants — and fixing it would resize the
    pre-footer heading, since showcase derives its size class from the level. Pinned
    here so this PR is provably not the thing that changed it.
    """
    page = ReferralHubPage(slug="hub-headings", title="Hub headings")
    minimal_site.root_page.add_child(instance=page)
    page.upper_content = [showcase_block("hubupper", "Upper")]
    page.extra_content = [showcase_block("hubextra", "Extra")]
    page.save_revision().publish()

    # The hub 404s without a well-formed ref_key, and referral_geo_check redirects
    # visitors outside FF_REFERRAL_COUNTRY_CODES. Pin the country rather than relying on
    # the DEV-only fallback in get_country_from_header, which is absent on CI.
    request = rf.get(f"{page.get_full_url()}?ref_key=TESTABCDEFGHJKMN")
    with patch("springfield.cms.models.pages.get_country_from_request", return_value="US"):
        response = page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")
    assert len(soup.find_all("h1", class_="fl-heading")) == 2
    assert heading_tags(soup, "fl-split-page-extra") == ["h1"]
