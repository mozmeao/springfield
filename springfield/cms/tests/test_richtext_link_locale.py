# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for rich text internal link localization.
"""

from django.test import override_settings
from django.utils import translation

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, Site

from springfield.cms.templatetags.cms_tags import richtext
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_richtext_internal_page_link_localizes_per_visitor_locale(tiny_localized_site):
    """
    Test that a rich text internal link outputs as a locale-aware URL.

    Currently, rich text links are not explicitly locale aware, but they work
    as a result of Wagtail internals; this test verifies that they continue to
    work, even if some Wagtail internals change.

    Scenario:
      - A page is authored in en-US (the usual case) and translated to de and
        pt-BR. It has NO pt-PT or Italian translation.
      - Another page's rich text contains a link to the en-US page.

    Expected:
      - an en-US visitor sees the en-US page itself (`/en-US/linked-page/`);
      - a de visitor sees the de translation (`/de/linked-page/`);
      - a pt-BR visitor sees the pt-BR translation (`/pt-BR/linked-page/`);
      - a pt-PT visitor — because
         a) the pt-PT locale exists,
         b) there is NO pt-PT translation of the page, and
         c) pt-PT is an alias for the pt-BR fallback locale,
        the user sees a link on the pt-PT URL (`/pt-PT/linked-page/`). Even
        though the pt-PT does not exist, this is the expected link, to keep the
        user on the pt-PT URL. If the user clicks on the link, then the pt-BR
        page will be served at the pt-PT URL.
      - an Italian visitor — because
         a) the it locale exists,
         b) there is no it translation of the page, and
         c) it is not an alias locale —
        the user sees a link to the source source en-US page (`/en-US/linked-page/`).

    Note: we render the page content through Springfield's `richtext` template
    filter — the exact code path `{{ page.content|richtext }}` runs at request
    time — under the visitor's active locale. This produces the `<a>` the
    visitor sees. A literal `client.get()` round-trip was tried and is
    unreliable here because:
      1. Constructing/saving a rich-text page link in a test can bake it into a
         static `href` (a wagtail-localize translation-segment artifact), so the
         stored link no longer localizes.
      2. The shared `tiny_localized_site` fixture mis-routes some locale paths
         (it even warns about `find_for_request` page-tree quirks).
    """
    en_us_locale = Locale.objects.get(language_code="en-US")
    pt_br_locale = Locale.objects.get(language_code="pt-BR")
    de_locale = LocaleFactory(language_code="de")
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    it_locale = LocaleFactory(language_code="it")

    site = Site.objects.get(is_default_site=True)
    en_root = site.root_page
    # The de translation needs a translated parent to live under.
    en_root.copy_for_translation(de_locale).save_revision().publish()

    # The link target: an en-US page with de and pt-BR translations only.
    en_page = SimpleRichTextPageFactory(title="Linked", slug="linked-page", parent=en_root, locale=en_us_locale)
    en_page.save_revision().publish()
    en_page.copy_for_translation(de_locale).save_revision().publish()
    en_page.copy_for_translation(pt_br_locale).save_revision().publish()

    # The en_page has no translation in pt-PT or it locales.
    assert en_page.get_translation_or_none(pt_pt_locale) is None
    assert en_page.get_translation_or_none(it_locale) is None

    # Rich text (as authored on a page) linking to the en-US page.
    content = f'<p>See <a linktype="page" id="{en_page.id}">the page</a>.</p>'

    # An en-US visitor: the link is the en-US page itself.
    with translation.override("en-US"):
        html = richtext(context={}, value=content)
    assert BeautifulSoup(html, "html.parser").find("a")["href"] == "/en-US/linked-page/"

    # A de visitor: link resolves to the de translation.
    with translation.override("de"):
        html = richtext(context={}, value=content)
    assert BeautifulSoup(html, "html.parser").find("a")["href"] == "/de/linked-page/"

    # A pt-BR visitor: link resolves to the pt-BR translation.
    with translation.override("pt-br"):
        html = richtext(context={}, value=content)
    assert BeautifulSoup(html, "html.parser").find("a")["href"] == "/pt-BR/linked-page/"

    # A pt-PT visitor: link stays on the pt-PT locale.
    with translation.override("pt-pt"):
        html = richtext(context={}, value=content)
    assert BeautifulSoup(html, "html.parser").find("a")["href"] == "/pt-PT/linked-page/"

    # An `it` visitor (known locale, no translation, not an alias locale): falls back to
    # the source en-US page rather than inventing an /it/ URL.
    with translation.override("it"):
        html = richtext(context={}, value=content)
    assert BeautifulSoup(html, "html.parser").find("a")["href"] == "/en-US/linked-page/"
