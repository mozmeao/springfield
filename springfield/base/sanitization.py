# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
HTML sanitization utilities using justhtml.

This module provides functions for sanitizing HTML content, replacing
the deprecated bleach library.
"""

import re

from justhtml import JustHTML, SanitizationPolicy, UrlPolicy, UrlRule

# Matches HTML comments. justhtml's DropComments transform cannot drop
# comments when disallowed_tag_handling="escape" is in effect, so
# we strip comments before handing the input to justhtml.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Tags whose content should be completely dropped (not just the tags)
_DROP_CONTENT_TAGS = frozenset({"script", "style"})

# URL rule for safe schemes
_URL_RULE = UrlRule(allowed_schemes=["http", "https", "mailto", "tel"])

# URL policy for allowing safe URLs in common attributes
_URL_POLICY = UrlPolicy(
    default_handling="strip",
    allow_rules={
        ("a", "href"): _URL_RULE,
        ("img", "src"): _URL_RULE,
        ("img", "srcset"): _URL_RULE,
        ("source", "src"): _URL_RULE,
        ("video", "src"): _URL_RULE,
        ("video", "poster"): _URL_RULE,
    },
)


def strip_all_tags(html: str) -> str:
    """Remove all HTML tags, returning only text content.

    This is equivalent to bleach.clean(html, tags=set(), strip=True).

    Args:
        html: The HTML string to strip.

    Returns:
        The text content with all HTML tags removed.
    """
    policy = SanitizationPolicy(
        allowed_tags=frozenset(),
        allowed_attributes={},
        disallowed_tag_handling="unwrap",
        drop_content_tags=_DROP_CONTENT_TAGS,
    )
    html = _HTML_COMMENT_RE.sub("", html)
    doc = JustHTML(html, policy=policy, fragment=True)
    return doc.to_html(pretty=False)


def sanitize_html(html: str, allowed_tags: set, allowed_attributes: dict) -> str:
    """Sanitize HTML using an allowlist of tags and attributes.

    Disallowed tags are escaped (converted to &lt;tag&gt;). HTML comments are
    dropped: keeping them would reveal authoring notes and, with the
    current escape policy, surface them as visible &lt;!-- ... --&gt; text.

    Args:
        html: The HTML string to sanitize.
        allowed_tags: Set of allowed tag names.
        allowed_attributes: Dict mapping tag names to lists of allowed attributes.
            Use "*" as a key for attributes allowed on all tags.

    Returns:
        The sanitized HTML string.
    """
    policy = SanitizationPolicy(
        allowed_tags=frozenset(allowed_tags),
        allowed_attributes=allowed_attributes,
        url_policy=_URL_POLICY,
        disallowed_tag_handling="escape",
        drop_content_tags=_DROP_CONTENT_TAGS,
    )
    html = _HTML_COMMENT_RE.sub("", html)
    doc = JustHTML(html, policy=policy, fragment=True)
    return doc.to_html(pretty=False)
