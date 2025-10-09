# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model

import pytest
import wagtail_factories
from wagtail.models import Locale, Page, Site

from springfield.cms.models import PageTranslationData
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

User = get_user_model()


@pytest.fixture
def minimal_site(
    client,
    top_level_page=None,
):
    # Bootstraps a minimal site with a root page at / and one child page at /test-page/

    if top_level_page is None:
        top_level_page = SimpleRichTextPageFactory(
            slug="root_page",  # this doesn't get shown
            live=True,
        )

    try:
        site = Site.objects.get(is_default_site=True)
        site.root_page = top_level_page
        site.hostname = client._base_environ()["SERVER_NAME"]
        site.save()
    except Site.DoesNotExist:
        site = wagtail_factories.SiteFactory(
            root_page=top_level_page,
            is_default_site=True,
            hostname=client._base_environ()["SERVER_NAME"],
        )

    LocaleFactory(language_code="fr")

    SimpleRichTextPageFactory(
        slug="test-page",
        parent=top_level_page,
        title="Test Page",
    )

    return site


@pytest.fixture
def tiny_localized_site():
    """
    Generates a small site tree with some pages in other languages:

    en-US:
        / [Page]
            /test-page [SimpleRichTextPage]
                /child-page [SimpleRichTextPage]
    fr:
        / [Page]
            /test-page [SimpleRichTextPage]
                /child-page [SimpleRichTextPage]
                    /grandchild-page [SimpleRichTextPage] <- no parallel page
    pt-BR:
        / [Page]
            /test-page [SimpleRichTextPage]
                /child-page [SimpleRichTextPage]

    Note: no aliases exist
    """

    en_us_locale = Locale.objects.get(language_code="en-US")
    fr_locale = LocaleFactory(language_code="fr")
    pt_br_locale = LocaleFactory(language_code="pt-BR")

    site = Site.objects.get(is_default_site=True)

    en_us_root_page = site.root_page
    fr_root_page = en_us_root_page.copy_for_translation(fr_locale)
    pt_br_root_page = en_us_root_page.copy_for_translation(pt_br_locale)

    en_us_homepage = SimpleRichTextPageFactory(
        title="Test Page",
        slug="test-page",
        parent=en_us_root_page,
    )

    en_us_child = SimpleRichTextPageFactory(
        title="Child",
        slug="child-page",
        parent=en_us_homepage,
    )

    fr_homepage = en_us_homepage.copy_for_translation(fr_locale)
    fr_homepage.title = "Page de Test"
    fr_homepage.save()
    rev = fr_homepage.save_revision()
    fr_homepage.publish(rev)

    fr_child = en_us_child.copy_for_translation(fr_locale)
    fr_child.title = "Enfant"
    fr_child.save()
    rev = fr_child.save_revision()
    fr_child.publish(rev)

    # WARNING: there may be a bug with the page tree here
    # fr_grandchild cannot be found with Page.find_for_request
    # when all the others can. TODO: debug this, but manually
    # it works
    fr_grandchild = SimpleRichTextPageFactory(
        title="Petit-enfant",
        slug="grandchild-page",
        locale=fr_locale,
        parent=fr_child,
    )

    pt_br_homepage = en_us_homepage.copy_for_translation(pt_br_locale)
    pt_br_homepage.title = "Página de Teste"
    pt_br_homepage.save()
    rev = pt_br_homepage.save_revision()
    pt_br_homepage.publish(rev)

    pt_br_child = fr_child.copy_for_translation(pt_br_locale)
    pt_br_child.title = "Página Filha"
    pt_br_child.save()
    rev = pt_br_child.save_revision()
    pt_br_child.publish(rev)

    assert en_us_root_page.locale == en_us_locale
    assert pt_br_root_page.locale == pt_br_locale
    assert fr_root_page.locale == fr_locale

    assert en_us_homepage.locale == en_us_locale
    assert en_us_child.locale == en_us_locale

    assert fr_homepage.locale == fr_locale
    assert fr_child.locale == fr_locale
    assert fr_grandchild.locale == fr_locale

    assert pt_br_homepage.locale == pt_br_locale
    assert pt_br_child.locale == pt_br_locale

    for page in (en_us_homepage, en_us_child, pt_br_homepage, pt_br_child, fr_homepage, fr_child, fr_grandchild):
        page.refresh_from_db()

    assert en_us_homepage.live is True
    assert en_us_child.live is True
    assert pt_br_homepage.live is True
    assert pt_br_child.live is True
    assert fr_homepage.live is True
    assert fr_child.live is True
    assert fr_grandchild.live is True


@pytest.fixture
def staff_user(base_url, request):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass", is_staff=True)

    return user


