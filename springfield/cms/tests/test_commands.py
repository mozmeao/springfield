# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import call, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

import everett
import pytest
from wagtail.models import Page
from wagtail_localize.models import StringTranslation, Translation, TranslationSource

from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory


@patch("springfield.cms.management.commands.bootstrap_local_admin.sys.stdout.write")
class BootstrapLocalAdminTests(TransactionTestCase):
    def _run_test(self, mock_write, expected_output):
        out = StringIO()
        call_command("bootstrap_local_admin", stdout=out)
        output = mock_write.call_args_list
        self.assertEqual(output, expected_output)

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "", "WAGTAIL_ADMIN_PASSWORD": ""})
    def test_no_env_vars_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Not bootstrapping an Admin user: WAGTAIL_ADMIN_EMAIL not defined in environment\n"),
            ],
        )

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "test@mozilla.com", "WAGTAIL_ADMIN_PASSWORD": ""})
    def test_email_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Created Admin user test@mozilla.com for local SSO use\n"),
            ],
        )

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "test@example.com", "WAGTAIL_ADMIN_PASSWORD": ""})
    def test_email_available_but_not_moco(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Not bootstrapping an Admin user: WAGTAIL_ADMIN_EMAIL is not a @mozilla.com email address\n"),
            ],
        )

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "test@mozilla.com", "WAGTAIL_ADMIN_PASSWORD": "secret"})
    def test_email_and_password_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Created Admin user test@mozilla.com with password 'secret'\n"),
            ],
        )

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "", "WAGTAIL_ADMIN_PASSWORD": ""})
    def test_only_password_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Not bootstrapping an Admin user: WAGTAIL_ADMIN_EMAIL not defined in environment\n"),
            ],
        )

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "test@mozilla.com", "WAGTAIL_ADMIN_PASSWORD": ""})
    def test_existing_user_exists_email_only(self, mock_write):
        out = StringIO()
        call_command("bootstrap_local_admin", stdout=out)
        call_command("bootstrap_local_admin", stdout=out)
        output = mock_write.call_args_list
        expected_output = [
            call("Created Admin user test@mozilla.com for local SSO use\n"),
            call("Admin user test@mozilla.com already exists\n"),
        ]
        self.assertEqual(output, expected_output)

    @patch.dict("os.environ", {"WAGTAIL_ADMIN_EMAIL": "test@mozilla.com", "WAGTAIL_ADMIN_PASSWORD": "secret"})
    def test_existing_user_exists_email_and_password(self, mock_write):
        out = StringIO()
        call_command("bootstrap_local_admin", stdout=out)
        call_command("bootstrap_local_admin", stdout=out)
        output = mock_write.call_args_list
        expected_output = [
            call("Created Admin user test@mozilla.com with password 'secret'\n"),
            call("Admin user test@mozilla.com already exists\n"),
        ]
        self.assertEqual(output, expected_output)


