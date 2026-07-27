# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from textwrap import dedent

from wagtail.models import Locale

from springfield.base.tests import TestCase
from springfield.sitemaps.models import NO_LOCALE, SitemapURL


class TestSitemapView(TestCase):
    def setUp(self):
        data = [
            {"path": "/firefox/notes/", "locale": "de"},
            {"path": "/firefox/", "locale": "de"},
            {
                "path": "/more/",
                "locale": "fr",
            },
            {"path": "/firefox/", "locale": "fr"},
            {"path": "/info.txt", "locale": NO_LOCALE},
            {
                "path": "/locales/",
                "locale": NO_LOCALE,
            },
        ]
        SitemapURL.objects.bulk_create(SitemapURL(**kw) for kw in data)

    def test_index(self):
        good_resp = dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
              <sitemap>
                <loc>https://www.firefox.com/sitemap-global.xml</loc>
              </sitemap>
              <sitemap>
                <loc>https://www.firefox.com/de/sitemap.xml</loc>
              </sitemap>
              <sitemap>
                <loc>https://www.firefox.com/fr/sitemap.xml</loc>
              </sitemap>
            </sitemapindex>"""
        )
        # Both alias and canonical paths return the index when unprefixed.
        resp = self.client.get("/all-urls.xml")
        assert resp.text == good_resp
        resp = self.client.get("/sitemap.xml")
        assert resp.text == good_resp

    def test_none(self):
        good_resp = dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
              <url>
                <loc>https://www.firefox.com/info.txt</loc>
              </url>
              <url>
                <loc>https://www.firefox.com/locales/</loc>
              </url>
            </urlset>"""
        )
        # NO_LOCALE entries never emit hreflang annotations.
        resp = self.client.get("/all-urls-global.xml")
        assert resp.text == good_resp
        resp = self.client.get("/sitemap-global.xml")
        assert resp.text == good_resp

    def test_locales(self):
        # No Wagtail Locale records configured here, so de/fr are treated as
        # legacy locales and emit no <xhtml:link> hreflang annotations.
        good_resp_de = dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
              <url>
                <loc>https://www.firefox.com/de/firefox/</loc>
              </url>
              <url>
                <loc>https://www.firefox.com/de/firefox/notes/</loc>
              </url>
            </urlset>"""
        )
        resp = self.client.get("/de/all-urls.xml")
        assert resp.text == good_resp_de
        resp = self.client.get("/de/sitemap.xml")
        assert resp.text == good_resp_de

        good_resp_fr = dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
              <url>
                <loc>https://www.firefox.com/fr/firefox/</loc>
              </url>
              <url>
                <loc>https://www.firefox.com/fr/more/</loc>
              </url>
            </urlset>"""
        )
        resp = self.client.get("/fr/all-urls.xml")
        assert resp.text == good_resp_fr
        resp = self.client.get("/fr/sitemap.xml")
        assert resp.text == good_resp_fr

    def test_post(self):
        resp = self.client.post("/en-US/all-urls.xml")
        assert resp.status_code == 405
        resp = self.client.post("/en-US/sitemap.xml")
        assert resp.status_code == 405