@pytest.fixture
def site_with_en_de_fr_it_homepages():
    """
    Generates a small site tree with home pages in the following languages:

    en-US:
        / [Page]
    de:
        / [Page]
    fr:
        / [Page]
    it:
        / [Page]
    """
    # Get or create locales
    en_locale, created = Locale.objects.get_or_create(language_code="en-US")
    de_locale, created = Locale.objects.get_or_create(language_code="de")
    fr_locale, created = Locale.objects.get_or_create(language_code="fr")
    it_locale, created = Locale.objects.get_or_create(language_code="it")

    # Set default locale
    if not Locale.objects.filter(language_code="en-US").exists():
        Locale.objects.create(language_code="en-US")

    # Get the English home page
    en_home = Page.objects.get(locale__language_code="en-US", slug="home")

    # Create German home page as a translation of the English home page
    de_home = en_home.copy_for_translation(de_locale)
    de_home.title = "German Home"
    de_home.save_revision().publish()

    # Create French home page as a translation of the English home page
    fr_home = en_home.copy_for_translation(fr_locale)
    fr_home.title = "French Home"
    fr_home.save_revision().publish()

    # Create Italian home page as a translation of the English home page
    it_home = en_home.copy_for_translation(it_locale)
    it_home.title = "Italian Home"
    it_home.save_revision().publish()


@pytest.fixture
def site_with_en_de_fr_it_homepages_1_en_page(site_with_en_de_fr_it_homepages):
    """
    Generates a small site tree with homepages and 1 English page:

    en-US:
        / [Page]
            /english-page [SimpleRichTextPage]
    de:
        / [Page]
    fr:
        / [Page]
    it:
        / [Page]
    """
    # Get the locales
    en_locale = Locale.objects.get(language_code="en-US")

    # Get the home pages
    en_home = Page.objects.get(locale__language_code="en-US", slug="home")

    # Create a page originally in English.
    en_page = SimpleRichTextPageFactory(
        title="English Original",
        slug="english-page",
        locale=en_locale,
        content="English content",
        parent=en_home,
    )
    en_page.save_revision().publish()


@pytest.fixture
def site_with_en_de_fr_it_homepages_and_some_translations(site_with_en_de_fr_it_homepages):
    """
    Generates a small site tree with a few pages:

    en-US:
        / [Page]
            /english-page [SimpleRichTextPage]
    de:
        / [Page]
            /german-page [SimpleRichTextPage]
            /english-page [SimpleRichTextPage] - translation of the en-US english-page
    fr:
        / [Page]
            /french-page [SimpleRichTextPage]
            /english-page [SimpleRichTextPage] - translation of the en-US english-page
    it:
        / [Page]
            /french-page [SimpleRichTextPage] - translation of the fr french-page
    """
    # Get the locales
    en_locale = Locale.objects.get(language_code="en-US")
    de_locale = Locale.objects.get(language_code="de")
    fr_locale = Locale.objects.get(language_code="fr")
    it_locale = Locale.objects.get(language_code="it")

    # Get the home pages
    en_home = Page.objects.get(locale__language_code="en-US", slug="home")
    de_home = Page.objects.get(locale__language_code="de", slug="home-de")
    fr_home = Page.objects.get(locale__language_code="fr", slug="home-fr")

    # Create a page originally in English.
    en_page = SimpleRichTextPageFactory(
        title="English Original",
        slug="english-page",
        locale=en_locale,
        content="English content",
        parent=en_home,
    )
    en_page.save_revision().publish()

    # Create a page originally in German.
    de_page = SimpleRichTextPageFactory(
        title="German Original",
        slug="german-page",
        locale=de_locale,
        content="German content",
        parent=de_home,
    )
    de_page.save_revision().publish()

    # Create a page originally in French.
    fr_page = SimpleRichTextPageFactory(
        title="French Original",
        slug="french-page",
        locale=fr_locale,
        content="French content",
        parent=fr_home,
    )
    fr_page.save_revision().publish()

    # Create German and French translations for the en_page.
    de_translation = en_page.copy_for_translation(de_locale)
    de_translation.title = "German Translation"
    de_translation.save_revision().publish()
    # Make sure that the PageTranslationData object for the translation exists.
    PageTranslationData.objects.get_or_create(
        source_page=en_page,
        translated_page=de_translation,
    )

    fr_translation = en_page.copy_for_translation(fr_locale)
    fr_translation.title = "French Translation"
    fr_translation.save_revision().publish()
    # Make sure that the PageTranslationData object for the translation exists.
    PageTranslationData.objects.get_or_create(
        source_page=en_page,
        translated_page=fr_translation,
    )

    # Create Italian translations for the fr_page.
    it_translation = fr_page.copy_for_translation(it_locale)
    it_translation.title = "Italian Translation"
    it_translation.save_revision().publish()
    # Make sure that the PageTranslationData object for the translation exists.
    PageTranslationData.objects.get_or_create(
        source_page=fr_page,
        translated_page=it_translation,
    )
