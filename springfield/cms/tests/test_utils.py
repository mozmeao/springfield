# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.test import override_settings

import pytest
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Page, Site

from springfield.cms.tests.factories import LocaleFactory
from springfield.cms.utils import (
    find_fallback_page_for_locale,
    get_cms_locales_for_path,
    get_locales_for_cms_page,
    get_page_for_request,
)

pytestmark = [pytest.mark.django_db]


def _publish_root_page(site, locale_code):
    """Publish the root page for the given locale (tiny_localized_site creates them as drafts)."""
    root = site.root_page.get_translation(Locale.objects.get(language_code=locale_code))
    root.live = True
    root.save()
    return root


@override_settings(FALLBACK_LOCALES={})
def test_get_locales_for_cms_page(tiny_localized_site):
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # By default there are no aliases in the system, so all _locales_available_for_cms will
    # match the pages set up in the tiny_localized_site fixture
    assert Page.objects.filter(alias_of__isnull=False).count() == 0

    assert sorted(get_locales_for_cms_page(en_us_test_page)) == ["en-US", "fr", "pt-BR"]

    # now make aliases of the test_page into Dutch and Spanish
    nl_locale = Locale.objects.create(language_code="nl")
    es_es_locale = Locale.objects.create(language_code="es-ES")

    nl_page_alias = en_us_test_page.copy_for_translation(locale=nl_locale, copy_parents=True, alias=True)
    nl_page_alias.save()

    es_es_page_alias = en_us_test_page.copy_for_translation(locale=es_es_locale, copy_parents=True, alias=True)
    es_es_page_alias.save()

    assert Page.objects.filter(alias_of__isnull=False).count() == 4  # 2 child + 2 parent pages, which had to be copied too

    # Show that the aliases don't appear in the available locales
    assert sorted(get_locales_for_cms_page(en_us_test_page)) == ["en-US", "fr", "pt-BR"]


@override_settings(FALLBACK_LOCALES={})
def test_get_locales_for_cms_page__ensure_draft_pages_are_excluded(tiny_localized_site):
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]
    fr_homepage = Page.objects.get(locale__language_code="fr", slug="home-fr")
    fr_test_page = fr_homepage.get_children()[0]

    fr_test_page.unpublish()

    assert sorted(get_locales_for_cms_page(en_us_test_page)) == ["en-US", "pt-BR"]


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_get_locales_for_cms_page__no_alias_added_when_no_target_matches(tiny_localized_site):
    """Test when no FALLBACK_LOCALES entries match a locale in the page's translation set."""
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # en_us_test_page has translations in fr and pt-BR; none of those are targets in FALLBACK_LOCALES,
    # so the results are ["en-US", "fr", "pt-BR"].
    assert sorted(get_locales_for_cms_page(en_us_test_page)) == sorted(["en-US", "fr", "pt-BR"])


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_locales_for_cms_page__alias_added_when_target_is_a_translation(tiny_localized_site):
    """
    When a page's translation has an fallback locale in FALLBACK_LOCALES, the fallback is returned.
    """
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # en_us_test_page has translations in fr and pt-BR.
    translation_locales = ["en-US", "fr", "pt-BR"]
    assert sorted(Page.objects.filter(translation_key=en_us_test_page.translation_key).values_list("locale__language_code", flat=True)) == sorted(
        translation_locales
    )
    # Since pt-BR is a fallback locale for pt-PT, we expect that pt-PT is included
    # in the results of get_locales_for_cms_page().
    expected_result = translation_locales + ["pt-PT"]
    result = get_locales_for_cms_page(en_us_test_page)
    assert "pt-PT" in result
    assert sorted(result) == sorted(expected_result)


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_locales_for_cms_page__alias_added_even_when_locale_record_absent(tiny_localized_site):
    """Alias locale codes are returned even if no Locale DB record exists for them.
    The function works with locale code strings and does not require a Locale row."""
    assert not Locale.objects.filter(language_code="pt-PT").exists()

    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    result = get_locales_for_cms_page(en_us_test_page)
    assert "pt-PT" in result


