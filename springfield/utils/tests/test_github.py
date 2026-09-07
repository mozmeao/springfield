# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.test import override_settings

from springfield.utils import github


def setup_function():
    github.GITHUB_CLIENT = None


def teardown_function():
    github.GITHUB_CLIENT = None


@override_settings(FLUENT_REPO_AUTH="")
def test_get_client_no_auth_configured():
    assert github.get_client() is None


@override_settings(FLUENT_REPO_AUTH="sometoken")
def test_get_client_bare_token(mocker):
    github_mock = mocker.patch.object(github, "Github")
    github.get_client()
    github_mock.assert_called_with("sometoken")


@override_settings(FLUENT_REPO_AUTH="dude:abides")
def test_get_client_legacy_username_and_token(mocker):
    github_mock = mocker.patch.object(github, "Github")
    github.get_client()
    github_mock.assert_called_with("abides")
