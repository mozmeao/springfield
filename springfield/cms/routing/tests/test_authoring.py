# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin authoring round-trip for the User Routing tab.

Every other routing test builds rules through the ORM; this one drives the real
Wagtail page edit form — the nested ``routing_rules`` → ``conditions`` InlinePanel
formsets — so the authoring path (formset wiring + save-time ``clean()``) is exercised
end to end. Uses the ``admin_client`` fixture (routing ``conftest.py``): a naive
``force_login`` 302s to Auth0 on CI, so the fixture's ``override_settings`` is required.
"""

from django.urls import reverse

import pytest
from wagtail.models import Site
from wagtail.test.utils.form_data import (
    inline_formset,
    nested_form_data,
    rich_text,
    streamfield,
)

from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule
from springfield.cms.tests.factories import WhatsNewIndexPageFactory, WhatsNewPage2026Factory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def wnp():
    """A canonical WhatsNewPage2026 (direct child of the index) with a valid target."""
    site_root = Site.objects.get(is_default_site=True).root_page
    index = WhatsNewIndexPageFactory(parent=site_root, slug="c21-whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, slug="c21-200", version="200", live=True)
    target = WhatsNewPage2026Factory(parent=canonical, slug="c21-200-b", version="200", live=True)
    return canonical, target


def _edit_post_data(canonical, rules_formset):
    """A complete, publishable WNP edit POST with the given routing_rules formset."""
    # RoutingPageForm auto-creates the kill-switch record for canonical pages, so a real
    # edit POST carries it back as an existing form (INITIAL_FORMS=1). Mirror that here.
    config, _ = RoutingConfig.objects.get_or_create(page=canonical)
    return nested_form_data(
        {
            "title": canonical.title,
            "slug": canonical.slug,
            "internal_title": "",
            "version": canonical.version,
            # Required by PreFooterImageMixin; the form has no implicit default on POST.
            "pre_footer_image": "kit",
            "upper_content": streamfield([]),
            "content": streamfield([("rich_text", rich_text("<p>Hello</p>"))]),
            "routing_rules": rules_formset,
            "routing_config": inline_formset([{"id": config.pk, "routing_paused": ""}], initial=1),
            # Publish so the edited cluster is written to the live child tables (a
            # draft save would only stash it in a revision).
            "action-publish": "action-publish",
        }
    )


def _edit_url(page):
    return reverse("wagtailadmin_pages:edit", args=[page.id])


def test_authoring_a_rule_with_a_condition_round_trips(admin_client, wnp):
    canonical, target = wnp
    rules = inline_formset(
        [
            {
                "name": "Windows users",
                "match_all": "",
                "target": target.pk,
                "conditions": inline_formset([{"signal": "platform", "operator": "is", "expected_value": "windows"}]),
            }
        ]
    )

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    assert response.status_code == 302  # a successful save redirects

    rule = RoutingRule.objects.get(page=canonical)
    assert rule.name == "Windows users"
    assert rule.target_id == target.pk
    condition = RoutingCondition.objects.get(rule=rule)
    assert (condition.signal, condition.operator, condition.expected_value) == ("platform", "is", "windows")


def test_authoring_a_match_all_rule_round_trips(admin_client, wnp):
    canonical, target = wnp
    rules = inline_formset([{"name": "Everyone", "match_all": "on", "target": target.pk, "conditions": inline_formset([])}])

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    assert response.status_code == 302

    rule = RoutingRule.objects.get(page=canonical)
    assert rule.match_all is True
    assert rule.conditions.count() == 0


def test_authoring_an_empty_non_match_all_rule_is_rejected(admin_client, wnp):
    # The condition floor must fire through the real formset, not just the ORM: a
    # rule with no conditions and match_all off is invalid and nothing is persisted.
    canonical, target = wnp
    rules = inline_formset([{"name": "Oops", "match_all": "", "target": target.pk, "conditions": inline_formset([])}])

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    # A failed floor check re-renders the form (200) with the specific error, and no
    # rule is written. (Asserting the message guards against a false pass from some
    # unrelated form error.)
    assert response.status_code == 200
    assert "Add at least one condition" in response.content.decode("utf-8")
    assert not RoutingRule.objects.filter(page=canonical).exists()


# ---------------------------------------------------------------------------
# Kill switch + non-canonical saves.
# ---------------------------------------------------------------------------


def test_kill_switch_checkbox_always_renders_on_canonical(admin_client, wnp):
    # The pause checkbox is always present (no "Add" step), nested under the Options group.
    canonical, _target = wnp
    html = admin_client.get(_edit_url(canonical)).content.decode("utf-8")
    assert 'name="routing_config-0-routing_paused"' in html
    assert "Options" in html  # the options group heading
    assert "Kill switch" in html


def _content_only_post_data(page):
    """An edit POST with no routing formsets — as a non-canonical page's hidden tab sends."""
    return nested_form_data(
        {
            "title": page.title,
            "slug": page.slug,
            "internal_title": "",
            "version": page.version,
            "pre_footer_image": "kit",
            "upper_content": streamfield([]),
            "content": streamfield([("rich_text", rich_text("<p>Hello</p>"))]),
            "action-publish": "action-publish",
        }
    )


