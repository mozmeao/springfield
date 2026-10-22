# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.test import override_settings

import pytest
from wagtail.models import TranslatableMixin

from springfield.cms.models import PartnerRepack

pytestmark = [pytest.mark.django_db]

ACME_PRODUCT = "partner-firefox-release-acme-acme-001-latest"
ACME_WINDOWS64_URL = f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64"
ACME_WINDOWS32_URL = f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win"
ACME_MAC_URL = f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx"
ACME_LINUX_URL = f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=linux64"


def make_partner(**fields):
    defaults = {"name": "Acme", "slug": "acme", "windows64_url": ACME_WINDOWS64_URL, "windows_languages": "en-US, de"}
    return PartnerRepack(**{**defaults, **fields})


def validation_errors(partner):
    with pytest.raises(ValidationError) as excinfo:
        partner.full_clean()
    return excinfo.value.message_dict


def test_valid_partner_saves_with_its_windows_languages():
    partner = make_partner()
    partner.full_clean()
    partner.save()

    assert partner.languages_for("windows") == ["en-US", "de"]
    assert str(partner) == "Acme"


def test_partner_needs_a_download_link():
    errors = validation_errors(make_partner(windows64_url="", windows_languages=""))

    assert errors[NON_FIELD_ERRORS] == ["Add a download link for at least one system."]


def test_link_needs_languages():
    errors = validation_errors(make_partner(mac_url=ACME_MAC_URL))

    assert errors == {"mac_languages": ["Add the languages this build was made for."]}


def test_languages_need_a_link():
    errors = validation_errors(make_partner(linux_languages="en-US"))

    assert errors == {"linux_languages": ["Add a download link, or clear these languages."]}


def test_unknown_languages_are_named_in_the_order_entered():
    errors = validation_errors(make_partner(windows_languages="de, xx, en-ZZ"))

    assert errors == {"windows_languages": ["Not a Firefox download language: xx, en-ZZ."]}


def test_languages_are_stored_in_canonical_form():
    partner = make_partner(windows_languages="EN-us,de  fr\nde")
    partner.full_clean()

    assert partner.windows_languages == "en-US, de, fr"


def test_each_platform_keeps_its_own_languages():
    partner = make_partner(mac_url=ACME_MAC_URL, mac_languages="en-US")
    partner.full_clean()

    assert partner.languages_for("windows") == ["en-US", "de"]
    assert partner.languages_for("mac") == ["en-US"]


@pytest.mark.parametrize("japanese_code", ["ja-JP-mac", "ja-jp-mac"])
@pytest.mark.parametrize("platform", ["windows", "mac"])
def test_mac_japanese_code_is_stored_as_ja(platform, japanese_code):
    other_fields = {"windows": {}, "mac": {"windows64_url": "", "windows_languages": "", "mac_url": ACME_MAC_URL}}
    partner = make_partner(**other_fields[platform], **{f"{platform}_languages": f"de, {japanese_code}"})
    partner.full_clean()

    assert partner.languages_for(platform) == ["de", "ja"]


def test_firefox_user_link_needs_a_label():
    errors = validation_errors(make_partner(firefox_user_link_url="https://acme.example/"))

    assert errors == {"firefox_user_link_label": ["Add a label for this link."]}


def test_firefox_user_link_label_needs_a_link():
    errors = validation_errors(make_partner(firefox_user_link_label="visit"))

    assert errors == {"firefox_user_link_url": ["Add a link for this label."]}


def test_slug_is_unique():
    make_partner().save()

    errors = validation_errors(make_partner(name="Acme again"))

    assert list(errors) == ["slug"]


def test_slug_is_stored_lowercase():
    partner = make_partner(slug="Acme")
    partner.full_clean()

    assert partner.slug == "acme"


def test_slug_is_unique_ignoring_case():
    make_partner().save()

    errors = validation_errors(make_partner(name="Acme again", slug="ACME"))

    assert list(errors) == ["slug"]


def test_partner_is_not_translatable():
    assert not issubclass(PartnerRepack, TranslatableMixin)
    assert "locale" not in {field.name for field in PartnerRepack._meta.get_fields()}


def test_only_published_partners_are_live():
    make_partner(slug="acme-live", live=True).save()
    make_partner(slug="acme-draft", live=False).save()

    assert list(PartnerRepack.objects.live().values_list("slug", flat=True)) == ["acme-live"]


def test_link_in_the_wrong_field_names_its_system():
    errors = validation_errors(make_partner(windows64_url=ACME_WINDOWS32_URL))

    assert errors == {"windows64_url": ["This link is for Windows 32-bit (os=win). Paste it in that field."]}