class TestSitemapHreflang(TestCase):
    """Tests for hreflang alternate emission, filtered by Wagtail's supported
    locale set (Locale.objects).
    """

    def setUp(self):
        # Configure Wagtail Locales — this is the "supported" set. de, fr, en-US,
        # pt-BR, and pt-PT are supported. ach is intentionally NOT in Wagtail
        # Locales — it's treated as a legacy locale.
        for code in ["en-US", "de", "fr", "pt-BR", "pt-PT"]:
            Locale.objects.get_or_create(language_code=code)

        data = [
            # Multi-locale path with both supported and legacy locales.
            {"path": "/features/", "locale": "en-US"},
            {"path": "/features/", "locale": "fr"},
            {"path": "/features/", "locale": "de"},
            {"path": "/features/", "locale": "ach"},  # legacy
            # Path that exists in pt-BR + pt-PT + en-US (tests bare-language
            # and pt-PT-as-promoted-alias conventions).
            {"path": "/about/", "locale": "en-US"},
            {"path": "/about/", "locale": "pt-BR"},
            {"path": "/about/", "locale": "pt-PT"},
            # Single-locale path: only one locale → no alternates emitted.
            {"path": "/only-en/", "locale": "en-US"},
            # Legacy-only path: only ach has it → since ach not in supported,
            # ach sitemap will list it but with no alternates.
            {"path": "/legacy-only/", "locale": "ach"},
        ]
        SitemapURL.objects.bulk_create(SitemapURL(**kw) for kw in data)

    def test_supported_locale_emits_alternates(self):
        """A page in a supported locale that exists in multiple supported
        locales declares all of them as hreflang alternates."""
        resp = self.client.get("/en-US/sitemap.xml")
        body = resp.text
        # /features/ has en-US, fr, de in supported (plus ach which is legacy
        # and should be filtered out).
        assert "<loc>https://www.firefox.com/en-US/features/</loc>" in body
        assert '<xhtml:link rel="alternate" hreflang="en-US" href="https://www.firefox.com/en-US/features/"/>' in body
        assert '<xhtml:link rel="alternate" hreflang="fr" href="https://www.firefox.com/fr/features/"/>' in body
        assert '<xhtml:link rel="alternate" hreflang="de" href="https://www.firefox.com/de/features/"/>' in body
        # Legacy locale (ach) must NOT appear as an alternate.
        assert 'hreflang="ach"' not in body
        assert "/ach/features/" not in body

    def test_en_us_emits_bare_language_alternate(self):
        """en-US emits both hreflang="en" and hreflang="en-US"."""
        resp = self.client.get("/en-US/sitemap.xml")
        body = resp.text
        assert '<xhtml:link rel="alternate" hreflang="en-US" href="https://www.firefox.com/en-US/features/"/>' in body
        assert '<xhtml:link rel="alternate" hreflang="en" href="https://www.firefox.com/en-US/features/"/>' in body

    def test_pt_br_emits_bare_language_alternate(self):
        """pt-BR emits both hreflang="pt" and hreflang="pt-BR" (primary
        Portuguese), mirroring canonical-url.html convention."""
        resp = self.client.get("/pt-BR/sitemap.xml")
        body = resp.text
        assert '<xhtml:link rel="alternate" hreflang="pt-BR" href="https://www.firefox.com/pt-BR/about/"/>' in body
        assert '<xhtml:link rel="alternate" hreflang="pt" href="https://www.firefox.com/pt-BR/about/"/>' in body

    def test_pt_pt_does_not_emit_bare_pt(self):
        """pt-PT emits only hreflang="pt-PT"; the bare hreflang="pt" belongs
        to pt-BR exclusively (alias convention)."""
        resp = self.client.get("/pt-PT/sitemap.xml")
        body = resp.text
        # The pt-PT URL itself is declared.
        assert '<xhtml:link rel="alternate" hreflang="pt-PT" href="https://www.firefox.com/pt-PT/about/"/>' in body
        # But the bare "pt" should only ever point to pt-BR, not pt-PT.
        assert 'hreflang="pt" href="https://www.firefox.com/pt-PT/' not in body

    def test_single_locale_url_emits_no_xhtml_link(self):
        """A URL that exists in only one locale should not emit any
        <xhtml:link> alternates (W3C: hreflang requires >=2 alternates to be
        meaningful)."""
        resp = self.client.get("/en-US/sitemap.xml")
        body = resp.text
        # /only-en/ has only en-US — no hreflang block expected for it.
        # We check that the URL block contains <loc> but no <xhtml:link>.
        assert "<loc>https://www.firefox.com/en-US/only-en/</loc>" in body
        # The xhtml:link line right after this loc shouldn't exist for /only-en/.
        # We assert there is no xhtml:link href to /only-en/ anywhere.
        assert '/only-en/"/>' not in body

    def test_legacy_locale_emits_no_hreflang(self):
        """A page in a legacy locale (not in Wagtail Locale.objects) is still
        listed in its per-locale sitemap, but emits no <xhtml:link> alternates
        — treats legacy URLs as standalone, not alternates of supported pages."""
        resp = self.client.get("/ach/sitemap.xml")
        body = resp.text
        # The URLs are still there (crawl coverage preserved).
        assert "<loc>https://www.firefox.com/ach/features/</loc>" in body
        assert "<loc>https://www.firefox.com/ach/legacy-only/</loc>" in body
        # But no hreflang annotations at all.
        assert "<xhtml:link" not in body

    def test_supported_pages_do_not_declare_legacy_as_alternate(self):
        """Supported-locale pages must not declare legacy locales as
        alternates, even when the legacy locale has the same URL path."""
        # /features/ exists in en-US (supported) and ach (legacy). The en-US
        # sitemap must not declare ach as an alternate.
        resp = self.client.get("/en-US/sitemap.xml")
        body = resp.text
        assert "/ach/" not in body
        assert 'hreflang="ach"' not in body
