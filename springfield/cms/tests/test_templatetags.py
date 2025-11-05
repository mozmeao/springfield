# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

import pytest
from bs4 import BeautifulSoup
from wagtail.templatetags.wagtailcore_tags import richtext as wagtail_richtext

from springfield.cms.templatetags.cms_tags import (
    add_utm_parameters,
    remove_p_tag,
    remove_tags,
    richtext,
)


def test_remove_p_tag():
    input_html = "<p>This is a paragraph.</p><p>This is another paragraph.</p>"
    expected_output = "This is a paragraph.<br/>This is another paragraph."
    assert remove_p_tag(input_html) == expected_output


def test_remove_p_tag_with_inner_tags():
    input_html = "<p>This is a <strong>paragraph</strong>.</p><p>This is another paragraph.</p>"
    expected_output = "This is a <strong>paragraph</strong>.<br/>This is another paragraph."
    assert remove_p_tag(input_html) == expected_output


def test_remove_tags():
    input_html = "<p>This is a <strong>paragraph</strong>.</p><p>This is another paragraph.</p>"
    expected_output = "This is a paragraph.This is another paragraph."
    assert remove_tags(input_html) == expected_output


@pytest.mark.parametrize(
    "url, expected_url",
    [
        (
            "https://example.mozilla.org/page",
            "https://example.mozilla.org/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign",
        ),
        (
            "example.mozilla.org/page",
            "example.mozilla.org/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign",
        ),
        (
            "https://example.mozilla.org/page?query=something#hash",
            "https://example.mozilla.org/page"
            "?query=%5B%27something%27%5D&utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign#hash",
        ),
        (
            "https://example.mozillafoundation.org/page",
            "https://example.mozillafoundation.org/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign",
        ),
        (
            "example.mozillafoundation.org/page",
            "example.mozillafoundation.org/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign",
        ),
        (
            "https://example.firefox.com/page",
            "https://example.firefox.com/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign",
        ),
        (
            "example.firefox.com/page",
            "example.firefox.com/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign",
        ),
        ("https://www.firefox.com/page", "https://www.firefox.com/page"),
        ("www.firefox.com/page", "www.firefox.com/page"),
        ("firefox.com/page", "firefox.com/page"),
    ],
)
def test_add_utm_parameters(url, expected_url):
    context = {
        "utm_parameters": {
            "utm_source": "test_source",
            "utm_medium": "test_medium",
            "utm_campaign": "test_campaign",
        }
    }

    assert add_utm_parameters(context, url) == expected_url


def test_richtext_preserves_original_wagtail_richtext_content():
    value = """
    <h2>Header</h2>
    <p>This is a <strong>bold</strong> paragraph with <a href="https://example.com">a link</a>.</p>
    <ul>
        <li>First item</li>
        <li>Second item</li>
    </ul>
    """
    assert BeautifulSoup(richtext(context={}, value=value), "html.parser") == BeautifulSoup(wagtail_richtext(value), "html.parser")


def test_richtext_parses_fxa_tag():
    value = '<p>Paragraph with <fxa data-cta-uid="UID">FxA link</fxa>.</p>'
    context = {
        "utm_parameters": {
            "utm_source": "test_source",
            "utm_medium": "test_medium",
            "utm_campaign": "test_campaign",
        },
        "block_position": "block-1",
        "block_text": "A heading above the link",
    }
    output_html = richtext(context=context, value=value)
    expected_url = "".join(
        [
            settings.FXA_ENDPOINT,
            "signup?entrypoint=test_source-test_campaign",
            "&amp;form_type=button",
            "&amp;utm_source=test_source-test_campaign",
            "&amp;utm_medium=referral",
            "&amp;utm_campaign=test_campaign",
        ]
    )
    expected_html = f"""<p>Paragraph with <a
        class="js-fxa-cta-link js-fxa-product-button fxa-link"
        data-action="{settings.FXA_ENDPOINT}"
        data-cta-position="block-1-fxa-link"
        data-cta-text="A heading above the link"
        data-cta-uid="UID"
        href="{expected_url}"
    >FxA link</a>.</p>"""
    assert BeautifulSoup(output_html, "html.parser") == BeautifulSoup(expected_html, "html.parser")


@pytest.mark.parametrize(
    "original_url, utm_params",
    [
        (
            "https://example.mozilla.org/page",
            True,
        ),
        (
            "example.mozilla.org/page",
            True,
        ),
        (
            "example.mozillafoundation.org/page",
            True,
        ),
        (
            "example.firefox.com/page",
            True,
        ),
        (
            "https://www.firefox.com/page",
            False,
        ),
        (
            "/page",
            False,
        ),
    ],
)
def test_richtext_adds_utm_params_to_links(original_url: str, utm_params: bool):
    value = f'<p>Check out <a href="{original_url}">this page</a>.</p>'
    context = {
        "utm_parameters": {
            "utm_source": "test_source",
            "utm_medium": "test_medium",
            "utm_campaign": "test_campaign",
        }
    }
    output_html = richtext(context=context, value=value)
    if utm_params:
        expected_url = f"{original_url}?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign"
    else:
        expected_url = original_url
    expected_html = f'<p>Check out <a href="{expected_url}">this page</a>.</p>'
    assert BeautifulSoup(output_html, "html.parser") == BeautifulSoup(expected_html, "html.parser")