def test_link_for_an_unknown_system_names_the_fields_system():
    errors = validation_errors(make_partner(mac_url=f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=beos", mac_languages="en-US"))

    assert errors == {"mac_url": ["This link isn't for Mac."]}


def test_link_must_be_on_the_download_host():
    errors = validation_errors(make_partner(windows64_url="https://example.com/?product=x&os=win64"))

    assert errors == {"windows64_url": ["Use the download.mozilla.org link supplied by the product team."]}


def test_link_must_have_a_product():
    errors = validation_errors(
        make_partner(windows64_url="", windows_languages="", mac_url="https://download.mozilla.org/?os=osx", mac_languages="en-US")
    )

    assert errors == {"mac_url": ["This link has no product. Paste the full link supplied by the product team."]}


def test_windows_32_bit_link_alone_is_valid():
    partner = make_partner(windows64_url="", windows32_url=ACME_WINDOWS32_URL)
    partner.full_clean()

    assert partner.languages_for("windows") == ["en-US", "de"]


def test_pasted_link_with_a_lang_is_kept_as_pasted():
    partner = make_partner(windows64_url=f"{ACME_WINDOWS64_URL}&lang=de")
    partner.full_clean()

    assert partner.windows64_url == f"{ACME_WINDOWS64_URL}&lang=de"


def test_partner_with_every_link_is_valid():
    partner = make_partner(
        windows64_url=ACME_WINDOWS64_URL,
        windows32_url=ACME_WINDOWS32_URL,
        mac_url=ACME_MAC_URL,
        mac_languages="en-US",
        linux_url=ACME_LINUX_URL,
        linux_languages="en-US",
    )
    partner.full_clean()

    assert partner.download_url("linux_url", "en-US") == f"{ACME_LINUX_URL}&lang=en-US"


def test_download_url_adds_lang_last():
    partner = make_partner()

    assert partner.download_url("windows64_url", "de") == f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64&lang=de"


def test_download_url_drops_other_pasted_parameters():
    partner = make_partner(windows64_url=f"{ACME_WINDOWS64_URL}&foo=1&lang=fr")

    assert partner.download_url("windows64_url", "de") == f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64&lang=de"


def test_download_url_uses_the_mac_japanese_code_on_mac_only():
    partner = make_partner(windows_languages="ja", mac_url=ACME_MAC_URL, mac_languages="ja")

    assert partner.download_url("mac_url", "ja") == f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx&lang=ja-JP-mac"
    assert partner.download_url("windows64_url", "ja") == f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64&lang=ja"


@override_settings(BOUNCER_URL="https://bouncer.stage.example/")
def test_download_url_always_uses_the_production_download_server():
    partner = make_partner()

    assert partner.download_url("windows64_url", "de").startswith("https://download.mozilla.org/?")


def test_download_url_is_none_for_an_unlisted_language():
    partner = make_partner(windows_languages="de")

    assert partner.download_url("windows64_url", "fr") is None


def test_download_url_is_none_for_a_blank_link():
    partner = make_partner(windows_languages="de")

    assert partner.download_url("windows32_url", "de") is None


PARTNER_REPACK_PERMISSIONS = {"add_partnerrepack", "change_partnerrepack", "delete_partnerrepack", "publish_partnerrepack"}


@pytest.fixture
def permissions_migration():
    # The module name starts with a digit, so it has to be imported by string.
    return import_module("springfield.cms.migrations.0164_partnerrepack")


def test_editors_and_moderators_get_partner_download_permissions(permissions_migration):
    groups = Group.objects.filter(name__in=["Editors", "Moderators"])
    for group in groups:
        group.permissions.clear()

    permissions_migration.add_group_permissions(apps, None)

    assert groups.count() == 2
    for group in groups:
        assert set(group.permissions.values_list("codename", flat=True)) == PARTNER_REPACK_PERMISSIONS


def test_permissions_migration_skips_a_missing_group(permissions_migration):
    Group.objects.filter(name="Moderators").delete()
    editors = Group.objects.get(name="Editors")
    editors.permissions.clear()

    permissions_migration.add_group_permissions(apps, None)

    assert set(editors.permissions.values_list("codename", flat=True)) == PARTNER_REPACK_PERMISSIONS


def test_test_links_list_every_system_and_language_in_order():
    partner = make_partner(
        windows32_url=ACME_WINDOWS32_URL,
        windows_languages="de, en-US",
        mac_url=ACME_MAC_URL,
        mac_languages="fr",
        linux_url=ACME_LINUX_URL,
        linux_languages="en-US",
    )

    assert [(system, lang) for system, lang, url in partner.test_links()] == [
        ("Windows 64-bit", "de"),
        ("Windows 64-bit", "en-US"),
        ("Windows 32-bit", "de"),
        ("Windows 32-bit", "en-US"),
        ("Mac", "fr"),
        ("Linux", "en-US"),
    ]
    assert partner.test_links()[0][2] == partner.download_url("windows64_url", "de")


def test_test_links_are_empty_without_links():
    assert PartnerRepack(name="Acme", slug="acme").test_links() == []


def test_partner_repacks_are_included_in_the_db_export():
    export_script = (settings.ROOT_PATH / "bin" / "export-db-to-sqlite.sh").read_text()

    assert "cms.PartnerRepack" in export_script


def test_download_options_per_platform_state():
    partner = make_partner(windows_languages="de", mac_url=ACME_MAC_URL, mac_languages="fr")

    assert partner.download_options("de") == {
        "windows": {"state": "available", "urls": {"win64": partner.download_url("windows64_url", "de")}},
        "mac": {"state": "language", "urls": {}},
        "linux": {"state": "device", "urls": {}},
    }


def test_download_options_carry_both_windows_links():
    partner = make_partner(windows32_url=ACME_WINDOWS32_URL)

    assert partner.download_options("de")["windows"]["urls"] == {
        "win64": partner.download_url("windows64_url", "de"),
        "win": partner.download_url("windows32_url", "de"),
    }


@pytest.mark.parametrize("link_field, link_os", [("windows64_url", "win64"), ("windows32_url", "win")])
def test_download_options_carry_a_single_windows_link(link_field, link_os):
    partner = make_partner(**{"windows64_url": "", link_field: f"https://download.mozilla.org/?product={ACME_PRODUCT}&os={link_os}"})

    assert list(partner.download_options("de")["windows"]["urls"]) == [link_os]


def test_download_options_have_no_urls_unless_available():
    partner = make_partner(mac_url=ACME_MAC_URL, mac_languages="de", linux_url=ACME_LINUX_URL, linux_languages="de")

    options = partner.download_options("fr")

    assert {platform: option["state"] for platform, option in options.items()} == {"windows": "language", "mac": "language", "linux": "language"}
    assert all(option["urls"] == {} for option in options.values())
