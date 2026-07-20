# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest
import wagtail_factories
from wagtail.contrib.redirects.models import Redirect

from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


def _write_csv(tmp_path, rows, filename="redirects.csv"):
    path = tmp_path / filename
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["wp_id", "old_permalink", "new_page_id", "new_page_path"])
        writer.writerows(rows)
    return path


@pytest.fixture
def target_page(minimal_site):
    return SimpleRichTextPageFactory(slug="target-page", title="Target Page")


def test_missing_csv_file_raises_command_error(tmp_path):
    with pytest.raises(CommandError, match="File not found"):
        call_command("import_wordpress_redirects", str(tmp_path / "nope.csv"))


def test_unknown_site_hostname_raises_command_error(tmp_path, target_page):
    csv_path = _write_csv(tmp_path, [("1", "https://old.example.com/a/", target_page.id, target_page.url)])
    with pytest.raises(CommandError, match="No Site found"):
        call_command("import_wordpress_redirects", str(csv_path), site="nonexistent.example.com")


def test_creates_redirect_for_each_row(tmp_path, target_page):
    csv_path = _write_csv(tmp_path, [("1", "https://old.example.com/a/", target_page.id, target_page.url)])
    out = StringIO()
    call_command("import_wordpress_redirects", str(csv_path), stdout=out)

    redirect = Redirect.objects.get(old_path="/a")
    assert redirect.redirect_page_id == target_page.id
    assert redirect.is_permanent is True
    assert redirect.automatically_created is True
    assert redirect.site is None
    assert "Done. 1 created, 0 already existed, 0 referenced a missing page." in out.getvalue()


def test_dry_run_creates_no_redirects(tmp_path, target_page):
    csv_path = _write_csv(tmp_path, [("1", "https://old.example.com/a/", target_page.id, target_page.url)])
    out = StringIO()
    call_command("import_wordpress_redirects", str(csv_path), dry_run=True, stdout=out)

    assert Redirect.objects.count() == 0
    assert "[dry-run]" in out.getvalue()
    assert "Done. 1 created, 0 already existed, 0 referenced a missing page." in out.getvalue()


def test_missing_page_is_skipped_and_counted(tmp_path):
    csv_path = _write_csv(tmp_path, [("1", "https://old.example.com/a/", 999999, "/does/not/exist/")])
    out = StringIO()
    err = StringIO()
    call_command("import_wordpress_redirects", str(csv_path), stdout=out, stderr=err)

    assert Redirect.objects.count() == 0
    assert "page id 999999 not found" in err.getvalue()
    assert "Done. 0 created, 0 already existed, 1 referenced a missing page." in out.getvalue()


def test_existing_redirect_is_skipped(tmp_path, target_page):
    Redirect.add_redirect(old_path="https://old.example.com/a/", redirect_to=target_page)
    csv_path = _write_csv(tmp_path, [("1", "https://old.example.com/a/", target_page.id, target_page.url)])
    out = StringIO()
    call_command("import_wordpress_redirects", str(csv_path), stdout=out)

    assert Redirect.objects.count() == 1
    assert "skip (already exists): https://old.example.com/a/" in out.getvalue()
    assert "Done. 0 created, 1 already existed, 0 referenced a missing page." in out.getvalue()


def test_site_option_scopes_redirect_to_site(tmp_path, target_page):
    site = wagtail_factories.SiteFactory(hostname="example.com", root_page=target_page)
    csv_path = _write_csv(tmp_path, [("1", "https://old.example.com/a/", target_page.id, target_page.url)])
    call_command("import_wordpress_redirects", str(csv_path), site="example.com")

    redirect = Redirect.objects.get(old_path="/a")
    assert redirect.site_id == site.id


def test_multiple_rows_are_all_processed(tmp_path, target_page):
    other_page = SimpleRichTextPageFactory(slug="other-page", title="Other Page")
    csv_path = _write_csv(
        tmp_path,
        [
            ("1", "https://old.example.com/a/", target_page.id, target_page.url),
            ("2", "https://old.example.com/b/", other_page.id, other_page.url),
        ],
    )
    out = StringIO()
    call_command("import_wordpress_redirects", str(csv_path), stdout=out)

    assert Redirect.objects.count() == 2
    assert "Done. 2 created, 0 already existed, 0 referenced a missing page." in out.getvalue()
