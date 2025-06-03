# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from unittest.mock import patch
from urllib.parse import parse_qs

from django.http import HttpResponse
from django.test import override_settings
from django.test.client import RequestFactory

import querystringsafe_base64
from pyquery import PyQuery as pq

from springfield.base.tests import TestCase
from springfield.firefox import views


@override_settings(
    STUB_ATTRIBUTION_HMAC_KEY="achievers",
    STUB_ATTRIBUTION_RATE=1,
    STUB_ATTRIBUTION_MAX_LEN=600,
)
class TestStubAttributionCode(TestCase):
    def _get_request(self, params):
        rf = RequestFactory()
        return rf.get(
            "/",
            params,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

    def test_not_ajax_request(self):
        req = RequestFactory().get("/", {"source": "malibu"})
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 400)
        assert "cache-control" not in resp
        data = json.loads(resp.content)
        self.assertEqual(data["error"], "Resource only available via XHR")

    def test_no_valid_param_names(self):
        final_params = {
            "source": "www.firefox.com",
            "medium": "(none)",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "(not set)",
            "client_id_ga4": "(not set)",
            "session_id": "(not set)",
            "dlsource": "fxdotcom",
        }
        req = self._get_request({"dude": "abides"})
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "7b85e2288e54169c8b3ffecc48ae53ffadcb899637c5d81320caaae16f25b04e",
        )

    def test_no_valid_param_data(self):
        params = {
            "utm_source": "br@ndt",
            "utm_medium": "ae<t>her",
            "experiment": "dfb</p>s",
            "variation": "ef&bvcv",
            "client_id_ga4": "14</p>4538.1610<t>957",
            "session_id": "2w</br>123bg<u>957",
            "dlsource": "fs<a>44fn</a>",
        }
        final_params = {
            "source": "www.firefox.com",
            "medium": "(none)",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "(not set)",
            "client_id_ga4": "(not set)",
            "session_id": "(not set)",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "7b85e2288e54169c8b3ffecc48ae53ffadcb899637c5d81320caaae16f25b04e",
        )

    def test_some_valid_param_data(self):
        params = {"utm_source": "brandt", "utm_content": "ae<t>her", "dlsource": "fxdotcom"}
        final_params = {
            "source": "brandt",
            "medium": "(direct)",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "(not set)",
            "client_id_ga4": "(not set)",
            "session_id": "(not set)",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "1045ac6652da1cf26a16298192fb7c24fa7633008dd74f7b6ee70de104552cc4",
        )

    def test_campaign_data_too_long(self):
        """If the code is too long then the utm_campaign value should be truncated"""
        params = {
            "utm_source": "brandt",
            "utm_medium": "aether",
            "utm_content": "A144_A000_0000000",
            "utm_campaign": "The%7cDude%7cabides%7cI%7cdont%7cknow%7cabout%7cyou%7cbut%7cI%7ctake%7ccomfort%7cin%7cthat" * 6,
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "chrome",
            "client_id_ga4": "2456954538.1610960957",
            "session_id": "1668161374",
            "dlsource": "fxdotcom",
        }
        final_params = {
            "source": "brandt",
            "medium": "aether",
            "campaign": "The|Dude|abides|I|dont|know|about|you|but|I|take|comfort|in"
            "|thatThe|Dude|abides|I|dont|know|about|you|but|I|take|comfort|in|thatThe"
            "|Dude|abides|I|dont|know|about|you|but|I|take|comfort|in|thatThe|Dude|abides"
            "|I|dont|know|about|you|but|I|take|comfort|in|thatThe|Dude|abides|I|dont|know|about%7_",
            "content": "A144_A000_0000000",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "chrome",
            "client_id_ga4": "2456954538.1610960957",
            "session_id": "1668161374",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        code = querystringsafe_base64.decode(data["attribution_code"].encode()).decode()
        assert len(code) <= 600
        attrs = parse_qs(code)
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "02f2109b763e2eff09884419ce6e674761acb814d79d6e84cd2fb174f5841e71",
        )

    def test_other_data_too_long_not_campaign(self):
        """If the code is too long but not utm_campaign return error"""
        params = {
            "utm_source": "brandt",
            "utm_campaign": "dude",
            "utm_content": "A144_A000_0000000",
            "utm_medium": "The%7cDude%7cabides%7cI%7cdont%7cknow%7cabout%7cyou%7cbut%7cI%7ctake%7ccomfort%7cin%7cthat" * 6,
        }
        final_params = {"error": "Invalid code"}
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 400)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        self.assertDictEqual(data, final_params)

    def test_returns_valid_data(self):
        params = {
            "utm_source": "brandt",
            "utm_medium": "aether",
            "experiment": "firefox-download",
            "variation": "1",
            "ua": "chrome",
            "client_id_ga4": "2456954538.1610960957",
            "session_id": "1668161374",
            "dlsource": "fxdotcom",
        }
        final_params = {
            "source": "brandt",
            "medium": "aether",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "firefox-download",
            "variation": "1",
            "ua": "chrome",
            "client_id_ga4": "2456954538.1610960957",
            "session_id": "1668161374",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "f96186b4d814cfe99bf0c4d17a065535239cc0b4054534b46552bbc615598b90",
        )

    def test_handles_referrer(self):
        params = {"utm_source": "brandt", "referrer": "https://duckduckgo.com/privacy"}
        final_params = {
            "source": "brandt",
            "medium": "(direct)",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "(not set)",
            "client_id_ga4": "(not set)",
            "session_id": "(not set)",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "1045ac6652da1cf26a16298192fb7c24fa7633008dd74f7b6ee70de104552cc4",
        )

    def test_handles_referrer_no_source(self):
        params = {
            "referrer": "https://example.com:5000/searchin",
            "utm_medium": "aether",
        }
        final_params = {
            "source": "example.com:5000",
            "medium": "referral",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "(not set)",
            "client_id_ga4": "(not set)",
            "session_id": "(not set)",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "1791839786fe22e61e20e570ff0860082b16527cc9f982564461d0b33afed4b8",
        )

    def test_handles_referrer_utf8(self):
        """Should ignore non-ascii domain names.

        We were getting exceptions when the view was trying to base64 encode
        non-ascii domain names in the referrer. The allowed list for bouncer
        doesn't include any such domains anyway, so we should just ignore them.
        """
        params = {"referrer": "http://youtubê.com/sorry/"}
        final_params = {
            "source": "www.firefox.com",
            "medium": "(none)",
            "campaign": "(not set)",
            "content": "(not set)",
            "experiment": "(not set)",
            "variation": "(not set)",
            "ua": "(not set)",
            "client_id_ga4": "(not set)",
            "session_id": "(not set)",
            "dlsource": "fxdotcom",
        }
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"
        data = json.loads(resp.content)
        # will it blend?
        attrs = parse_qs(querystringsafe_base64.decode(data["attribution_code"].encode()).decode())
        # parse_qs returns a dict with lists for values
        attrs = {k: v[0] for k, v in attrs.items()}
        self.assertDictEqual(attrs, final_params)
        self.assertEqual(
            data["attribution_sig"],
            "7b85e2288e54169c8b3ffecc48ae53ffadcb899637c5d81320caaae16f25b04e",
        )

    @override_settings(STUB_ATTRIBUTION_RATE=0.2)
    def test_rate_limit(self):
        params = {"utm_source": "brandt", "utm_medium": "aether"}
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 200)
        assert resp["cache-control"] == "max-age=300"

    @override_settings(STUB_ATTRIBUTION_RATE=0)
    def test_rate_limit_disabled(self):
        params = {"utm_source": "brandt", "utm_medium": "aether"}
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 429)
        assert resp["cache-control"] == "max-age=300"

    @override_settings(STUB_ATTRIBUTION_HMAC_KEY="")
    def test_no_hmac_key_set(self):
        params = {"utm_source": "brandt", "utm_medium": "aether"}
        req = self._get_request(params)
        resp = views.stub_attribution_code(req)
        self.assertEqual(resp.status_code, 403)
        assert resp["cache-control"] == "max-age=300"


