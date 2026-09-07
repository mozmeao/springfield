# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import base64
from subprocess import CalledProcessError
from unittest.mock import DEFAULT, call, patch

from django.test import override_settings

import pytest

from springfield.utils import git


@patch.object(git, "os")
@patch.object(git, "check_output")
def test_git(co_mock, os_mock):
    os_mock.getcwd.return_value = "olddir"
    co_mock.return_value = "dude"
    git_repo = git.GitRepo("new_repo")
    output = git_repo.git("checkout", "maude")
    co_mock.assert_called_with((git.GIT, "checkout", "maude"), stderr=git.STDOUT)
    os_mock.chdir.assert_has_calls(
        [
            call(git_repo.path_str),
            call("olddir"),
        ]
    )
    assert output == "dude"


@patch.object(git, "os")
@patch.object(git, "check_output")
def test_git_merges_environment_overrides_over_os_environ(co_mock, os_mock):
    # Exercises git()'s own merge logic directly (check_output/os mocked,
    # not git() itself), unlike the clone/pull/push auth tests, which mock
    # out git() entirely and so never touch this line.
    os_mock.getcwd.return_value = "olddir"
    os_mock.environ = {"PATH": "/usr/bin", "GIT_TERMINAL_PROMPT": "1"}
    co_mock.return_value = "dude"
    git_repo = git.GitRepo("new_repo")

    git_repo.git("fetch", environment_overrides={"GIT_TERMINAL_PROMPT": "0"})

    co_mock.assert_called_with(
        (git.GIT, "fetch"),
        stderr=git.STDOUT,
        env={"PATH": "/usr/bin", "GIT_TERMINAL_PROMPT": "0"},
    )


def test_git_current_hash():
    git_repo = git.GitRepo(".")
    with patch.object(git_repo, "git") as git_mock:
        git_repo.current_hash

    git_mock.assert_called_with("rev-parse", "HEAD")


@pytest.mark.django_db
def test_git_db_latest():
    git_repo = git.GitRepo(".", "https://example.com/repo.git", "master")
    assert git_repo.db_latest_key == "33ff0192f06306345030004c92533017b466e16489d4c762eab69ad8142ddae4"
    assert git_repo.get_db_latest() is None
    git_repo.set_db_latest("deadbeef")
    assert git_repo.get_db_latest() == "deadbeef"
    git_repo.set_db_latest("deadbeef1234")
    assert git_repo.get_db_latest() == "deadbeef1234"


@pytest.mark.django_db
def test_git_db_latest_methods():
    git_repo = git.GitRepo(".", "https://example.com/repo.git", "master", "dude")
    git_repo.set_db_latest("deadbeef")
    assert git_repo.get_db_latest() == "deadbeef"
    gobj = git.GitRepoState.objects.get(repo_id=git_repo.db_latest_key)
    assert gobj.repo_name == "dude"
    assert gobj.commit_url == "https://example.com/repo/commit/deadbeef"


@pytest.mark.django_db
def test_git_db_latest_auto_name():
    # name should be the last bit of the path, and the repo URL can deal with a trailing slash
    git_repo = git.GitRepo("hollywood-star-lanes/the-dude", "https://example.com/repo/", "master")
    git_repo.set_db_latest("deadbeef")
    assert git_repo.get_db_latest() == "deadbeef"
    gobj = git.GitRepoState.objects.get(repo_id=git_repo.db_latest_key)
    assert gobj.repo_name == "the-dude"
    assert gobj.commit_url == "https://example.com/repo/commit/deadbeef"


@override_settings(DEV=True)
def test_git_clone():
    git_repo = git.GitRepo(".")
    with pytest.raises(RuntimeError):
        git_repo.clone()

    git_repo = git.GitRepo(".", "https://example.com")
    with patch.multiple(git_repo, git=DEFAULT, path=DEFAULT) as git_mock:
        git_repo.clone()

    git_mock["path"].mkdir.assert_called_with(parents=True, exist_ok=True)
    git_mock["git"].assert_called_with("clone", "--depth", "1", "--branch", "main", "https://example.com", ".")


