# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from django.core.management.base import CommandError

import pytest

from lib.l10n_utils.management.commands.process_ftl import Command
from springfield.utils.git import GitRepo


def test_push_changes_uses_configured_branch_name():
    # Regression test: push_changes() used to hardcode "HEAD:main",
    # regardless of what branch_name the repo was actually configured
    # with (FLUENT_REPO_BRANCH), so a push could silently target the
    # wrong branch.
    command = Command()
    command.meao_repo = GitRepo(".", "https://github.com/mozmeao/www-firefox-l10n", "release", authentication="dude:abides")

    with patch.object(command.meao_repo, "push") as push_mock, patch.object(command.meao_repo, "git") as git_mock:
        git_mock.return_value = "abc1234"
        command.push_changes()

    push_mock.assert_called_with("HEAD:release")


def test_push_changes_raises_without_authentication():
    command = Command()
    command.meao_repo = GitRepo(".", "https://github.com/mozmeao/www-firefox-l10n", "main")

    with pytest.raises(CommandError):
        command.push_changes()
