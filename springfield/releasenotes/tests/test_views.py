# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

import pytest

from springfield.releasenotes.views import latest_notes, latest_sysreq, releases_index, show_android_sys_req


@pytest.mark.parametrize(
    "version_string, expected",
    (
        (None, False),
        ("", False),
        ("test", False),
        ("0", False),
        ("45", False),
        ("45.0", False),
        ("45.1.1", False),
        ("45.0a1", False),
        ("45.0a2", False),
        ("46", True),
        ("46.0", True),
        ("46.1.1", True),
        ("46.0a1", True),
        ("46.0a2", True),
        ("47", True),
        ("100", True),
        ("100.0", True),
        ("100.1.1", True),
        ("100.0a1", True),
        ("100.0a2", True),
        ("102", True),
        ("102.0", True),
        ("102.1.1", True),
        ("102.0a1", True),
        ("102.0a2", True),
    ),
)
def test_show_android_sys_req(version_string, expected):
    assert show_android_sys_req(version_string) == expected


@patch("springfield.firefox.views.l10n_utils.render")
def test_releases_index(render_mock, rf):
    """Spot checks, incl confirmation that FF100 will not cause a hiccup"""

    # Dates are from https://wiki.mozilla.org/Release_Management/Calendar but
    # these are here just for testing/dummy purposes
    mock_major_releases_val = {
        "3.6": "2010-01-21",
        "33.0": "2014-10-14",
        "33.1": "2014-11-10",
        "96.0": "2022-01-11",
        "100.0": "2022-05-03",
        "101.0": "2022-05-31",
    }
    mock_minor_releases_val = {
        "3.6.2": "2010-03-22",
        "3.6.3": "2010-04-01",
        "3.6.4": "2010-06-22",
        "3.6.6": "2010-06-26",
        "3.6.7": "2010-07-20",
        "3.6.8": "2010-07-23",
        "3.6.9": "2010-09-07",
        "3.6.10": "2010-09-15",
        "3.6.11": "2010-10-19",
        "3.6.12": "2010-10-27",
        "3.6.13": "2010-12-09",
        "3.6.14": "2011-03-01",
        "3.6.15": "2011-03-04",
        "3.6.16": "2011-03-22",
        "33.0.1": "2014-10-24",
        "33.0.2": "2014-10-28",
        "33.0.3": "2014-11-06",
        "33.1.1": "2014-11-14",
        "96.5": "2022-01-11",  # 100% fake/test
        "100.1": "2022-05-03",  # 100% fake/test
        "100.2": "2022-05-03",  # 100% fake/test
        "101.2": "2022-05-31",  # 100% fake/test
    }

    request = rf.get("/")

    with patch("springfield.releasenotes.views.firefox_desktop") as mock_firefox_desktop:
        mock_firefox_desktop.firefox_history_major_releases = mock_major_releases_val
        mock_firefox_desktop.firefox_history_stability_releases = mock_minor_releases_val

        releases_index(request, "Firefox")

    expected_data = {
        "releases": [
            (
                101.0,
                {
                    "major": "101.0",
                    "minor": [
                        {"version_string": "101.2", "is_esr": True},
                    ],
                },
            ),
            (
                100.0,
                {
                    "major": "100.0",
                    "minor": [
                        {"version_string": "100.1", "is_esr": True},
                        {"version_string": "100.2", "is_esr": True},
                    ],
                },
            ),
            (
                96.0,
                {
                    "major": "96.0",
                    "minor": [
                        {"version_string": "96.5", "is_esr": True},
                    ],
                },
            ),
            (
                33.1,
                {
                    "major": "33.1",
                    "minor": [
                        {"version_string": "33.1.1", "is_esr": False},
                    ],
                },
            ),
            (
                33.0,
                {
                    "major": "33.0",
                    "minor": [
                        {"version_string": "33.0.1", "is_esr": False},
                        {"version_string": "33.0.2", "is_esr": False},
                        {"version_string": "33.0.3", "is_esr": False},
                    ],
                },
            ),
            (
                3.6,
                {
                    "major": "3.6",
                    "minor": [
                        {"version_string": "3.6.2", "is_esr": False},
                        {"version_string": "3.6.3", "is_esr": False},
                        {"version_string": "3.6.4", "is_esr": False},
                        {"version_string": "3.6.6", "is_esr": False},
                        {"version_string": "3.6.7", "is_esr": False},
                        {"version_string": "3.6.8", "is_esr": False},
                        {"version_string": "3.6.9", "is_esr": False},
                        {"version_string": "3.6.10", "is_esr": False},
                        {"version_string": "3.6.11", "is_esr": False},
                        {"version_string": "3.6.12", "is_esr": False},
                        {"version_string": "3.6.13", "is_esr": False},
                        {"version_string": "3.6.14", "is_esr": False},
                        {"version_string": "3.6.15", "is_esr": False},
                        {"version_string": "3.6.16", "is_esr": False},
                    ],
                },
            ),
        ],
    }
    render_mock.assert_called_once_with(
        request,
        "firefox/releases/index.html",
        expected_data,
    )