@patch.object(git, "os")
@patch.object(git, "check_output")
def test_git_scrubs_auth_from_called_process_error(co_mock, os_mock):
    os_mock.getcwd.return_value = "olddir"
    co_mock.side_effect = CalledProcessError(
        128,
        (git.GIT, "fetch", "-f", "https://dude:abides@example.com", "main"),
        output=b"fatal: unable to access 'https://dude:abides@example.com/': error",
    )
    git_repo = git.GitRepo("new_repo", authentication="dude:abides")

    with pytest.raises(CalledProcessError) as excinfo:
        git_repo.git("fetch", "-f", "https://dude:abides@example.com", "main")

    assert "dude:abides" not in str(excinfo.value.cmd)
    assert b"dude:abides" not in excinfo.value.output
    # .args is set independently of .cmd at exception-construction time and
    # doesn't pick up a later mutation of .cmd, so it needs its own scrub.
    assert "dude:abides" not in str(excinfo.value.args)
    assert excinfo.value.__cause__ is None


EXPECTED_AUTH_ENV = {
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "http.https://example.com/.extraheader",
    "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: Basic {base64.b64encode(b'dude:abides').decode('ascii')}",
    "GIT_TERMINAL_PROMPT": "0",
}


@override_settings(DEV=True)
def test_git_clone_with_auth():
    git_repo = git.GitRepo(".", "https://example.com", authentication="dude:abides")
    with patch.multiple(git_repo, git=DEFAULT, path=DEFAULT) as git_mock:
        git_repo.clone()

    git_mock["git"].assert_called_with(
        "clone", "--depth", "1", "--branch", "main", "https://example.com", ".", environment_overrides=EXPECTED_AUTH_ENV
    )


def test_git_pull_with_auth():
    git_repo = git.GitRepo(".", "https://example.com", authentication="dude:abides")
    with patch.object(git_repo, "git") as git_mock:
        git_repo.pull()

    git_mock.assert_any_call("fetch", "-f", "https://example.com", "main", environment_overrides=EXPECTED_AUTH_ENV)


def test_git_pull_with_bare_token_auth():
    git_repo = git.GitRepo(".", "https://example.com", authentication="sometoken")
    with patch.object(git_repo, "git") as git_mock:
        git_repo.pull()

    expected_env = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://example.com/.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: Basic {base64.b64encode(b'x-access-token:sometoken').decode('ascii')}",
        "GIT_TERMINAL_PROMPT": "0",
    }
    git_mock.assert_any_call("fetch", "-f", "https://example.com", "main", environment_overrides=expected_env)


def test_git_push_with_auth():
    git_repo = git.GitRepo(".", "https://example.com", authentication="dude:abides")
    with patch.object(git_repo, "git") as git_mock:
        result = git_repo.push("HEAD:main")

    git_mock.assert_called_with("push", "https://example.com", "HEAD:main", environment_overrides=EXPECTED_AUTH_ENV)
    assert result == git_mock.return_value


def test_git_push_without_auth_passes_no_env():
    git_repo = git.GitRepo(".", "https://example.com")
    with patch.object(git_repo, "git") as git_mock:
        git_repo.push("HEAD:main")

    git_mock.assert_called_with("push", "https://example.com", "HEAD:main")


def test_git_clone_without_auth_passes_no_env():
    git_repo = git.GitRepo(".", "https://example.com")
    with patch.multiple(git_repo, git=DEFAULT, path=DEFAULT) as git_mock:
        git_repo.clone()

    git_mock["git"].assert_called_with("clone", "--depth", "1", "--branch", "main", "https://example.com", ".")


def test_git_split_auth_bare_token():
    git_repo = git.GitRepo(".", "https://example.com", authentication="sometoken")
    assert git_repo._split_auth() == (git.DEFAULT_AUTH_USERNAME, "sometoken")


def test_git_split_auth_username_and_token():
    git_repo = git.GitRepo(".", "https://example.com", authentication="dude:abides")
    assert git_repo._split_auth() == ("dude", "abides")


def test_git_split_auth_none():
    git_repo = git.GitRepo(".", "https://example.com")
    assert git_repo._split_auth() == (None, None)


