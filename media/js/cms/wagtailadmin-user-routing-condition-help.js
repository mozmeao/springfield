/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * User Routing — inline condition editor helper.
 *
 * Enhances the Wagtail admin's condition rows so that when an author
 * selects a Signal name, the Expected values field's help text updates to
 * show the valid values for that specific signal (e.g. selecting
 * ``country`` reveals the ISO code allowlist; selecting ``ai_controls``
 * reveals ``enabled / available / blocked``).
 *
 * Without this, the valid-values list is only surfaced by validation errors
 * after save — a poor authoring experience.
 *
 * Reads the signal metadata from the JSON blob emitted by
 * ``wagtail_hooks.user_routing_condition_help_js`` — a
 * ``<script type="application/json" id="springfield-routing-signals">``
 * block. Emitting as a JSON block (rather than a raw
 * ``window.SPRINGFIELD_ROUTING_SIGNALS = ...`` assignment) means
 * admin-editable content in the payload can't escape the tag.
 */

(function () {
    'use strict';

    var signalsNode = document.getElementById('springfield-routing-signals');
    if (!signalsNode) return;
    var SIGNALS;
    try {
        SIGNALS = JSON.parse(signalsNode.textContent);
    } catch (e) {
        return;
    }
    if (!SIGNALS) return;

    // Selector for the inline condition rows Wagtail renders. Each row has
    // two fields we care about: signal_name (a <select>) and
    // expected_values (a <textarea>). Their IDs share a common inline
    // prefix like ``id_conditions-0-...`` which we use to correlate.
    function findSignalSelects() {
        return document.querySelectorAll(
            'select[id$="-signal_name"], select[name$="-signal_name"]'
        );
    }

    function hintTextFor(signalName) {
        var meta = SIGNALS[signalName];
        if (!meta) return '';
        if (meta.enum_values && meta.enum_values.length) {
            return (
                'Valid values: ' +
                meta.enum_values
                    .map(function (v) {
                        return "'" + v + "'";
                    })
                    .join(', ')
            );
        }
        if (meta.value_type === 'bool') {
            return "Valid values: 'true' or 'false'.";
        }
        if (meta.value_type === 'int') {
            return 'Valid values: any integer.';
        }
        return '';
    }

    function findConditionRow(signalSelect) {
        // Walk up to the nearest ancestor that also contains the
        // expected_values textarea for the same inline row. Wagtail wraps
        // each inline row in a container, but the class names change
        // between versions — use the shared id-prefix trick.
        var id = signalSelect.id || '';
        var prefix = id.replace(/-signal_name$/, '');
        if (!prefix) {
            var name = signalSelect.name || '';
            prefix = name.replace(/-signal_name$/, '');
        }
        if (!prefix) return null;
        var textarea =
            document.getElementById(prefix + '-expected_values') ||
            document.querySelector(
                'textarea[name="' + prefix + '-expected_values"]'
            );
        return textarea ? textarea : null;
    }

    var HINT_CLASS = 'springfield-routing-value-hint';

    function updateHint(signalSelect) {
        var textarea = findConditionRow(signalSelect);
        if (!textarea) return;
        var host =
            textarea.closest('.field-content') ||
            textarea.closest('.field') ||
            textarea.parentNode;
        if (!host) return;

        var existing = host.querySelector('.' + HINT_CLASS);
        var hint = hintTextFor(signalSelect.value);

        if (!hint) {
            if (existing) existing.remove();
            return;
        }

        if (!existing) {
            existing = document.createElement('p');
            existing.className = HINT_CLASS + ' help';
            existing.style.marginBlockStart = '0.35rem';
            existing.style.fontStyle = 'italic';
            host.appendChild(existing);
        }
        existing.textContent = hint;
    }

    function wire(signalSelect) {
        if (signalSelect.dataset.springfieldRoutingBound) return;
        signalSelect.dataset.springfieldRoutingBound = '1';
        signalSelect.addEventListener('change', function () {
            updateHint(signalSelect);
        });
        updateHint(signalSelect);
    }

    function wireAll() {
        var selects = findSignalSelects();
        for (var i = 0; i < selects.length; i++) {
            wire(selects[i]);
        }
    }

    // Wagtail's InlinePanel adds new rows dynamically. Observe the
    // document so newly-inserted signal selects get hooked up too.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireAll);
    } else {
        wireAll();
    }

    if ('MutationObserver' in window) {
        var observer = new window.MutationObserver(function (mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length) {
                    wireAll();
                    return;
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
})();
