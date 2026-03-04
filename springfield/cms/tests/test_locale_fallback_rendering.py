# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.test import override_settings

import pytest
from wagtail.models import Page, Site

from springfield.cms.tests.factories import LocaleFactory

pytestmark = [pytest.mark.django_db]


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_canonical_link_and_index_for_alias_page(client, tiny_localized_site):
    """
    Test canonical and index when serving content from an aliased Page.

    If the user requests the pt-PT page, but it does not exist, the user is served
    content from the pt-BR page at the pt-PT URL (since pt-BR is the fallback
    URL for pt-PT).
    The <link rel="canonical"> href should use the CANONICAL_LANG (pt-BR), not LANG (pt-PT).
    The page should not be indexed.

    When the middleware transparently serves pt-BR content at the pt-PT URL,
    the canonical link must point to the pt-BR URL so search engines know
    where the authoritative content lives.
    """
    # Make sure that the pt-PT locale exists and has an empty home page,
    # so that Wagtail correctly 404s for pt-PT paths instead of falling back
    # to the en-US tree.
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page
    pt_pt_root_page = en_us_root_page.copy_for_translation(pt_pt_locale)
    pt_pt_root_page.live = True
    pt_pt_root_page.save()

    en_us_homepage = en_us_root_page.get_children()[0]
    pt_pt_homepage = en_us_homepage.copy_for_translation(pt_pt_locale)
    pt_pt_homepage.title = "Página de Teste"
    pt_pt_homepage.live = True
    pt_pt_homepage.save()
    rev = pt_pt_homepage.save_revision()
    pt_pt_homepage.publish(rev)

    # Determine the URL for the non-existent page in the pt-PT locale.
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")
    pt_pt_url = pt_br_child.url.replace("pt-BR", "pt-PT")

    response = client.get(pt_pt_url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    page_path = "/test-page/child-page/"
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-PT{page_path}"' not in html
    # Since the page content (pt-BR) is different from the URL (pt-PT), the URL
    # should not be indexed.
    assert '<meta name="robots" content="noindex,follow">' in html
    # Note: while response.context["LANG"] and response.context["CANONICAL_LANG"]
    # are correctly used to render the templates, we do not assert them here,
    # because they are incorrectly cached in the tests from the 1st request (the
    # request for a pt-PT page, which returns a 404 response).


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_canonical_link_and_index_for_non_alias_page(client, tiny_localized_site):
    """
    Test canonical and index when serving content from a regular non-alias Page.

    The <link rel="canonical"> href should use the lang from the request.
    The page should be indexed.
    """
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")

    response = client.get(pt_br_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    page_path = "/test-page/child-page/"
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    # Since the page content (pt-BR) is the same as the URL (pt-BR), the URL
    # should be indexed.
    assert '<meta name="robots" content="noindex,follow">' not in html
    # The response context has both the LANG and the CANONICAL_LANG.
    assert response.context["LANG"] == "pt-BR"
    assert response.context["CANONICAL_LANG"] == "pt-BR"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_pt_br_hreflang_block_emits_bare_hreflang_pt(client, tiny_localized_site):
    """The pt-BR hreflang block emits hreflang="pt" in addition to hreflang="pt-BR".

    pt-BR is the primary Portuguese locale; it should claim the bare hreflang="pt"
    tag, which search engines treat as the default Portuguese variant.
    """
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    response = client.get(en_us_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert f'hreflang="pt" href="{settings.CANONICAL_URL}/pt-BR/' in html
    # hreflang="pt" must appear exactly once (from pt-BR block only)
    count = html.count('hreflang="pt"')
    assert count == 1, f'Expected exactly one hreflang="pt" link, found {count}'
    # That one occurrence must point to pt-BR, not pt-PT
    idx = html.index('hreflang="pt"')
    surrounding = html[idx : idx + 120]
    assert f"{settings.CANONICAL_URL}/pt-BR/" in surrounding
    assert f"{settings.CANONICAL_URL}/pt-PT/" not in surrounding


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_pt_pt_hreflang_block_does_not_emit_bare_hreflang_pt(client, tiny_localized_site):
    """The pt-PT hreflang block only emits hreflang="pt-PT", not hreflang="pt".

    pt-PT is an alias locale; the bare hreflang="pt" belongs to pt-BR exclusively.
    Emitting hreflang="pt" for pt-PT would conflict with the pt-BR entry.
    """
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    response = client.get(en_us_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert f'hreflang="pt" href="{settings.CANONICAL_URL}/pt-PT/' not in html
