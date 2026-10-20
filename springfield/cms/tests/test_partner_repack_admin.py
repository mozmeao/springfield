# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from html import unescape

from django.contrib.messages import get_messages
from django.urls import reverse

import pytest
from bs4 import BeautifulSoup

from springfield.cms.models import PartnerRepack

pytestmark = [pytest.mark.django_db]

ACME_PRODUCT = "partner-firefox-release-acme-acme-001-latest"
PUBLISHED_MESSAGE = "Published. Visitors see the change within about 20 minutes."


def partner_form_data(**fields):
    return {
        "name": "Acme",
        "slug": "acme",
        "windows64_url": f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64",
        "windows32_url": "",
        "windows_languages": "en-US, de",
        "mac_url": "",
        "mac_languages": "",
        "linux_url": "",
        "linux_languages": "",
        "firefox_user_link_url": "",
        "firefox_user_link_label": "",
        **fields,
    }


def create_partner(live, **fields):
    partner = PartnerRepack(live=False, **{**partner_form_data(), **fields})
    partner.save()
    revision = partner.save_revision()
    if live:
        revision.publish()
    return partner


def success_messages(response):
    """Return the text of each success message, without Wagtail's trailing buttons."""
    return [unescape(str(message).split("\n")[0]) for message in get_messages(response.wsgi_request) if message.level_tag == "success"]


def listing_rows(response):
    """Map each listing row's display name to the row's text."""
    soup = BeautifulSoup(response.content, "html.parser")
    return {row.select_one("td.title a").get_text(strip=True): row.get_text(" ", strip=True) for row in soup.select("table.listing tbody tr")}


def test_listing_shows_live_and_draft_partners(admin_client):
    create_partner(live=True, name="Acme", slug="acme")
    create_partner(
        live=False,
        name="Acme Labs",
        slug="acme-labs",
        mac_url=f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx",
        mac_languages="en-US",
    )

    response = admin_client.get(reverse("wagtailsnippets_cms_partnerrepack:list"))

    rows = listing_rows(response)
    assert set(rows) == {"Acme", "Acme Labs"}
    assert "acme Windows live" in rows["Acme"]
    assert "acme-labs Windows, Mac draft" in rows["Acme Labs"]


@pytest.mark.parametrize("query", ["Labs", "acme-labs"])
def test_listing_searches_by_name_and_slug(admin_client, query):
    create_partner(live=True, name="Acme", slug="acme")
    create_partner(live=True, name="Acme Labs", slug="acme-labs")

    response = admin_client.get(reverse("wagtailsnippets_cms_partnerrepack:list"), {"q": query})

    assert set(listing_rows(response)) == {"Acme Labs"}


def test_users_without_partner_permissions_cannot_see_partner_downloads(limited_admin_client):
    snippets_response = limited_admin_client.get(reverse("wagtailsnippets:index"))
    listing_response = limited_admin_client.get(reverse("wagtailsnippets_cms_partnerrepack:list"))

    assert "Partner downloads" not in snippets_response.content.decode()
    assert listing_response.status_code == 302
    assert listing_response["Location"] == reverse("wagtailadmin_home")


def test_publishing_a_new_partner_says_when_visitors_see_it(admin_client):
    response = admin_client.post(reverse("wagtailsnippets_cms_partnerrepack:add"), {**partner_form_data(), "action-publish": "action-publish"})

    assert PartnerRepack.objects.get(slug="acme").live
    assert success_messages(response) == [PUBLISHED_MESSAGE]


def test_publishing_an_edit_says_when_visitors_see_it(admin_client):
    partner = create_partner(live=True)

    response = admin_client.post(
        reverse("wagtailsnippets_cms_partnerrepack:edit", args=[partner.pk]),
        {**partner_form_data(name="Acme Inc"), "action-publish": "action-publish"},
    )

    partner.refresh_from_db()
    assert partner.name == "Acme Inc"
    assert success_messages(response) == [PUBLISHED_MESSAGE]


def test_publishing_an_earlier_revision_says_when_visitors_see_it(admin_client):
    partner = create_partner(live=True)
    earlier_revision = partner.latest_revision
    partner.name = "Acme Inc"
    partner.save_revision().publish()

    response = admin_client.post(
        reverse("wagtailsnippets_cms_partnerrepack:revisions_revert", args=[partner.pk, earlier_revision.pk]),
        {**partner_form_data(), "action-publish": "action-publish"},
    )

    partner.refresh_from_db()
    assert partner.name == "Acme"
    assert success_messages(response) == [PUBLISHED_MESSAGE]


def test_saving_a_draft_keeps_the_usual_message(admin_client):
    partner = create_partner(live=True)

    response = admin_client.post(reverse("wagtailsnippets_cms_partnerrepack:edit", args=[partner.pk]), partner_form_data(name="Acme Inc"))

    assert success_messages(response) == ["Partner download 'Acme Inc' updated."]


TEST_LINKS_HELP = "The exact links visitors get. Click each one and check that a download starts before you publish."


def find_test_links_help(response):
    """Return the Test links panel's help paragraph from a rendered edit screen."""
    soup = BeautifulSoup(response.content, "html.parser")
    return soup.find("p", string=TEST_LINKS_HELP)


def test_edit_screen_lists_a_test_link_per_system_and_language(admin_client):
    partner = create_partner(
        live=False,
        mac_url=f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx",
        mac_languages="en-US, de",
    )

    response = admin_client.get(reverse("wagtailsnippets_cms_partnerrepack:edit", args=[partner.pk]))

    table = find_test_links_help(response).find_next("table")
    rows = [[cell.get_text(strip=True) for cell in row.find_all("td")] for row in table.select("tbody tr")]
    assert rows == [
        ["Windows 64-bit", "en-US", f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64&lang=en-US"],
        ["Windows 64-bit", "de", f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64&lang=de"],
        ["Mac", "en-US", f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx&lang=en-US"],
        ["Mac", "de", f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx&lang=de"],
    ]
    assert all(link["target"] == "_blank" and link["href"] == link.get_text(strip=True) for link in table.select("a"))


def test_edit_screen_test_link_uses_the_mac_japanese_code(admin_client):
    partner = create_partner(live=False, mac_url=f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx", mac_languages="ja")

    response = admin_client.get(reverse("wagtailsnippets_cms_partnerrepack:edit", args=[partner.pk]))

    mac_links = [link["href"] for link in find_test_links_help(response).find_next("table").select("a") if "os=osx" in link["href"]]
    assert mac_links == [f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=osx&lang=ja-JP-mac"]


def test_create_screen_has_no_test_links_yet(admin_client):
    response = admin_client.get(reverse("wagtailsnippets_cms_partnerrepack:add"))

    help_text = find_test_links_help(response)
    assert help_text.find_parent("section").find("h2").get_text(strip=True) == "Test links"
    assert help_text.find_next("p").get_text(strip=True) == "No links yet"
