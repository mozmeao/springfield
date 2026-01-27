# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.base.sanitization import sanitize_html, strip_all_tags


class TestStripAllTags:
    """Tests for the strip_all_tags function."""

    @pytest.mark.parametrize(
        "html, expected",
        [
            ("plain text", "plain text"),
            ("<p>paragraph</p>", "paragraph"),
            ("<p>nested <strong>bold</strong> text</p>", "nested bold text"),
            ("<div><p>deep <span>nesting</span></p></div>", "deep nesting"),
            ("text &amp; more", "text &amp; more"),
            ("<p>text &amp; more</p>", "text &amp; more"),
            # Script and style content is completely dropped
            ("<script>alert('xss')</script>", ""),
            ("<style>body { color: red; }</style>", ""),
            ("before<script>alert('xss')</script>after", "beforeafter"),
            ("before<style>body { color: red; }</style>after", "beforeafter"),
            # Unclosed tags
            ("<p>unclosed", "unclosed"),
            ("unclosed</p>", "unclosed"),
            # Empty input
            ("", ""),
            # Self-closing tags
            ("<br>", ""),
            ("<br/>", ""),
            ("line<br>break", "linebreak"),
            # Attributes are ignored
            ('<a href="https://example.com">link</a>', "link"),
            ('<div class="test" id="foo">content</div>', "content"),
        ],
    )
    def test_strip_all_tags(self, html, expected):
        assert strip_all_tags(html) == expected


class TestSanitizeHtml:
    """Tests for the sanitize_html function."""

    @pytest.mark.parametrize(
        "html, expected",
        [
            # Allowed tags pass through
            ("<b>bold</b>", "<b>bold</b>"),
            ("<i>italic</i>", "<i>italic</i>"),
            ("<a>link</a>", "<a>link</a>"),
            # Nested allowed tags
            ("<b><i>bold italic</i></b>", "<b><i>bold italic</i></b>"),
            # Disallowed tags are escaped
            ("<div>content</div>", "&lt;div&gt;content&lt;/div&gt;"),
            ("<span>content</span>", "&lt;span&gt;content&lt;/span&gt;"),
            # Script/style content is dropped entirely
            ("<script>alert('xss')</script>", ""),
            ("<style>body { color: red; }</style>", ""),
            ("before<script>bad</script>after", "beforeafter"),
        ],
    )
    def test_basic_sanitization(self, html, expected):
        allowed_tags = {"a", "b", "i"}
        allowed_attributes = {}
        assert sanitize_html(html, allowed_tags, allowed_attributes) == expected

    @pytest.mark.parametrize(
        "html, expected",
        [
            # Allowed attribute passes through
            ('<a href="https://example.com">link</a>', '<a href="https://example.com">link</a>'),
            # Disallowed attribute is stripped
            ('<a onclick="bad()">link</a>', "<a>link</a>"),
            # Mix of allowed and disallowed
            ('<a href="https://example.com" onclick="bad()">link</a>', '<a href="https://example.com">link</a>'),
        ],
    )
    def test_attribute_filtering(self, html, expected):
        allowed_tags = {"a"}
        allowed_attributes = {"a": ["href"]}
        assert sanitize_html(html, allowed_tags, allowed_attributes) == expected

    def test_global_attributes(self):
        """Test that '*' allows attributes on all tags."""
        allowed_tags = {"a", "span"}
        allowed_attributes = {"*": ["class", "id"]}
        html = '<a class="test" id="link1">link</a><span class="foo">text</span>'
        expected = '<a class="test" id="link1">link</a><span class="foo">text</span>'
        assert sanitize_html(html, allowed_tags, allowed_attributes) == expected

    def test_mixed_global_and_specific_attributes(self):
        """Test combining global and tag-specific attributes."""
        allowed_tags = {"a", "span"}
        allowed_attributes = {
            "*": ["class", "id"],
            "a": ["href"],
        }
        html = '<a href="https://example.com" class="link" id="link1">link</a>'
        expected = '<a href="https://example.com" class="link" id="link1">link</a>'
        assert sanitize_html(html, allowed_tags, allowed_attributes) == expected

    def test_empty_input(self):
        assert sanitize_html("", {"a"}, {}) == ""

    def test_plain_text(self):
        assert sanitize_html("plain text", {"a"}, {}) == "plain text"

    def test_entities_preserved(self):
        """Test that HTML entities are preserved."""
        assert sanitize_html("text &amp; more", {"a"}, {}) == "text &amp; more"
        assert sanitize_html("<b>&lt;escaped&gt;</b>", {"b"}, {}) == "<b>&lt;escaped&gt;</b>"


class TestUrlSchemeValidation:
    """Tests for URL scheme validation (XSS prevention)."""

    @pytest.mark.parametrize(
        "html, expected",
        [
            # javascript: URLs should be stripped
            ('<a href="javascript:alert(1)">click</a>', "<a>click</a>"),
            ('<a href="javascript:alert(document.cookie)">xss</a>', "<a>xss</a>"),
            # Case variations
            ('<a href="JAVASCRIPT:alert(1)">click</a>', "<a>click</a>"),
            ('<a href="JaVaScRiPt:alert(1)">click</a>', "<a>click</a>"),
            # data: URLs should be stripped
            ('<img src="data:text/html,<script>alert(1)</script>">', "<img>"),
            ('<a href="data:text/html,<script>alert(1)</script>">xss</a>', "<a>xss</a>"),
            # vbscript: URLs should be stripped
            ('<a href="vbscript:msgbox(1)">click</a>', "<a>click</a>"),
            # Valid URLs should pass through
            ('<a href="https://example.com">safe</a>', '<a href="https://example.com">safe</a>'),
            ('<a href="http://example.com">safe</a>', '<a href="http://example.com">safe</a>'),
            ('<a href="mailto:test@example.com">email</a>', '<a href="mailto:test@example.com">email</a>'),
            ('<a href="tel:+1234567890">call</a>', '<a href="tel:+1234567890">call</a>'),
        ],
    )
    def test_url_scheme_validation(self, html, expected):
        allowed_tags = {"a", "img"}
        allowed_attributes = {"a": ["href"], "img": ["src"]}
        assert sanitize_html(html, allowed_tags, allowed_attributes) == expected