@override_settings(DEV=False)
@patch("springfield.firefox.views.l10n_utils.render", return_value=HttpResponse())
class TestFirefoxDownload(TestCase):
    def test_post(self, render_mock):
        req = RequestFactory().post("/")
        req.locale = "en-US"
        view = views.DownloadView.as_view()
        resp = view(req)
        assert resp.status_code == 405

    def test_download_template(self, render_mock):
        for locale, ftl_file_is_active_value, expected_template in (
            ("en-US", True, "firefox/download/desktop/download-en-us-ca.html"),
            ("en-CA", True, "firefox/download/desktop/download-en-us-ca.html"),
            ("en-GB", True, "firefox/download/desktop/download.html"),
            ("fr", True, "firefox/download/desktop/download.html"),
            ("en-CA", False, "firefox/download/basic/base_download.html"),  # Note the False for activation
        ):
            with self.subTest(
                locale=locale,
                ftl_file_is_active_value=ftl_file_is_active_value,
                expected_template=expected_template,
            ):
                with patch.object(views, "ftl_file_is_active", lambda *x: ftl_file_is_active_value):
                    req = RequestFactory().get("/")
                    req.locale = locale
                    view = views.DownloadView.as_view()
                    view(req)
                    template = render_mock.call_args[0][1]
                    assert template == [expected_template]

    @patch.object(views, "ftl_file_is_active", lambda *x: True)
    def test_thanks_template(self, render_mock):
        req = RequestFactory().get("/thanks/")
        req.locale = "en-US"
        view = views.DownloadThanksView.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/download/desktop/thanks.html"]

    @patch.object(views, "ftl_file_is_active", lambda *x: False)
    def test_download_basic_template(self, render_mock):
        req = RequestFactory().get("/")
        req.locale = "de"
        view = views.DownloadView.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/download/basic/base_download.html"]

    @patch.object(views, "ftl_file_is_active", lambda *x: False)
    def test_thanks_basic_template(self, render_mock):
        req = RequestFactory().get("/thanks/")
        req.locale = "de"
        view = views.DownloadThanksView.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/download/basic/thanks.html"]

    def test_thanks_redirect(self, render_mock):
        req = RequestFactory().get("/?scene=2&dude=abides")
        req.locale = "en-US"
        view = views.DownloadView.as_view()
        resp = view(req)
        assert resp.status_code == 301
        assert resp["location"].endswith("/thanks/?scene=2&dude=abides")

    # begin /thanks?s=direct URL - issue 10520

    @patch.object(views, "ftl_file_is_active", lambda *x: True)
    def test_thanks_desktop_direct(self, render_mock):
        req = RequestFactory().get("/thanks/?s=direct")
        req.locale = "en-US"
        view = views.DownloadThanksView.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/download/desktop/thanks_direct.html"]

    @patch.object(views, "ftl_file_is_active", lambda *x: False)
    def test_thanks_basic_direct(self, render_mock):
        req = RequestFactory().get("/thanks/?s=direct")
        req.locale = "el"
        view = views.DownloadThanksView.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/download/basic/thanks_direct.html"]

    # end /thanks?s=direct URL - issue 10520


