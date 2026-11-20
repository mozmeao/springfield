# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import Mock

from django.test.utils import override_settings

from lib.l10n_utils.management.commands.open_ftl_pr import Command


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def list_files(root):
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


@override_settings(FLUENT_REPO_AUTH="")
def test_sync_dirs_purges_removed_files_but_keeps_locales(tmp_path):
    source = tmp_path / "springfield"
    target = tmp_path / "firefoxcom-l10n"

    # springfield's l10n folder
    write_file(source / "l10n-pontoon.toml", "new pontoon config")
    write_file(source / "configs" / "pontoon.toml", "pontoon")
    write_file(source / "en" / "brands.ftl", "updated brands")
    write_file(source / "en" / "firefox" / "new.ftl", "new file")
    write_file(source / "en-US" / "firefox" / "home.ftl", "home")

    # l10n team repo, with obsolete files and locale folders
    write_file(target / ".github" / "workflows" / "ci.yml", "ci")
    write_file(target / "README.md", "readme")
    write_file(target / "l10n-pontoon.toml", "old pontoon config")
    write_file(target / "configs" / "pontoon.toml", "pontoon")
    write_file(target / "configs" / "obsolete.toml", "obsolete")
    write_file(target / "en" / "brands.ftl", "old brands")
    write_file(target / "en" / "404-locale.ftl", "obsolete")
    write_file(target / "en" / "firefox" / "features" / "index.ftl", "obsolete")
    write_file(target / "en-US" / "firefox" / "home.ftl", "home")
    write_file(target / "en-US" / "firefox" / "whatsnew" / "whatsnew-fx80.ftl", "obsolete")
    write_file(target / "fr" / "brands.ftl", "marques")
    write_file(target / "fr" / "404-locale.ftl", "translated")

    command = Command()
    command.l10n_repo = Mock(path=target)
    with override_settings(FLUENT_LOCAL_PATH=source):
        command.sync_dirs()

    assert list_files(target) == [
        ".github/workflows/ci.yml",
        "README.md",
        "configs/pontoon.toml",
        "en-US/firefox/home.ftl",
        "en/brands.ftl",
        "en/firefox/new.ftl",
        "fr/404-locale.ftl",
        "fr/brands.ftl",
        "l10n-pontoon.toml",
    ]
    assert not (target / "en" / "firefox" / "features").exists()
    assert not (target / "en-US" / "firefox" / "whatsnew").exists()
    assert (target / "en" / "brands.ftl").read_text() == "updated brands"
    assert (target / "l10n-pontoon.toml").read_text() == "new pontoon config"
    assert (target / "fr" / "brands.ftl").read_text() == "marques"