@patch("springfield.firefox.views.l10n_utils.render")
def test_releases_index__esr_annotation(render_mock, rf):
    """ESR point releases (nonzero second segment) are flagged,
    but 50.1.0 is excluded as a known non-ESR exception."""

    mock_major_releases_val = {
        "50.0": "2016-11-15",
        "115.0": "2023-07-04",
    }
    mock_minor_releases_val = {
        "50.0.1": "2016-11-28",
        "50.0.2": "2016-12-01",
        "50.1.0": "2016-12-13",
        "115.0.1": "2023-07-06",
        "115.0.2": "2023-07-11",
        "115.1.0": "2023-08-01",
        "115.2.0": "2023-08-29",
    }

    request = rf.get("/")

    with patch("springfield.releasenotes.views.firefox_desktop") as mock_firefox_desktop:
        mock_firefox_desktop.firefox_history_major_releases = mock_major_releases_val
        mock_firefox_desktop.firefox_history_stability_releases = mock_minor_releases_val

        releases_index(request, "Firefox")

    expected_data = {
        "releases": [
            (
                115.0,
                {
                    "major": "115.0",
                    "minor": [
                        {"version_string": "115.0.1", "is_esr": False},
                        {"version_string": "115.0.2", "is_esr": False},
                        {"version_string": "115.1.0", "is_esr": True},
                        {"version_string": "115.2.0", "is_esr": True},
                    ],
                },
            ),
            (
                50.0,
                {
                    "major": "50.0",
                    "minor": [
                        {"version_string": "50.0.1", "is_esr": False},
                        {"version_string": "50.0.2", "is_esr": False},
                        {"version_string": "50.1.0", "is_esr": False},
                    ],
                },
            ),
        ],
    }
    render_mock.assert_called_once_with(
        request,
        "firefox/releases/index.html",
        expected_data,
    )


@patch("springfield.firefox.views.l10n_utils.render")
def test_releases_index__product_other_than_firefox(render_mock, rf):
    request = rf.get("/")
    releases_index(request, "someproduct")
    render_mock.assert_called_once_with(
        request,
        "someproduct/releases/index.html",
        {"releases": []},
    )


@pytest.mark.parametrize(
    "view_func, url_method",
    [
        (latest_notes, "get_absolute_url"),
        (latest_sysreq, "get_sysreq_url"),
    ],
)
@patch("springfield.releasenotes.views.latest_release")
def test_latest_redirects_preserve_query_params(latest_release_mock, view_func, url_method, rf):
    mock_release = latest_release_mock.return_value
    mock_release.get_sysreq_url.return_value = "/firefox/ios/152.0/system-requirements/"
    mock_release.get_absolute_url.return_value = "/en-US/firefox/ios/152.0/releasenotes/"

    request = rf.get("/?redirect_source=mozilla-org")
    response = view_func(request)

    assert response.status_code == 302
    expected_url = getattr(mock_release, url_method)()
    assert response.url == f"{expected_url}?redirect_source=mozilla-org"


@pytest.mark.parametrize(
    "view_func, url_method",
    [
        (latest_notes, "get_absolute_url"),
        (latest_sysreq, "get_sysreq_url"),
    ],
)
@patch("springfield.releasenotes.views.latest_release")
def test_latest_redirects_without_query_params(latest_release_mock, view_func, url_method, rf):
    mock_release = latest_release_mock.return_value
    mock_release.get_sysreq_url.return_value = "/firefox/ios/152.0/system-requirements/"
    mock_release.get_absolute_url.return_value = "/en-US/firefox/ios/152.0/releasenotes/"

    request = rf.get("/")
    response = view_func(request)

    assert response.status_code == 302
    assert response.url == getattr(mock_release, url_method)()