@patch("springfield.cms.management.commands.bootstrap_demo_server_admins.sys.stdout.write")
class BootstrapDemoAdminsTests(TransactionTestCase):
    maxDiff = None

    def _run_test(self, mock_write, expected_output):
        out = StringIO()
        call_command("bootstrap_demo_server_admins", stdout=out)
        output = mock_write.call_args_list
        self.assertEqual(output, expected_output)

    @patch.dict("os.environ", {"DEMO_SERVER_ADMIN_USERS": ""})
    def test_no_env_vars_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Not bootstrapping users: DEMO_SERVER_ADMIN_USERS not set\n"),
            ],
        )

    @patch.dict("os.environ", {"DEMO_SERVER_ADMIN_USERS": ","})
    def test_only_empty_list_available(self, mock_write):
        with self.assertRaises(everett.InvalidValueError):
            self._run_test(
                mock_write=None,
                expected_output=None,
            )

    @patch.dict("os.environ", {"DEMO_SERVER_ADMIN_USERS": "test@mozilla.com, test2@mozilla.com,  test3@mozilla.com "})
    def test_multiple_emails_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Bootstrapping 3 SSO users\n"),
                call("Created Admin user test@mozilla.com for local SSO use\n"),
                call("Created Admin user test2@mozilla.com for local SSO use\n"),
                call("Created Admin user test3@mozilla.com for local SSO use\n"),
            ],
        )

    @patch.dict("os.environ", {"DEMO_SERVER_ADMIN_USERS": "testadmin@mozilla.com"})
    def test_single_email_available(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Bootstrapping 1 SSO users\n"),
                call("Created Admin user testadmin@mozilla.com for local SSO use\n"),
            ],
        )

    @patch.dict("os.environ", {"DEMO_SERVER_ADMIN_USERS": "testadmin@mozilla.com"})
    def test_user_created_has_appropriate_perms(self, mock_write):
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Bootstrapping 1 SSO users\n"),
                call("Created Admin user testadmin@mozilla.com for local SSO use\n"),
            ],
        )
        user = User.objects.get(email="testadmin@mozilla.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertFalse(user.has_usable_password())

    @patch.dict("os.environ", {"DEMO_SERVER_ADMIN_USERS": "test@mozilla.com, test2@mozilla.com, test3@mozilla.com"})
    def test_multiple_emails_available_but_exist_already_somehow(self, mock_write):
        # This is not likely to happen in reality, but worth testing
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Bootstrapping 3 SSO users\n"),
                call("Created Admin user test@mozilla.com for local SSO use\n"),
                call("Created Admin user test2@mozilla.com for local SSO use\n"),
                call("Created Admin user test3@mozilla.com for local SSO use\n"),
            ],
        )
        mock_write.reset_mock()
        self._run_test(
            mock_write=mock_write,
            expected_output=[
                call("Bootstrapping 3 SSO users\n"),
                call("User test@mozilla.com already exists - not creating\n"),
                call("User test2@mozilla.com already exists - not creating\n"),
                call("User test3@mozilla.com already exists - not creating\n"),
            ],
        )


class SmartlingSyncTests(TestCase):
    @patch("springfield.cms.management.commands.run_smartling_sync.call_command")
    def test_sentry_logging_for_run_smartling_sync_command(self, mock_call_command):
        test_exception = Exception("Boom!")
        mock_call_command.side_effect = test_exception
        with patch("springfield.cms.management.commands.run_smartling_sync.capture_exception") as mock_capture_exception:
            call_command("run_smartling_sync")
        mock_capture_exception.assert_called_once_with(test_exception)

    @patch("springfield.cms.management.commands.bootstrap_local_admin.sys.stderr.write")
    @patch("springfield.cms.management.commands.run_smartling_sync.call_command")
    def test_error_messaging_for_run_smartling_sync_command(self, mock_call_command, mock_stderr_write):
        test_exception = Exception("Boom!")
        mock_call_command.side_effect = test_exception
        call_command("run_smartling_sync")

        expected_output = "\nsync_smartling did not execute successfully: Boom!\n"
        output = mock_stderr_write.call_args_list[0][0][0]
        self.assertEqual(output, expected_output)


# ---------------------------------------------------------------------------
# Helpers shared by LinkTranslationsAfterExport tests
# ---------------------------------------------------------------------------


def _run_link_translations(**options):
    """Run link_translations_after_export; return (stdout_str, stderr_str)."""
    out = StringIO()
    err = StringIO()
    call_command("link_translations_after_export", stdout=out, stderr=err, **options)
    return out.getvalue(), err.getvalue()


def _clear_localize_records():
    """Delete all wagtail_localize records to simulate the post-DB-export state."""
    TranslationSource.objects.all().delete()
    # Cascades via FK to Translation, StringTranslation, StringSegment, etc.