def test_non_canonical_page_saves_without_routing_formsets(admin_client, wnp):
    # The target is a nested variant → non-canonical, so its routing tab (and the
    # min_num=1 kill switch) is hidden and omitted from the POST. The page must still
    # save; the routing formsets are excluded from validation, not forced.
    _canonical, variant = wnp
    assert variant.is_routing_canonical() is False

    response = admin_client.post(_edit_url(variant), _content_only_post_data(variant))
    assert response.status_code == 302
    # min_num=1 did not force a RoutingConfig onto the non-canonical page.
    assert not RoutingConfig.objects.filter(page=variant).exists()


# ---------------------------------------------------------------------------
# Target guards enforced admin-side.
# ---------------------------------------------------------------------------


def test_self_target_rule_is_rejected_in_admin(admin_client, wnp):
    canonical, _target = wnp
    rules = inline_formset([{"name": "Self", "match_all": "on", "target": canonical.pk, "conditions": inline_formset([])}])

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    assert response.status_code == 200
    assert "cannot target its own page" in response.content.decode("utf-8")
    assert not RoutingRule.objects.filter(page=canonical).exists()


# ---------------------------------------------------------------------------
# The arming param is not offerable as a condition signal.
# ---------------------------------------------------------------------------


def _offered_signals(form):
    """The signal names a condition form's dropdown actually offers."""
    names = []
    for value, label in form.fields["signal"].widget.choices:
        if isinstance(label, (list, tuple)):
            names.extend(option[0] for option in label)
        else:
            names.append(value)
    return names


def _condition_forms(page_form):
    """Every condition form on the page form, including the add-a-row templates."""
    rules = page_form.formsets["routing_rules"]
    for rule_form in [*rules.forms, rules.empty_form]:
        conditions = rule_form.formsets["conditions"]
        yield from [*conditions.forms, conditions.empty_form]


def test_arming_param_is_not_offered_as_a_condition_signal(admin_client, wnp):
    # WNP arms on ?utm_source=update, so the resolver only ever runs with utm_source
    # already at that value — a condition testing it could never do anything useful.
    # empty_form is covered too: it's the template Wagtail clones for "Add condition".
    canonical, _target = wnp
    page_form = admin_client.get(_edit_url(canonical)).context["form"]

    forms = list(_condition_forms(page_form))
    assert forms, "expected at least the add-a-row template"
    for form in forms:
        offered = _offered_signals(form)
        assert "utm_source" not in offered, "the arming param must not be offerable"
        # Only the arming param is withheld — everything else stays available.
        assert {"country", "utm_medium", "utm_campaign", "firefox_version"} <= set(offered)


def test_posting_the_arming_param_as_a_signal_is_rejected(admin_client, wnp):
    # The narrowed dropdown is presentation only, so the save path has to reject it too:
    # a hand-crafted POST is refused with an explanatory error and nothing is written.
    canonical, target = wnp
    rules = inline_formset(
        [
            {
                "name": "Always true",
                "match_all": "",
                "target": target.pk,
                "conditions": inline_formset([{"signal": "utm_source", "operator": "is", "expected_value": "update"}]),
            }
        ]
    )

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    assert response.status_code == 200
    assert "always matches" in response.content.decode("utf-8")
    assert not RoutingRule.objects.filter(page=canonical).exists()


def test_other_url_signals_are_still_authorable(admin_client, wnp):
    # Only the arming param is withheld. Geo and the other utm signals stay usable —
    # guards against the exclusion widening to the whole URL source.
    canonical, target = wnp
    rules = inline_formset(
        [
            {
                "name": "Germany",
                "match_all": "",
                "target": target.pk,
                "conditions": inline_formset([{"signal": "country", "operator": "is", "expected_value": "DE"}]),
            }
        ]
    )

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    assert response.status_code == 302
    assert RoutingCondition.objects.get(rule__page=canonical).signal == "country"


def test_non_descendant_target_is_rejected_in_admin(admin_client, wnp):
    canonical, _target = wnp
    # A sibling canonical (direct child of the index) is a valid WhatsNewPage2026 but
    # NOT a descendant of `canonical`, so the chooser type-scope wouldn't catch it.
    index = canonical.get_parent()
    sibling = WhatsNewPage2026Factory(parent=index, slug="c21-201", version="201", live=True)
    rules = inline_formset([{"name": "Sibling", "match_all": "on", "target": sibling.pk, "conditions": inline_formset([])}])

    response = admin_client.post(_edit_url(canonical), _edit_post_data(canonical, rules))
    assert response.status_code == 200
    assert "must be a descendant" in response.content.decode("utf-8")
    assert not RoutingRule.objects.filter(page=canonical).exists()
