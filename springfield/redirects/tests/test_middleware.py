# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.http.response import HttpResponse
from django.test import RequestFactory

from springfield.base.tests import TestCase
from springfield.redirects.middleware import RedirectsMiddleware
from springfield.redirects.util import get_resolver, redirect

patterns = [
    redirect(r"^dude/already/10th/", "/far/out/"),
    redirect(r"^walter/prior/restraint/", "/finishes/coffee/"),
]
middleware = RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(patterns))


class TestRedirectsMiddleware(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_finds_and_uses_redirect(self):
        resp = middleware.process_request(self.rf.get("/walter/prior/restraint/"))
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp["location"], "/finishes/coffee/")

    def test_no_redirect_match(self):
        resp = middleware.process_request(self.rf.get("/donnie/out/element/"))
        self.assertIsNone(resp)
