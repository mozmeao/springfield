# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for matching rules on the server."""

from unittest.mock import patch

from django.test import RequestFactory, override_settings

import pytest

from springfield.cms.routing import server_match
from springfield.cms.routing.models import RoutingCondition, RoutingRule
from springfield.cms.routing.server_match import SERVER_SIGNALS, condition_matches, matched_target
from springfield.cms.tests.factories import WhatsNewPage2026Factory

rf = RequestFactory()


def country_condition(operator, expected_value):
    return RoutingCondition(signal="country", operator=operator, expected_value=expected_value)


# ---------------------------------------------------------------------------
# One condition against one value. Unknown (None) never matches, negated operators included.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("operator", "expected_value", "value", "matches"),
    (
        ("is", "CN", "CN", True),
        ("is", "CN", "US", False),
        ("is", "CN", None, False),
        ("is_not", "CN", "US", True),
        ("is_not", "CN", "CN", False),
        ("is_not", "CN", None, False),
        ("in", "CN, HK\nMO", "HK", True),
        ("in", "CN, HK\nMO", "MO", True),
        ("in", "CN, HK\nMO", "TW", False),
        ("in", "CN, HK\nMO", None, False),
        ("not_in", "CN", "US", True),
        ("not_in", "CN", "CN", False),
        ("not_in", "CN", None, False),
    ),
)
def test_condition_matches(operator, expected_value, value, matches):
    assert condition_matches(country_condition(operator, expected_value), value) is matches


def test_matching_is_exact_case_included():
    assert condition_matches(country_condition("is", "CN"), "cn") is False


def test_an_unknown_operator_never_matches():
    assert condition_matches(country_condition("gt", "CN"), "CN") is False


def test_only_country_is_a_server_signal():
    assert set(SERVER_SIGNALS) == {"country"}


@pytest.mark.django_db
@override_settings(DEV=False)
def test_a_country_header_the_cdn_could_not_resolve_is_unknown():
    request = rf.get("/", HTTP_CF_IPCOUNTRY="**")
    value = SERVER_SIGNALS["country"](request)
    assert value is None
    assert condition_matches(country_condition("is_not", "CN"), value) is False


# ---------------------------------------------------------------------------
# Rules on a page, in order. The page's trigger plays no part here.
# ---------------------------------------------------------------------------


def create_country_rule(page, target, operator, expected_value, sort_order):
    rule = RoutingRule.objects.create(page=page, target=target, sort_order=sort_order)
    RoutingCondition.objects.create(rule=rule, signal="country", operator=operator, expected_value=expected_value)
    return rule


def request_from(country):
    return rf.get("/", HTTP_CF_IPCOUNTRY=country)


@pytest.fixture
def country_rules(translated_wnp):
    """Two country rules after the fixture's platform rule, which the server cannot read."""
    wnp = translated_wnp
    second = WhatsNewPage2026Factory(parent=wnp.canonical, slug="145-c", version="145", live=True)
    create_country_rule(wnp.canonical, wnp.variant, "in", "CN, HK", sort_order=1)
    create_country_rule(wnp.canonical, second, "is", "CN", sort_order=2)
    wnp.second = second
    return wnp


def refetched(page):
    return type(page).objects.get(pk=page.pk)


def test_the_first_matching_rule_wins(country_rules):
    assert matched_target(refetched(country_rules.canonical), request_from("CN")).pk == country_rules.variant.pk


@override_settings(DEV=False)
def test_no_rule_matches(country_rules):
    assert matched_target(refetched(country_rules.canonical), request_from("US")) is None
    assert matched_target(refetched(country_rules.canonical), rf.get("/")) is None


def test_a_rule_with_a_browser_only_condition_is_skipped(translated_wnp):
    # The fixture's only rule checks platform, which the server cannot read.
    RoutingCondition.objects.create(rule=translated_wnp.rule, signal="country", operator="is", expected_value="CN", sort_order=1)
    assert matched_target(refetched(translated_wnp.canonical), request_from("CN")) is None


def test_a_match_all_rule_is_skipped(translated_wnp):
    RoutingRule.objects.create(page=translated_wnp.canonical, target=translated_wnp.variant, match_all=True)
    assert matched_target(refetched(translated_wnp.canonical), request_from("CN")) is None


def test_a_rule_with_an_unpublished_target_is_never_matched(country_rules):
    country_rules.variant.unpublish()
    assert matched_target(refetched(country_rules.canonical), request_from("CN")).pk == country_rules.second.pk


def test_a_rule_whose_target_has_no_version_in_this_language_is_never_matched(country_rules):
    # The second target exists only in English; the first resolves to its German version.
    create_country_rule(country_rules.de_canonical, country_rules.second, "is", "CN", sort_order=1)
    assert matched_target(refetched(country_rules.de_canonical), request_from("CN")) is None
    create_country_rule(country_rules.de_canonical, country_rules.variant, "is", "CN", sort_order=2)
    assert matched_target(refetched(country_rules.de_canonical), request_from("CN")).pk == country_rules.de_variant.pk


def test_each_signal_is_read_once_per_request(country_rules):
    reads = []

    def reader(request):
        reads.append(request)
        return "US"

    with patch.dict(server_match.SERVER_SIGNALS, {"country": reader}):
        assert matched_target(refetched(country_rules.canonical), request_from("US")) is None
    assert len(reads) == 1