def test_git_extraheader_config_key_returns_none_for_non_http_url():
    git_repo = git.GitRepo(".", "git@github.com:mozmeao/example.git", authentication="dude:abides")
    assert git_repo._extraheader_config_key() is None


def test_git_extraheader_config_key_omits_default_port():
    git_repo = git.GitRepo(".", "https://example.com/repo", authentication="dude:abides")
    assert git_repo._extraheader_config_key() == "http.https://example.com/.extraheader"


def test_git_extraheader_config_key_includes_non_default_port():
    git_repo = git.GitRepo(".", "https://example.com:8443/repo", authentication="dude:abides")
    assert git_repo._extraheader_config_key() == "http.https://example.com:8443/.extraheader"


def test_git_extraheader_config_key_restores_ipv6_brackets():
    git_repo = git.GitRepo(".", "https://[::1]:8443/repo", authentication="dude:abides")
    assert git_repo._extraheader_config_key() == "http.https://[::1]:8443/.extraheader"


def test_git_extraheader_config_key_returns_none_for_malformed_port():
    git_repo = git.GitRepo(".", "https://example.com:abc/repo", authentication="dude:abides")
    assert git_repo._extraheader_config_key() is None


def test_git_auth_env_rejects_unscopable_remote():
    git_repo = git.GitRepo(".", "git@github.com:mozmeao/example.git", authentication="dude:abides")
    with pytest.raises(RuntimeError):
        with git_repo.auth_env():
            pass


@patch.object(git, "rmtree")
def test_git_reclone_propagates_auth(rmtree_mock):
    git_repo = git.GitRepo(".", "https://example.com", authentication="dude:abides")
    with patch.multiple(git_repo, path=DEFAULT):
        git_repo.path.exists.return_value = True
        with patch.object(git, "GitRepo") as gitrepo_mock:
            git_repo.reclone()

    assert gitrepo_mock.call_args.kwargs["authentication"] == "dude:abides"


@patch.object(git, "rmtree")
def test_git_update(rmtree_mock):
    git_repo = git.GitRepo(".", "https://example.com")
    with patch.multiple(git_repo, clone=DEFAULT, path=DEFAULT, diff=DEFAULT, pull=DEFAULT) as git_mock:
        git_mock["path"].is_dir.return_value = False
        git_repo.update()
        assert git_mock["clone"].called
        git_mock["pull"].assert_not_called()

    rmtree_mock.reset_mock()
    with patch.multiple(git_repo, clone=DEFAULT, path=DEFAULT, diff=DEFAULT, pull=DEFAULT) as git_mock:
        git_mock["path"].is_dir.return_value = True
        git_mock["path"].joinpath().is_dir.return_value = False
        git_repo.update()
        rmtree_mock.assert_called_with(git_repo.path_str, ignore_errors=True)
        assert git_mock["clone"].called
        git_mock["pull"].assert_not_called()

    rmtree_mock.reset_mock()
    with patch.multiple(git_repo, clone=DEFAULT, path=DEFAULT, diff=DEFAULT, pull=DEFAULT) as git_mock:
        git_mock["path"].is_dir.return_value = True
        git_mock["path"].joinpath().is_dir.return_value = True
        val = git_repo.update()
        rmtree_mock.assert_not_called()
        git_mock["clone"].assert_not_called()
        assert git_mock["pull"].called
        assert val == git_mock["pull"].return_value