class TestFirefoxDownloadNoIndex(TestCase):
    def test_download_noindex(self):
        # Scene 1 of / should never contain a noindex tag.
        response = self.client.get("/en-US/")
        doc = pq(response.content)
        robots = doc('meta[name="robots"]')
        assert robots.length == 0

    def test_thanks_canonical(self):
        # Scene 2 /thanks/ should always contain a noindex tag.
        response = self.client.get("/en-US/thanks/")
        doc = pq(response.content)
        robots = doc('meta[name="robots"]')
        assert robots.length == 1
        assert "noindex" in robots.attr("content")
        assert "follow" in robots.attr("content")


class TestFirefoxGA(TestCase):
    def assert_ga_attr(self, response):
        doc = pq(response.content)
        links = doc(".mzp-c-button")
        # test buttons all have appropriate attribute to trigger tracking in GA
        for link in links.items():
            cta_text = link.attr("data-cta-text")
            link_text = link.attr("data-link-text")
            if cta_text or link_text:
                assert True
            else:
                assert False, f"{link} does not contain attr data-cta-text or data-link-text"

    def test_firefox_home_GA(self):
        req = RequestFactory().get("/en-US/")
        view = views.FirefoxHomeView.as_view()
        response = view(req)
        self.assert_ga_attr(response)

    def test_firefox_download_all_GA(self):
        # the root page at / is a download page; let's also test /download/all/
        req = RequestFactory().get("/en-US/download/all/")
        view = views.DownloadView.as_view()
        response = view(req)
        self.assert_ga_attr(response)


# Issue 13253: Ensure that Firefox can continue to refer to this URL.
class TestFirefoxSetAsDefaultThanks(TestCase):
    def test_firefox_set_as_default_thanks(self):
        resp = self.client.get("/landing/set-as-default/thanks/", follow=True)
        assert resp.status_code == 200, "Ensure this URL continues to work, see issue 13253"
        assert resp.templates[0].name == "firefox/default/thanks.html"


@override_settings(DEV=False)
@patch("springfield.firefox.views.l10n_utils.render", return_value=HttpResponse())
class TestFirefoxPlatform(TestCase):
    @patch.object(views, "ftl_file_is_active", lambda *x: True)
    def test_linux_download_template(self, render_mock):
        req = RequestFactory().get("/browsers/desktop/linux/")
        req.locale = "en-US"
        view = views.PlatformViewLinux.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/browsers/desktop/linux.html"]

    @patch.object(views, "ftl_file_is_active", lambda *x: True)
    def test_mac_download_template(self, render_mock):
        req = RequestFactory().get("/browsers/desktop/mac/")
        req.locale = "en-US"
        view = views.PlatformViewMac.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/browsers/desktop/mac.html"]

    @patch.object(views, "ftl_file_is_active", lambda *x: True)
    def test_windows_download_template(self, render_mock):
        req = RequestFactory().get("/browsers/desktop/windows/")
        req.locale = "en-US"
        view = views.PlatformViewWindows.as_view()
        view(req)
        template = render_mock.call_args[0][1]
        assert template == ["firefox/browsers/desktop/windows.html"]