@override_settings(FALLBACK_LOCALES={"en-GB": "en-US", "en-CA": "en-US"})
def test_get_locales_for_cms_page__alias_added_when_target_is_page_own_locale(tiny_localized_site):
    """An alias locale whose target is the page's own locale is also appended."""
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # en_us_test_page has translations in fr and pt-BR.
    translation_locales = ["en-US", "fr", "pt-BR"]
    assert sorted(Page.objects.filter(translation_key=en_us_test_page.translation_key).values_list("locale__language_code", flat=True)) == sorted(
        translation_locales
    )
    # Since "en-US" is a fallback locale for "en-GB" and "en-CA", we expect that
    # "en-GB" and "en-CA" are included in the results of get_locales_for_cms_page().
    expected_result = translation_locales + ["en-GB", "en-CA"]
    result = get_locales_for_cms_page(en_us_test_page)
    assert "en-GB" in result
    assert "en-CA" in result
    assert sorted(result) == sorted(expected_result)


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX", "es-CL": "es-MX"})
def test_get_locales_for_cms_page__multiple_aliases_for_same_target_all_added(tiny_localized_site):
    """All alias locales targeting the same locale are each included in the result."""
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # Create an es-MX translation of the test page so es-MX is in the list
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_mx_test_page = en_us_test_page.copy_for_translation(es_mx_locale, copy_parents=True)
    es_mx_test_page.save_revision().publish()

    # en_us_test_page has translations in fr, pt-BR, and es-MX.
    translation_locales = ["en-US", "fr", "pt-BR", "es-MX"]
    assert sorted(Page.objects.filter(translation_key=en_us_test_page.translation_key).values_list("locale__language_code", flat=True)) == sorted(
        translation_locales
    )
    # Since "es-MX" is a fallback locale for "es-AR" and "es-CL", we expect that
    # "es-AR" and "es-CL" are included in the results of get_locales_for_cms_page().
    expected_result = translation_locales + ["es-AR", "es-CL"]
    result = get_locales_for_cms_page(en_us_test_page)
    assert "es-AR" in result
    assert "es-CL" in result
    assert sorted(result) == sorted(expected_result)


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_locales_for_cms_page__canonical_locales_listed_before_alias_additions(tiny_localized_site):
    """Alias locales are appended after canonical/translated locales, not interleaved."""
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    result = get_locales_for_cms_page(en_us_test_page)
    pt_br_index = result.index("pt-BR")
    pt_pt_index = result.index("pt-PT")
    assert pt_br_index < pt_pt_index


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_get_locales_for_cms_page__no_duplicate_when_alias_locale_is_also_an_actual_translation(tiny_localized_site):
    """When an alias locale has a real translation, it must not appear twice in the result."""
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # Create actual (non-alias) translations in both es-MX and es-AR
    es_mx_test_page = en_us_test_page.copy_for_translation(es_mx_locale, copy_parents=True)
    es_mx_test_page.save_revision().publish()

    es_ar_test_page = en_us_test_page.copy_for_translation(es_ar_locale, copy_parents=True)
    es_ar_test_page.save_revision().publish()

    # From es-MX page's perspective: es-AR is both an actual translation AND listed
    # in FALLBACK_LOCALES as an alias. It should appear exactly once.
    es_mx_test_page.refresh_from_db()
    result = get_locales_for_cms_page(es_mx_test_page)
    assert result.count("es-AR") == 1
    assert result.count("es-MX") == 1


@override_settings(FALLBACK_LOCALES={})
def test_get_locales_for_cms_page__empty_fallback_locales_adds_nothing(tiny_localized_site):
    """An empty FALLBACK_LOCALES dict adds no alias locales."""
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # en_us_test_page has translations in fr and pt-BR.
    translation_locales = ["en-US", "fr", "pt-BR"]
    assert sorted(Page.objects.filter(translation_key=en_us_test_page.translation_key).values_list("locale__language_code", flat=True)) == sorted(
        translation_locales
    )
    # get_locales_for_cms_page() results match the translations' locale codes.
    assert sorted(get_locales_for_cms_page(en_us_test_page)) == sorted(translation_locales)


def test_get_locales_for_cms_page__absent_fallback_locales_setting_adds_nothing(tiny_localized_site, settings):
    """When FALLBACK_LOCALES is not present in settings at all, the function
    handles it gracefully via getattr and adds no aliases."""
    del settings.FALLBACK_LOCALES

    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # en_us_test_page has translations in fr and pt-BR.
    translation_locales = ["en-US", "fr", "pt-BR"]
    assert sorted(Page.objects.filter(translation_key=en_us_test_page.translation_key).values_list("locale__language_code", flat=True)) == sorted(
        translation_locales
    )
    # get_locales_for_cms_page() results match the translations' locale codes.
    assert sorted(get_locales_for_cms_page(en_us_test_page)) == sorted(translation_locales)


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__returns_page_when_found(tiny_localized_site):
    """Returns the live page from the fallback locale's tree."""
    # The pt-BR page for this URL exists; this is the expected result.
    expected_result = Page.objects.get(locale__language_code="pt-BR", slug="test-page")

    result = find_fallback_page_for_locale("pt-PT", "test-page/")
    assert expected_result == result
    assert result.locale.language_code == "pt-BR"


