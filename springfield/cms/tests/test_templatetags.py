# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.cms.templatetags.cms_tags import add_utm_parameters, remove_p_tag, remove_tags


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
        ("example.mozilla.org/page", "example.mozilla.org/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign"),
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
        ("example.firefox.com/page", "example.firefox.com/page?utm_source=test_source&utm_medium=test_medium&utm_campaign=test_campaign"),
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
