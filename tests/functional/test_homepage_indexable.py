# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
import requests


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.parametrize("locale", ["en-US", "de", "fr"])
def test_homepage_is_indexable(locale, base_url):
    """The deployed homepage must never tell search engines not to index it. Locales here
    have their own homepage; alias locales are noindexed by design when they fall back."""
    resp = requests.get(f"{base_url}/{locale}/", timeout=5)
    assert resp.status_code == 200
    assert '<meta name="robots"' not in resp.text
    assert "noindex" not in resp.headers.get("X-Robots-Tag", "")