@pytest.mark.parametrize(
    "falsy_url_path",
    [
        (""),
        ("/"),
    ],
)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__returns_homepage_for_falsy_url_path(tiny_localized_site, falsy_url_path):
    """
    Returns fallback locale homepage when no alias homepage & url_path is falsy (homepage request).

    When a user requests /pt-PT/ (the pt-PT homepage), and the pt-PT locale does
    not have a live homepage, we should return the pt-BR homepage.
    """
    # The pt-PT locale does not have a live homepage.
    assert not Locale.objects.filter(language_code="pt-PT").exists()

    site = Site.objects.get(is_default_site=True)
    pt_br_root = _publish_root_page(site, "pt-BR")

    result = find_fallback_page_for_locale("pt-PT", falsy_url_path)
    assert result is not None, "find_fallback_page_for_locale returned None for empty url_path (homepage)"
    assert result == pt_br_root
    assert result.locale.language_code == "pt-BR"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__returns_fallback_homepage_when_alias_has_no_live_homepage(tiny_localized_site):
    """
    When the alias locale (pt-PT) exists but has no live homepage,
    the function returns the fallback locale's (pt-BR) homepage.
    """
    # Create pt-PT locale with a non-live root page (mimics migration 0053).
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    site = Site.objects.get(is_default_site=True)
    pt_pt_root = site.root_page.copy_for_translation(pt_pt_locale)
    pt_pt_root.live = False
    pt_pt_root.save()

    # pt-PT has no live homepage.
    assert not Page.objects.live().filter(locale=pt_pt_locale, depth=site.root_page.depth).exists()

    pt_br_root = _publish_root_page(site, "pt-BR")

    result = find_fallback_page_for_locale("pt-PT", "")
    assert result is not None, "find_fallback_page_for_locale returned None when alias has no live homepage"
    assert result == pt_br_root
    assert result.locale.language_code == "pt-BR"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__returns_fallback_homepage_when_alias_has_live_homepage(tiny_localized_site):
    """
    When the alias locale (pt-PT) has its own live homepage, the function
    still returns the fallback locale's (pt-BR) homepage.

    find_fallback_page_for_locale always looks up the fallback locale's page tree.
    Whether to use the alias locale's own page or the fallback is decided by the
    caller (the middleware), not by this function.
    """
    # Create pt-PT locale with a live root page (promoted alias).
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    site = Site.objects.get(is_default_site=True)
    pt_pt_root = site.root_page.copy_for_translation(pt_pt_locale)
    pt_pt_root.live = True
    pt_pt_root.save()
    pt_pt_root.save_revision().publish()

    # pt-PT has a live homepage.
    assert Page.objects.live().filter(locale=pt_pt_locale, depth=site.root_page.depth).exists()

    pt_br_root = _publish_root_page(site, "pt-BR")

    result = find_fallback_page_for_locale("pt-PT", "")
    assert result is not None, "find_fallback_page_for_locale returned None when alias has live homepage"
    # The function always returns the fallback locale's page, regardless of
    # whether the alias locale has its own content.
    assert result == pt_br_root
    assert result.locale.language_code == "pt-BR"


@pytest.mark.parametrize(
    "url_path",
    [
        ("/test-page"),  # left slash
        ("test-page/"),  # right slash
        ("/test-page/"),  # left and right slash
        ("test-page"),  # no slash
    ],
)
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__url_path_normalized(tiny_localized_site, url_path):
    """Leading/trailing slashes in url_path are stripped before the lookup."""
    expected_result = Page.objects.get(locale__language_code="pt-BR", slug="test-page")
    assert find_fallback_page_for_locale("pt-PT", url_path) == expected_result


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__returns_none_when_page_not_found(tiny_localized_site):
    """Returns None when no live page exists at the constructed URL path."""
    assert find_fallback_page_for_locale("pt-PT", "does-not-exist/") is None


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_find_fallback_page_for_locale__returns_none_when_locale_not_in_fallback_locales(tiny_localized_site):
    """Returns None for a locale_code not listed in FALLBACK_LOCALES."""
    # es-AR is not in FALLBACK_LOCALES, so the function returns None
    assert find_fallback_page_for_locale("es-AR", "test-page/") is None


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_find_fallback_page_for_locale__returns_none_when_fallback_locale_has_no_db_record(tiny_localized_site):
    """Returns None when the fallback locale has no Locale DB record."""
    assert not Locale.objects.filter(language_code="es-MX").exists()
    assert find_fallback_page_for_locale("es-AR", "test-page/") is None


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_find_fallback_page_for_locale__returns_none_when_fallback_locale_has_no_page_tree(tiny_localized_site):
    """Returns None when the fallback Locale record exists but has no page tree."""
    LocaleFactory(language_code="es-MX")
    assert find_fallback_page_for_locale("es-AR", "test-page/") is None