def test_git_diff():
    git_repo = git.GitRepo(".", "https://example.com")
    with patch.object(git_repo, "git") as git_mock:
        git_mock.return_value = GIT_DIFF_TEST_DATA
        modified, deleted = git_repo.diff("abcd", "ef12")
        git_mock.assert_called_with("diff", "--name-status", "abcd", "ef12")

    assert modified == {
        "media/css/base/home/home.scss",
        "lib/l10n_utils/tests/test_template.py",
        "docs/mozilla-traffic-cop.rst",
        "lib/l10n_utils/management/commands/l10n_update.py",
        "media/css/base/home/home-variant.scss",
        "media/css/pebbles/base/_elements.scss",
        "media/css/newsletter/newsletter-mozilla.scss",
        "media/css/pebbles/components/_buttons-download.scss",
        "media/css/base/technology.less",
        "lib/l10n_utils/tests/test_commands.py",
        "media/css/pebbles/base/elements/_document.scss",
        "media/css/pebbles/base/elements/_typography.scss",
        "media/css/pebbles/base/elements/_links.scss",
        "docs/javascript-libs.rst",
        "docker/run.sh",
        "media/css/pebbles/components/_masthead.scss",
        "media/css/pebbles/components/_footer.scss",
        "media/css/pebbles/components/_modal.scss",
        "media/css/pebbles/base/oldIE.scss",
        "etc/supervisor_available/cron_db.conf",
        "media/css/base/leadership.scss",
        "media/css/pebbles/components/_buttons.scss",
        "media/css/pebbles/base/elements/_lists.scss",
        "etc/supervisor_available/cron_l10n.conf",
        "media/css/pebbles/base/elements/_reset.scss",
        "media/css/pebbles/base/elements/_tables.scss",
        "media/css/pebbles/components/_sections.scss",
        "media/css/firefox/firstrun/ravioli.less",
        "media/css/pebbles/elements/forms.less",
        "media/css/pebbles/base/elements/_forms.scss",
        "media/css/pebbles/components/_base-button.scss",
        "media/css/newsletter/newsletter-firefox.scss",
    }
    assert deleted == {
        "media/css/base/leadership.less",
        "media/css/pebbles/base.less",
        "media/css/pebbles/reset.less",
        "media/css/newsletter/newsletter-mozilla.less",
        "media/css/pebbles/components/footer.less",
        "media/css/pebbles/components/modal.less",
        "media/css/base/home/home.less",
        "etc/supervisor_available/cron.conf",
        "media/css/newsletter/newsletter-firefox.less",
        "media/css/pebbles/oldIE.less",
    }


# real output from git against the springfield repo
GIT_DIFF_TEST_DATA = """\
A       docker/run.sh
M       docs/javascript-libs.rst
A       docs/mozilla-traffic-cop.rst
R072    etc/supervisor_available/cron.conf      etc/supervisor_available/cron_db.conf
A       etc/supervisor_available/cron_l10n.conf
M       lib/l10n_utils/management/commands/l10n_update.py
M       lib/l10n_utils/tests/test_commands.py
M       lib/l10n_utils/tests/test_template.py
A       media/css/firefox/firstrun/ravioli.less
A       media/css/base/home/home-variant.scss
R059    media/css/base/home/home.less media/css/base/home/home.scss
R081    media/css/base/leadership.less        media/css/base/leadership.scss
A       media/css/base/technology.less
R059    media/css/newsletter/newsletter-firefox.less    media/css/newsletter/newsletter-firefox.scss
R063    media/css/newsletter/newsletter-mozilla.less    media/css/newsletter/newsletter-mozilla.scss
D       media/css/pebbles/base.less
A       media/css/pebbles/base/_elements.scss
A       media/css/pebbles/base/elements/_document.scss
C080    media/css/pebbles/elements/forms.less   media/css/pebbles/base/elements/_forms.scss
A       media/css/pebbles/base/elements/_links.scss
A       media/css/pebbles/base/elements/_lists.scss
R100    media/css/pebbles/reset.less    media/css/pebbles/base/elements/_reset.scss
A       media/css/pebbles/base/elements/_tables.scss
A       media/css/pebbles/base/elements/_typography.scss
R064    media/css/pebbles/oldIE.less    media/css/pebbles/base/oldIE.scss
A       media/css/pebbles/components/_base-button.scss
A       media/css/pebbles/components/_buttons-download.scss
A       media/css/pebbles/components/_buttons.scss
R067    media/css/pebbles/components/footer.less        media/css/pebbles/components/_footer.scss
A       media/css/pebbles/components/_masthead.scss
R080    media/css/pebbles/components/modal.less media/css/pebbles/components/_modal.scss
A       media/css/pebbles/components/_sections.scss
D       media/css/pebbles/base.less
"""
