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
    """Spot checks, incl confirmation that FF100 will not cause a hiccup, and
    that ESR status comes from the ESR/Release-channel ProductRelease
    queries rather than being guessed from the version string shape."""

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
        "33.0.1": "2014-10-24",
        "33.1.1": "2014-11-14",
        "96.5": "2022-01-11",  # 100% fake/test
        "100.1": "2022-05-03",  # 100% fake/test
        "100.2": "2022-05-03",  # 100% fake/test
        "101.2": "2022-05-31",  # 100% fake/test
    }

    request = rf.get("/")

    with (
        patch("springfield.releasenotes.views.firefox_desktop") as mock_firefox_desktop,
        patch("springfield.releasenotes.views.get_esr_release_versions", return_value=set()),
        patch("springfield.releasenotes.views.get_release_channel_versions", return_value=set()),
    ):
        mock_firefox_desktop.firefox_history_major_releases = mock_major_releases_val
        mock_firefox_desktop.firefox_history_stability_releases = mock_minor_releases_val

        releases_index(request, "Firefox")

    # None of these version strings are in the (empty) mocked ESR set, so
    # every minor entry should render as a single, non-ESR pill.
    expected_data = {
        "releases": [
            (101.0, {"major": "101.0", "minor": [{"version_string": "101.2", "is_esr": False}]}),
            (
                100.0,
                {
                    "major": "100.0",
                    "minor": [
                        {"version_string": "100.1", "is_esr": False},
                        {"version_string": "100.2", "is_esr": False},
                    ],
                },
            ),
            (96.0, {"major": "96.0", "minor": [{"version_string": "96.5", "is_esr": False}]}),
            (33.1, {"major": "33.1", "minor": [{"version_string": "33.1.1", "is_esr": False}]}),
            (33.0, {"major": "33.0", "minor": [{"version_string": "33.0.1", "is_esr": False}]}),
            (
                3.6,
                {
                    "major": "3.6",
                    "minor": [
                        {"version_string": "3.6.2", "is_esr": False},
                        {"version_string": "3.6.3", "is_esr": False},
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
    """ESR annotation is driven by the ESR/Release-channel ProductRelease
    queries, not by the shape of the version string:

    - "115.0.1"/"115.0.2" are Release-channel-only -> not flagged.
    - "115.1.0"/"115.2.0" are genuine ESR-only point releases (present in
      firefox_history_stability_releases, which mixes Release and ESR point
      releases with no marker, but absent from the Release-channel set) ->
      flagged, and shown as a single pill each, not doubled.
    - "140.5.0" simulates a genuine channel collision: the same version
      string, separately public on both Release and ESR -> both a plain and
      an "ESR" pill are shown, neither channel silently wins.
    - "102.0.1" mirrors the one real historical collision found in
      data/release_notes/releases/: present in the Release-channel set, but
      its ESR sibling was never public, so it never makes it into the ESR
      set -> resolves to a single, non-ESR pill.
    - "140.0esr" has no entry at all in firefox_history_major_releases/
      firefox_history_stability_releases (ESR baselines aren't tracked
      there) and must be injected as an extra minor pill under its matching
      major (140.0), sorted before its point releases.
    """
    mock_major_releases_val = {
        "102.0": "2022-06-28",
        "115.0": "2023-07-04",
        "140.0": "2025-06-30",
    }
    mock_minor_releases_val = {
        "102.0.1": "2022-07-06",
        "115.0.1": "2023-07-06",
        "115.0.2": "2023-07-11",
        "115.1.0": "2023-08-01",
        "115.2.0": "2023-08-29",
        "140.5.0": "2025-11-01",
    }
    mock_esr_versions = {"115.1.0", "115.2.0", "140.0esr", "140.5.0"}
    mock_release_versions = {"102.0.1", "140.5.0"}

    request = rf.get("/")

    with (
        patch("springfield.releasenotes.views.firefox_desktop") as mock_firefox_desktop,
        patch("springfield.releasenotes.views.get_esr_release_versions", return_value=mock_esr_versions),
        patch("springfield.releasenotes.views.get_release_channel_versions", return_value=mock_release_versions),
    ):
        mock_firefox_desktop.firefox_history_major_releases = mock_major_releases_val
        mock_firefox_desktop.firefox_history_stability_releases = mock_minor_releases_val

        releases_index(request, "Firefox")

    expected_data = {
        "releases": [
            (
                140.0,
                {
                    "major": "140.0",
                    "minor": [
                        {"version_string": "140.0esr", "is_esr": True},
                        {"version_string": "140.5.0", "is_esr": False},
                        {"version_string": "140.5.0", "is_esr": True},
                    ],
                },
            ),
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
                102.0,
                {
                    "major": "102.0",
                    "minor": [
                        {"version_string": "102.0.1", "is_esr": False},
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