@override_settings(FALLBACK_LOCALES={})
def test_find_fallback_page_for_locale__returns_none_with_empty_fallback_locales(tiny_localized_site):
    """Returns None when FALLBACK_LOCALES is empty."""
    assert find_fallback_page_for_locale("pt-PT", "test-page/") is None


def test_find_fallback_page_for_locale__returns_none_when_fallback_locales_absent(tiny_localized_site, settings):
    """Returns None when FALLBACK_LOCALES is absent from settings."""
    del settings.FALLBACK_LOCALES
    assert find_fallback_page_for_locale("pt-PT", "test-page/") is None


@pytest.mark.parametrize(
    "path, expected_page_url",
    [
        (
            "/en-US/test-page/",
            "/en-US/test-page/",
        ),
        (
            "/test-page/",
            "/en-US/test-page/",
        ),
        (
            "/pt-BR/test-page/",
            "/pt-BR/test-page/",
        ),
        (
            "/pt-BR/test-page/child-page/",
            "/pt-BR/test-page/child-page/",
        ),
        (
            "/fr/test-page/",
            "/fr/test-page/",
        ),
        (
            "/fr/test-page/child-page/",
            "/fr/test-page/child-page/",
        ),
        # These two routes do not work, even though a manual test with similar ones
        # does not show up as a problem. I think it's possibly related to the
        # tiny_localized_site fixture generated in cms/tests/conftest.py
        # (
        #     "/fr/test-page/child-page/grandchild-page/",
        #     "/fr/test-page/child-page/grandchild-page/",
        # ),
        # (
        #     "/test-page/child-page/grandchild-page/",
        #     "/fr/test-page/child-page/grandchild-page/",
        # ),
    ],
)
def test_get_page_for_request__happy_path(path, expected_page_url, tiny_localized_site):
    request = get_dummy_request(path=path)
    page = get_page_for_request(request=request)
    assert isinstance(page, Page)
    assert page.url == expected_page_url


@pytest.mark.parametrize(
    "path",
    [
        "/en-US/test-page/fake/path/",
        "/fr/test-page/fake/path/",
        "/not/a/real/test-page",
    ],
)
def test_get_page_for_request__no_match(path, tiny_localized_site):
    request = get_dummy_request(path=path)
    page = get_page_for_request(request=request)
    assert page is None


@pytest.mark.parametrize(
    "get_page_for_request_should_return_a_page, get_locales_for_cms_page_retval, expected",
    (
        (True, ["en-CA", "sco", "zh-CN"], ["en-CA", "sco", "zh-CN"]),
        (False, None, []),
    ),
)
def test_get_cms_locales_for_path(
    rf,
    get_page_for_request_should_return_a_page,
    get_locales_for_cms_page_retval,
    expected,
    minimal_site,
    mocker,
):
    request = rf.get("/path/is/irrelevant/due/to/mocks")
    mock_get_page_for_request = mocker.patch("springfield.cms.utils.get_page_for_request")
    mock_get_locales_for_cms_page = mocker.patch("springfield.cms.utils.get_locales_for_cms_page")

    if get_page_for_request_should_return_a_page:
        page = mocker.Mock("fake-page")
        mock_get_page_for_request.return_value = page
        mock_get_locales_for_cms_page.return_value = get_locales_for_cms_page_retval
    else:
        mock_get_page_for_request.return_value = None

    request = rf.get("/irrelevant/because/we/are/mocking")
    assert get_cms_locales_for_path(request) == expected

    if get_page_for_request_should_return_a_page:
        mock_get_page_for_request.assert_called_once_with(request=request)
        mock_get_locales_for_cms_page.assert_called_once_with(page=page)
