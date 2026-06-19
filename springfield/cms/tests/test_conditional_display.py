# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.conditional_display_fixtures import (
    get_conditional_display_test_page,
    get_conditional_display_variants,
)


@pytest.mark.django_db
def test_conditional_display_blocks(index_page, rf):
    variants = get_conditional_display_variants()
    page = get_conditional_display_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    upper = soup.find("div", class_="fl-split-page-upper")
    assert upper

    notification_divs = upper.find_all("div", class_="fl-notification")
    assert len(notification_divs) == len(variants)

    for index, variant in enumerate(variants):
        notification = notification_divs[index]
        show_to = variant["value"]["settings"]["show_to"]

        platforms = show_to.get("platforms") or []
        firefox = show_to.get("firefox") or ""
        auth_state = show_to.get("auth_state") or ""
        default_browser = show_to.get("default_browser") or ""
        geo = show_to.get("geo") or []
        min_version = show_to.get("min_version")
        max_version = show_to.get("max_version")
        ai_controls = show_to.get("ai_controls")

        wrappers = [el for el in notification.parents if "conditional-display" in (el.get("class") or [])]

        has_any_condition = any([platforms, firefox, auth_state, default_browser, geo, min_version, max_version, ai_controls])

        if not has_any_condition:
            assert wrappers == [], f"Block {index}: expected no conditional-display wrappers, got {len(wrappers)}"
            continue

        wrapper_classes = {cls for wrapper in wrappers for cls in wrapper.get("class", [])}

        # Platform — each selected platform becomes a class on one wrapper div
        if platforms:
            platform_wrapper = next(
                (w for w in wrappers if any(f"condition-{p}" in (w.get("class") or []) for p in platforms)),
                None,
            )
            assert platform_wrapper is not None, f"Block {index}: no platform wrapper found for {platforms}"
            for platform in platforms:
                assert f"condition-{platform}" in platform_wrapper["class"], f"Block {index}: missing class 'condition-{platform}'"

        # Firefox
        if firefox:
            assert f"condition-{firefox}" in wrapper_classes, f"Block {index}: missing class 'condition-{firefox}'"

        # Auth state
        if auth_state:
            assert f"condition-{auth_state}" in wrapper_classes, f"Block {index}: missing class 'condition-{auth_state}'"

        # Default browser
        if default_browser:
            assert f"condition-{default_browser}" in wrapper_classes, f"Block {index}: missing class 'condition-{default_browser}'"

        # Geo — wrapper has condition-geo class and data-geo-conditions attribute
        if geo:
            geo_wrapper = next((w for w in wrappers if "condition-geo" in (w.get("class") or [])), None)
            assert geo_wrapper is not None, f"Block {index}: no geo wrapper found"
            geo_attr = geo_wrapper.get("data-geo-conditions", "")
            for country in geo:
                assert country in geo_attr, f"Block {index}: country '{country}' not in data-geo-conditions='{geo_attr}'"

        # AI controls — each value becomes condition-ai-controls-<value>
        if ai_controls:
            assert f"condition-ai-controls-{ai_controls}" in wrapper_classes, f"Block {index}: missing class 'condition-ai-controls-{ai_controls}'"

        # Version — wrapper has condition-fx-version class with data attributes
        if min_version or max_version:
            version_wrapper = next(
                (w for w in wrappers if "condition-fx-version" in (w.get("class") or [])),
                None,
            )
            assert version_wrapper is not None, f"Block {index}: no version wrapper found"
            if min_version:
                assert version_wrapper.get("data-min-version") == str(min_version), f"Block {index}: expected data-min-version='{min_version}'"
            if max_version:
                assert version_wrapper.get("data-max-version") == str(max_version), f"Block {index}: expected data-max-version='{max_version}'"
