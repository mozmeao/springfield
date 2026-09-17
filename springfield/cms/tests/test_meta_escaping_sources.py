# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests that meta text is HTML-escaped exactly once, whatever its source.

A value reaches `<title>`, `og:title`, `description` or `og:description` as one
of three things, and Jinja autoescapes each differently:

- a plain `str` (a CMS field), escaped when the block output is captured
- `Markup`, which `ftl()` returns, not escaped on capture
- literal template text in an overridden block, also not escaped

Escaping twice leaves a visible `&#39;` in link previews. Leaving a straight
double quote unescaped ends the `content` attribute early and parses the rest
of the text as junk attributes. Both bases must avoid each.
"""

from django.urls import path

import pytest
from bs4 import BeautifulSoup
from markupsafe import Markup

from lib import l10n_utils
from springfield.base.i18n import springfield_i18n_patterns
from springfield.cms.fixtures.homepage_fixtures import get_home_test_page
from springfield.urls import urlpatterns as springfield_urlpatterns

TITLE = 'A "quoted" title & co'
DESC = 'A "quoted" desc & co'

# What sanitize_html() returns for the strings above: it escapes `&` and `<`
# but leaves a straight double quote alone. Encoding the quote here instead
# would stop these cases from reproducing the bug at all.
TITLE_MARKUP = Markup('A "quoted" title &amp; co')
DESC_MARKUP = Markup('A "quoted" desc &amp; co')

SOURCES = {
    "literal": {},
    "plain_str": {"title_source": TITLE, "desc_source": DESC},
    "markup": {"title_source": TITLE_MARKUP, "desc_source": DESC_MARKUP},
}

BASES = {"flare": "cms/base-flare.html", "protocol": "base-protocol.html"}


def _meta_test_view(request):
    context = {"base_template": BASES[request.GET["base"]]}
    context.update(SOURCES[request.GET["source"]])
    return l10n_utils.render(request, f"test-meta-escaping{request.GET['variant']}.html", context)


urlpatterns = springfield_i18n_patterns(path("test-meta-escaping/", _meta_test_view)) + springfield_urlpatterns


def _assert_escaped_once(soup, tags):
    """Each tag's content must survive one unescape unchanged, with no extra attributes.

    A stray attribute means a quote ended the attribute early and the rest of
    the string was parsed as markup.
    """
    for (attr, value), expected in tags.items():
        tag = soup.find("meta", {attr: value})
        assert tag is not None, f"no <meta {attr}={value}>"
        assert tag["content"] == expected
        assert set(tag.attrs) == {attr, "content"}, f"attribute broke out: {tag.attrs}"


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("_add_test_templates_dir")
@pytest.mark.parametrize("base", list(BASES))
@pytest.mark.parametrize("source", list(SOURCES))
def test_overridden_blocks_escape_once(client, base, source):
    response = client.get(f"/en-US/test-meta-escaping/?base={base}&source={source}&variant=")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.title.string == f"{TITLE} — Firefox.com"
    _assert_escaped_once(
        soup,
        {
            ("property", "og:title"): TITLE,
            ("name", "description"): DESC,
            ("property", "og:description"): DESC,
        },
    )


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("_add_test_templates_dir")
@pytest.mark.parametrize("source", list(SOURCES))
def test_inherited_og_blocks_escape_once(client, source):
    """base-protocol's og:* defaults re-render page_title/page_desc via self.

    That captures the block output a second time, so it is the likeliest place
    for an extra escape to creep in. base-flare is excluded because its og:*
    defaults read the page object rather than calling back into these blocks.
    """
    response = client.get(f"/en-US/test-meta-escaping/?base=protocol&source={source}&variant=-inherited")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    _assert_escaped_once(
        soup,
        {
            ("property", "og:title"): TITLE,
            ("name", "description"): DESC,
            ("property", "og:description"): DESC,
        },
    )


# A non-breaking space before punctuation is normal French typography, and
# real pages carry them in titles. Collapsing them to an ASCII space lets the
# browser tab and search snippet line-break where the copy says it must not.
NBSP_TITLE = "Le bloqueur de publicités : PDF Editor"
NBSP_DESC = "Adoptez Firefox : c'est « rapide »"


@pytest.mark.django_db
def test_cms_page_meta_preserves_non_breaking_spaces(index_page, rf):
    page = get_home_test_page()
    page.title = NBSP_TITLE
    page.seo_title = NBSP_TITLE
    page.search_description = NBSP_DESC
    page.save_revision().publish()

    soup = BeautifulSoup(page.serve(rf.get(page.get_full_url())).content, "html.parser")

    assert soup.title.string == f"{NBSP_TITLE} — Firefox.com"
    _assert_escaped_once(
        soup,
        {
            ("property", "og:title"): NBSP_TITLE,
            ("name", "description"): NBSP_DESC,
            ("property", "og:description"): NBSP_DESC,
        },
    )
