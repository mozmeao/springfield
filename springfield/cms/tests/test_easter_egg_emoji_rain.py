# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup
from waffle.testutils import override_switch
from wagtail.models import Site

from springfield.cms.tests.factories import FreeFormPage2026Factory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def page():
    site = Site.objects.get(is_default_site=True)
    return FreeFormPage2026Factory(parent=site.root_page)


def loads_emoji_rain_bundle(client, url):
    response = client.get(url)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
    return any("easter-egg-emoji-rain" in script.get("src", "") for script in soup.find_all("script"))


@override_switch("EASTER_EGG_EMOJI_RAIN", active=True)
def test_sticker_url_loads_emoji_rain_bundle(client, page):
    assert loads_emoji_rain_bundle(client, f"{page.url}?utm_team=web+martech")


@override_switch("EASTER_EGG_EMOJI_RAIN", active=True)
@pytest.mark.parametrize("query", ["", "?utm_team=other", "?utm_source=web+martech"])
def test_other_urls_skip_emoji_rain_bundle(client, page, query):
    assert not loads_emoji_rain_bundle(client, f"{page.url}{query}")


@override_switch("EASTER_EGG_EMOJI_RAIN", active=False)
def test_sticker_url_skips_emoji_rain_bundle_when_switch_is_off(client, page):
    assert not loads_emoji_rain_bundle(client, f"{page.url}?utm_team=web+martech")
