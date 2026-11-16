# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.fixtures.block_factories import rich_text
from springfield.cms.models import FreeFormPage2026

SAMPLE_RICH_TEXT = (
    '<h2 data-block-key="rt0001">This is a Rich Text block</h2>'
    '<p data-block-key="rt0002">Use it for free-form prose that does not fit a more specific block: a few paragraphs of '
    "explanation, terms and conditions, or editorial copy. It supports <b>bold</b>, <i>italic</i>, and "
    '<a href="https://www.mozilla.org/">inline links</a>.</p>'
    '<h3 data-block-key="rt0003">Headings keep long copy scannable</h3>'
    '<p data-block-key="rt0004">Break walls of text into sections. Reach for a purpose-built block (Section, Media + Content, '
    "Cards) when you need layout, media, or buttons — the Rich Text block is only text.</p>"
    '<ul><li data-block-key="rt0005">Bulleted lists for unordered points</li>'
    '<li data-block-key="rt0006">Keep each item short and parallel</li></ul>'
    '<ol><li data-block-key="rt0007">Numbered lists for steps or ranked items</li>'
    '<li data-block-key="rt0008">Readers can refer back to a number</li></ol>'
)


def get_rich_text_variants() -> list[dict]:
    return [rich_text("2026rt01-0000-0000-0000-000000000001", SAMPLE_RICH_TEXT)]


def get_rich_text_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-rich-text",
        parent=index_page,
        defaults={"title": "Rich Text"},
    )

    page.content = get_rich_text_variants()
    page.docs = (
        "<p>The Rich Text block is a plain prose block: headings, paragraphs, bold and italic, links, and bulleted "
        "or numbered lists. Use it for copy that has no media or layout of its own.</p>"
        "<p>When you need an image, buttons, or a specific layout, wrap the copy in a Section or another purpose-built "
        "block instead of styling it by hand here.</p>"
    )
    page.save_revision().publish()
    return page
