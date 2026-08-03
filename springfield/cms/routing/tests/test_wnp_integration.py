# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""End-to-end serve integration for the first consumer, WhatsNewPage2026.

This is the first place real request-level ``serve()`` dispatch is exercised:
organic traffic must be byte-identical to today, the resolver must fire
only on a triggered live canonical with rules, and the loop-breaker / kill switch /
global switch must each behave correctly.
"""

from types import SimpleNamespace

import pytest
from waffle.testutils import override_switch
from wagtail.models import Site

from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule
from springfield.cms.tests.factories import WhatsNewIndexPageFactory, WhatsNewPage2026Factory

pytestmark = [pytest.mark.django_db]

# A marker only the client resolver page carries.
RESOLVER_MARKER = "data-routing-rules"


@pytest.fixture
def wnp():
    site = Site.objects.get(is_default_site=True)
    index = WhatsNewIndexPageFactory(parent=site.root_page, slug="whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, slug="145", version="145", live=True)
    variant = WhatsNewPage2026Factory(parent=canonical, slug="145-b", version="145", live=True)
    rule = RoutingRule.objects.create(page=canonical, target=variant)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)
    return SimpleNamespace(site=site, index=index, canonical=canonical, variant=variant, rule=rule)


# ---------------------------------------------------------------------------
# Adoption surface and the descendant target.
# ---------------------------------------------------------------------------


def test_wnp_declares_only_the_two_adoption_hooks(wnp):
    from springfield.cms.routing.arming import QueryParamValueArmingCondition

    trigger = wnp.canonical.get_routing_trigger()
    assert isinstance(trigger, QueryParamValueArmingCondition)
    # Armed on Firefox's just-updated flow specifically.
    assert trigger.param_name == "utm_source"
    assert trigger.values == frozenset({"update"})


def test_is_routing_canonical_only_for_direct_children_of_the_index(wnp):
    # Direct child of the index is canonical; a nested variant is not.
    assert wnp.canonical.is_routing_canonical() is True
    assert wnp.variant.is_routing_canonical() is False


def test_a_child_wnp_is_a_valid_descendant_target(wnp):
    # The descendant constraint passes for a nested WhatsNewPage2026 target.
    # match_all satisfies the condition floor so this isolates the target check.
    rule = RoutingRule(page=wnp.canonical, target=wnp.variant, match_all=True)
    rule.full_clean()  # does not raise


def test_wnp_target_chooser_is_scoped_to_whatsnew_pages():
    # The rule's target chooser only offers WhatsNewPage2026 pages.
    from wagtail.admin.panels import InlinePanel
    from wagtail.admin.widgets import AdminPageChooser

    from springfield.cms.models import WhatsNewPage2026

    tab = WhatsNewPage2026.get_routing_tab()
    rules_panel = next(p for p in tab.children if isinstance(p, InlinePanel) and p.relation_name == "routing_rules")
    target_panel = next(p for p in rules_panel.panels if getattr(p, "field_name", "") == "target")
    assert isinstance(target_panel.widget, AdminPageChooser)
    assert WhatsNewPage2026 in target_panel.widget.target_models


# ---------------------------------------------------------------------------
# Serve-path dispatch, end to end.
# ---------------------------------------------------------------------------


def test_organic_untriggered_traffic_is_byte_identical_to_today(client, wnp):
    url = wnp.canonical.get_url()
    # Framework dark (switch off) is "today".
    baseline = client.get(url)
    with override_switch("user_routing", active=True):
        untriggered = client.get(url)
    assert untriggered.status_code == baseline.status_code == 200
    assert untriggered.content == baseline.content
    assert RESOLVER_MARKER not in baseline.content.decode("utf-8")


@override_switch("user_routing", active=True)
def test_triggered_live_canonical_with_rules_serves_the_resolver(client, wnp):
    response = client.get(wnp.canonical.get_url() + "?utm_source=update")
    assert response.status_code == 200
    assert RESOLVER_MARKER in response.content.decode("utf-8")


@override_switch("user_routing", active=True)
def test_untriggered_utm_source_value_serves_canonical(client, wnp):
    # A non-"update" utm_source does not arm routing.
    response = client.get(wnp.canonical.get_url() + "?utm_source=newsletter")
    assert response.status_code == 200
    assert RESOLVER_MARKER not in response.content.decode("utf-8")


@override_switch("user_routing", active=True)
def test_loop_breaker_serves_canonical_even_when_triggered(client, wnp):
    response = client.get(wnp.canonical.get_url() + "?utm_source=update&routed=1")
    assert response.status_code == 200
    assert RESOLVER_MARKER not in response.content.decode("utf-8")


@override_switch("user_routing", active=True)
def test_kill_switch_serves_canonical(client, wnp):
    RoutingConfig.objects.create(page=wnp.canonical, routing_paused=True)
    response = client.get(wnp.canonical.get_url() + "?utm_source=update")
    assert response.status_code == 200
    assert RESOLVER_MARKER not in response.content.decode("utf-8")


def test_global_switch_off_never_serves_the_resolver(client, wnp):
    # Switch off + triggered + rules present -> still canonical (ships dark).
    response = client.get(wnp.canonical.get_url() + "?utm_source=update")
    assert response.status_code == 200
    assert RESOLVER_MARKER not in response.content.decode("utf-8")


@override_switch("user_routing", active=True)
def test_triggered_canonical_without_rules_serves_canonical(client, wnp):
    # A sibling canonical with no rules must not serve the resolver.
    bare = WhatsNewPage2026Factory(parent=wnp.index, slug="144", version="144", live=True)
    response = client.get(bare.get_url() + "?utm_source=update")
    assert response.status_code == 200
    assert RESOLVER_MARKER not in response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# Serving the resolver outside en-US.
#
# The resolver renders through l10n_utils.render, which redirects a visitor whose
# locale has no translation of the strings being rendered — unless the request carries
# the CMS page's own locale list. A German visitor must reach the resolver on the German
# canonical, not be bounced to /en-US/, and the `resolver_strings_english_only` fixture
# is what makes that observable (see its docstring).
# ---------------------------------------------------------------------------


@override_switch("user_routing", active=True)
def test_triggered_visitor_is_not_redirected_out_of_their_locale(client, translated_wnp, resolver_strings_english_only):
    response = client.get(translated_wnp.de_canonical.get_url() + "?utm_source=update")
    assert response.status_code == 200
    assert RESOLVER_MARKER in response.content.decode("utf-8")


@override_switch("user_routing", active=True)
def test_preview_signal_is_not_redirected_out_of_their_locale(admin_client, translated_wnp, resolver_strings_english_only):
    response = admin_client.get(translated_wnp.de_canonical.get_url() + "?preview_signal=platform:windows")
    assert response.status_code == 200
    assert RESOLVER_MARKER in response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# The index's latest-version redirect is unaffected by nested variants.
# ---------------------------------------------------------------------------


def test_index_latest_version_redirect_ignores_nested_variants(client, wnp):
    # A newer direct child; the nested variant under `canonical` is a grandchild and
    # must not be considered by the index's latest-version query.
    WhatsNewPage2026Factory(parent=wnp.index, slug="146", version="146", live=True)
    response = client.get(wnp.index.get_url())
    assert response.status_code == 302
    assert response["Location"].endswith("/146/")
