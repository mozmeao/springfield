# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError

import pytest
from wagtail.blocks import StreamBlockValidationError
from wagtail.models import Locale

from springfield.blog.blocks import BlogCardsListBlock, BlogCardsListSourceBlock, BlogLatestArticlesBlock
from springfield.blog.models.snippets import BlogTag, BlogTopic


def test_cards_list_source_requires_exactly_one_choice():
    """A section draws from one topic or one tag, never from nothing."""
    block = BlogCardsListSourceBlock()

    with pytest.raises(StreamBlockValidationError):
        block.clean(block.to_python([]))


@pytest.mark.django_db
def test_cards_list_source_rejects_two_choices():
    locale = Locale.get_default()
    topic = BlogTopic.objects.create(name="Privacy", slug="test-block-privacy", locale=locale)
    tag = BlogTag.objects.create(name="VPN", slug="test-block-vpn", locale=locale)
    block = BlogCardsListSourceBlock()
    value = block.to_python(
        [
            {"type": "topic", "value": topic.pk, "id": "src00001-0000-0000-0000-000000000001"},
            {"type": "tag", "value": tag.pk, "id": "src00002-0000-0000-0000-000000000002"},
        ]
    )

    with pytest.raises(StreamBlockValidationError):
        block.clean(value)


def test_latest_articles_count_allows_eight():
    """The latest section is expected to run to a second row."""
    block = BlogLatestArticlesBlock()

    assert block.child_blocks["count"].clean(8) == 8


def test_latest_section_exempts_nothing():
    """The latest section has no source of its own, so no exclusion is spared."""
    block = BlogLatestArticlesBlock()

    assert block.get_exempt_exclusions(None) == (set(), set())


def test_cards_list_count_rejects_five():
    """article_card_media only has tuned image sizes for grids of 2-4."""
    block = BlogCardsListBlock()

    with pytest.raises(ValidationError):
        block.child_blocks["count"].clean(5)


def test_section_with_an_empty_source_exempts_nothing():
    """min_num only holds while the form is cleaned, so stored data can arrive empty."""
    block = BlogCardsListBlock()
    value = block.to_python(
        {
            "heading_text": '<p data-block-key="h">Privacy</p>',
            "source": [],
            "count": 4,
            "link_label": "View all",
        }
    )

    assert block.get_exempt_exclusions(value) == (set(), set())


@pytest.mark.django_db
def test_section_with_a_deleted_source_exempts_nothing():
    """A chooser reads a deleted snippet back as None, and a section that no longer
    has a source cannot exempt anything."""
    topic = BlogTopic.objects.create(name="Privacy", slug="test-block-deleted", locale=Locale.get_default())
    deleted_pk = topic.pk
    topic.delete()
    block = BlogCardsListBlock()
    value = block.to_python(
        {
            "heading_text": '<p data-block-key="h">Privacy</p>',
            "source": [{"type": "topic", "value": deleted_pk, "id": "src00005-0000-0000-0000-000000000005"}],
            "count": 4,
            "link_label": "View all",
        }
    )

    assert value["source"][0].value is None
    assert block.get_exempt_exclusions(value) == (set(), set())


@pytest.mark.django_db
def test_topic_section_exempts_its_own_topic():
    topic = BlogTopic.objects.create(name="Privacy", slug="test-block-exempt", locale=Locale.get_default())
    block = BlogCardsListBlock()
    value = block.to_python(
        {
            "heading_text": '<p data-block-key="h">Privacy</p>',
            "source": [{"type": "topic", "value": topic.pk, "id": "src00004-0000-0000-0000-000000000004"}],
            "count": 4,
            "link_label": "View all",
        }
    )

    topic_keys, tag_keys = block.get_exempt_exclusions(value)

    assert topic_keys == {topic.translation_key}
    assert tag_keys == set()