def _make_translated_page(target_locale, *, en_slug, en_title, translated_title=None):
    """
    Create an en-US content page (under the existing site home) and copy it to
    *target_locale*.  If *translated_title* is provided the translated page is
    updated and published with that title so that a StringTranslation can later
    be inferred.  Returns (en_page, translated_page).
    """
    en_home = Page.objects.get(slug="home")
    en_page = SimpleRichTextPageFactory(parent=en_home, slug=en_slug, title=en_title)
    translated_page = en_page.copy_for_translation(target_locale)
    if translated_title:
        translated_page.title = translated_title
        translated_page.save_revision().publish()
    return en_page, translated_page


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLinkTranslationsAfterExport:
    """Tests for the link_translations_after_export management command."""

    def test_no_pages(self):
        """Command completes cleanly when there are no multi-locale page groups."""
        out, err = _run_link_translations()
        assert "TranslationSources: 0" in out
        assert "Translations: 0" in out
        assert "StringTranslations: 0" in out
        assert "Errors: 0" in out
        assert err == ""

    def test_untranslated_page(self):
        """A page existing only in one locale creates no wagtail_localize records."""
        en_home = Page.objects.get(slug="home")
        SimpleRichTextPageFactory(parent=en_home, slug="en-only", title="English Only")
        _clear_localize_records()

        out, err = _run_link_translations()

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # Nothing was translated.
        assert TranslationSource.objects.count() == 0
        assert Translation.objects.count() == 0
        assert "TranslationSources: 0" in out

    def test_translated_page_creates_structural_records(self):
        """TranslationSource and Translation records are recreated for translated pages."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        en_home.copy_for_translation(fr_locale)

        en_page, _ = _make_translated_page(fr_locale, en_slug="structural-en", en_title="Structural EN")
        _clear_localize_records()

        assert TranslationSource.objects.count() == 0
        assert Translation.objects.count() == 0

        out, err = _run_link_translations()

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # Two multi-locale groups: en_home↔fr_home and en_page↔fr_page
        assert TranslationSource.objects.count() == 2
        assert Translation.objects.filter(enabled=True).count() == 2
        # The content page's group is specifically linked
        en_home_source = TranslationSource.objects.get(object_id=str(en_home.translation_key))
        assert Translation.objects.filter(source=en_home_source, target_locale=fr_locale, enabled=True).exists()
        en_page_source = TranslationSource.objects.get(object_id=str(en_page.translation_key))
        assert Translation.objects.filter(source=en_page_source, target_locale=fr_locale, enabled=True).exists()

    def test_translated_page_creates_string_translations(self):
        """StringTranslation records are created when translated content differs from source."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        fr_home = en_home.copy_for_translation(fr_locale)

        en_page, fr_page = _make_translated_page(
            fr_locale,
            en_slug="string-en",
            en_title="English Title",
            translated_title="Titre français",
        )
        _clear_localize_records()
        assert StringTranslation.objects.count() == 0

        out, err = _run_link_translations()

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # StringTranslations were created
        assert StringTranslation.objects.count() == 2
        # There is a StringTranslation for the fr homepage slug (the fr homepage
        # exists because the translated fr page needs a homepage to exist)
        assert StringTranslation.objects.filter(data=fr_home.slug).exists()
        # There is a StringTranslation for the translated page in the fr locale
        assert StringTranslation.objects.filter(data=fr_page.title).exists()
        # The fr_page slug matches the en_page slug, so there is no StringTranslation for it
        assert en_page.slug == fr_page.slug

    def test_dry_run(self):
        """--dry-run prints a warning but makes no DB changes."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        en_home.copy_for_translation(fr_locale)
        _make_translated_page(fr_locale, en_slug="dry-run-en", en_title="Dry Run EN")
        _clear_localize_records()

        out, err = _run_link_translations(dry_run=True)

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # No translations were created
        assert TranslationSource.objects.count() == 0
        assert Translation.objects.count() == 0
        assert "DRY RUN" in out

    def test_skip_string_translations(self):
        """--skip-string-translations creates structural records but no StringTranslations."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        en_home.copy_for_translation(fr_locale)
        _make_translated_page(
            fr_locale,
            en_slug="skip-strings-en",
            en_title="Skip Strings EN",
            translated_title="Skip Strings FR",
        )
        _clear_localize_records()

        out, err = _run_link_translations(skip_string_translations=True)

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # A TranslationSource and a Translation were created, but no StringTranslations.
        assert TranslationSource.objects.count() >= 1
        assert Translation.objects.filter(enabled=True).count() >= 1
        assert StringTranslation.objects.count() == 0
        assert "StringTranslations: 0" in out

    def test_page_ids_filters_to_matching_group(self):
        """--page_ids limits processing to groups that contain a specified page ID."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        en_home.copy_for_translation(fr_locale)

        en_page1, _ = _make_translated_page(fr_locale, en_slug="group1-en", en_title="Group 1 EN")
        en_page2, _ = _make_translated_page(fr_locale, en_slug="group2-en", en_title="Group 2 EN")
        _clear_localize_records()

        out, err = _run_link_translations(page_ids=str(en_page1.pk))

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # The en_page1 was translated into the fr locale.
        assert TranslationSource.objects.count() == 1
        en_page1_source = TranslationSource.objects.filter(object_id=str(en_page1.translation_key)).first()
        assert Translation.objects.count() == 1
        assert Translation.objects.filter(source=en_page1_source, target_locale__language_code="fr")
        assert "matching --page_ids filter" in out

    def test_page_ids_accepts_target_page_id(self):
        """--page_ids works when a translated (target) page ID is passed instead of source ID."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        en_home.copy_for_translation(fr_locale)

        en_page, fr_page = _make_translated_page(fr_locale, en_slug="target-id-en", en_title="Target ID EN")
        _clear_localize_records()

        # Pass the translated page's pk — the whole group should be linked
        out, err = _run_link_translations(page_ids=str(fr_page.pk))

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # The en_page was translated into the fr_page.
        assert "TranslationSources: 1" in out
        assert "Translations: 1" in out
        assert TranslationSource.objects.count() == 1
        assert Translation.objects.count() == 1
        source = TranslationSource.objects.filter(object_id=str(en_page.translation_key)).first()
        assert source is not None
        assert Translation.objects.filter(source=source, target_locale=fr_locale).exists()

    def test_page_ids_invalid_input_raises_system_exit(self):
        """--page_ids rejects non-integer values with a SystemExit."""
        with pytest.raises(SystemExit):
            _run_link_translations(page_ids="not-a-number")

    def test_idempotent(self):
        """Running the command twice produces identical record counts."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        en_home.copy_for_translation(fr_locale)
        _make_translated_page(
            fr_locale,
            en_slug="idempotent-en",
            en_title="Idempotent EN",
            translated_title="Idempotent FR",
        )
        _clear_localize_records()

        _run_link_translations()
        source_count = TranslationSource.objects.count()
        translation_count = Translation.objects.count()
        string_count = StringTranslation.objects.count()

        _run_link_translations()
        assert TranslationSource.objects.count() == source_count
        assert Translation.objects.count() == translation_count
        assert StringTranslation.objects.count() == string_count

    def test_multiple_target_locales(self):
        """Pages translated into multiple locales each get their own Translation record."""
        en_home = Page.objects.get(slug="home")
        fr_locale = LocaleFactory(language_code="fr")
        de_locale = LocaleFactory(language_code="de")
        en_home.copy_for_translation(fr_locale)
        en_home.copy_for_translation(de_locale)

        en_page, _ = _make_translated_page(fr_locale, en_slug="multi-locale-en", en_title="Multi Locale EN")
        en_page.copy_for_translation(de_locale)
        _clear_localize_records()

        out, err = _run_link_translations()

        # There were no errors.
        assert "Errors: 0" in out
        assert err == ""
        # The en_home was translated into fr and de locales, and also, the
        # en_page was translated into the fr and de locales.
        assert "TranslationSources: 2" in out
        assert "Translations: 4" in out
        assert TranslationSource.objects.count() == 2
        en_home_source = TranslationSource.objects.filter(object_id=str(en_home.translation_key)).first()
        en_page_source = TranslationSource.objects.filter(object_id=str(en_page.translation_key)).first()
        assert Translation.objects.count() == 4
        assert Translation.objects.filter(source=en_home_source, target_locale__language_code="fr")
        assert Translation.objects.filter(source=en_home_source, target_locale__language_code="de")
        assert Translation.objects.filter(source=en_page_source, target_locale__language_code="fr")
        assert Translation.objects.filter(source=en_page_source, target_locale__language_code="de")


class TestGenerateFlareIconCssCommand(TestCase):
    """Tests for the generate_flare_icon_css management command."""

    def _run_command(self, icon_dir, output):
        out = StringIO()
        call_command("generate_flare_icon_css", icon_dir=str(icon_dir), output=str(output), stdout=out)
        return out.getvalue()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.icon_dir = self.tmp / "icons"
        self.icon_dir.mkdir()
        self.output_file = self.tmp / "out.css"

    def _make_svg(self, *parts):
        """Create an SVG file at icon_dir / *parts, creating parent dirs as needed."""
        path = self.icon_dir.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<svg/>")
        return path

    def _run(self):
        # icon_dir is self.tmp / "icons"; static_dir is self.tmp so that
        # icon_dir_static_path resolves to "icons" and static() produces /static/icons/...
        with patch("django.conf.settings.ROOT_PATH", self.tmp), patch("django.conf.settings.STATICFILES_DIRS", [self.tmp]):
            return self._run_command(
                icon_dir=Path("icons"),
                output=Path("out.css"),
            )

    def test_generates_rule_for_each_svg(self):
        self._make_svg("a", "icon-a.svg")
        self._make_svg("b", "icon-b.svg")
        self._make_svg("c", "icon-c.svg")
        self._run()
        css = self.output_file.read_text()
        assert css.count("{") == 3

    def test_class_name_is_stem_without_size_suffix(self):
        self._make_svg("activity", "activity-16.svg")
        self._run()
        css = self.output_file.read_text()
        assert ".fl-icon-activity {" in css
        assert ".fl-icon-activity-16 {" not in css

    def test_icon_url_value(self):
        self._make_svg("activity", "activity-16.svg")
        with patch("django.conf.settings.ROOT_PATH", self.tmp), patch("django.conf.settings.STATICFILES_DIRS", [self.tmp]):
            self._run_command(icon_dir=Path("icons"), output=Path("out.css"))
        css = self.output_file.read_text()
        assert "--icon-src: url(" in css
        assert "activity-16.svg" in css

    def test_conflict_detection_adds_folder_prefix(self):
        self._make_svg("arrows", "left-16.svg")
        self._make_svg("user", "left-16.svg")
        self._run()
        css = self.output_file.read_text()
        assert ".fl-icon-arrows-left {" in css
        assert ".fl-icon-user-left {" in css
        assert ".fl-icon-left {" not in css

    def test_non_svg_files_excluded(self):
        self._make_svg("a", "icon.svg")
        (self.icon_dir / "a" / "readme.txt").write_text("text")
        (self.icon_dir / "a" / "data.json").write_text("{}")
        self._run()
        css = self.output_file.read_text()
        assert css.count("{") == 1

    def test_hidden_files_excluded(self):
        self._make_svg("a", "visible.svg")
        (self.icon_dir / "a" / ".hidden.svg").write_text("<svg/>")
        self._run()
        css = self.output_file.read_text()
        assert ".fl-icon-visible {" in css
        assert ".fl-icon-.hidden {" not in css
        assert css.count("{") == 1

    def test_mpl_header_present(self):
        self._make_svg("a", "icon.svg")
        self._run()
        css = self.output_file.read_text()
        assert "Mozilla Public" in css
        assert "https://mozilla.org/MPL/2.0/" in css

    def test_run_command_comment_present(self):
        self._make_svg("a", "icon.svg")
        self._run()
        css = self.output_file.read_text()
        assert "generate_flare_icon_css" in css

    def test_output_file_written(self):
        self._make_svg("a", "icon.svg")
        self._run()
        assert self.output_file.exists()

    def test_summary_line_printed(self):
        self._make_svg("a", "icon-a.svg")
        self._make_svg("b", "icon-b.svg")
        out = self._run()
        assert "Generated 2 rules" in out

    def test_conflict_warning_printed(self):
        self._make_svg("arrows", "left-16.svg")
        self._make_svg("user", "left-16.svg")
        out = self._run()
        assert "conflict" in out.lower()
        assert "ACTION REQUIRED" in out

    def test_no_conflict_warning_when_no_conflicts(self):
        self._make_svg("a", "icon-a.svg")
        self._make_svg("b", "icon-b.svg")
        out = self._run()
        assert "ACTION REQUIRED" not in out

    def test_missing_icon_dir_raises_command_error(self):
        from django.core.management.base import CommandError

        with patch("django.conf.settings.ROOT_PATH", self.tmp):
            with self.assertRaises(CommandError):
                self._run_command(icon_dir=Path("nonexistent"), output=Path("out.css"))
