/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — dynamic condition help text in the Wagtail admin (spec §6.2).
 *
 * When an author picks a signal in a routing condition, this surfaces the valid values
 * beneath the expected-value field: the enumerated set for enum signals, or a type hint
 * plus the operator meanings for the rest. Everything human-readable comes from
 * `window.ROUTING_SIGNAL_PAYLOAD` (the registry, localized server-side in C11), so the
 * help can never drift from the evaluator and needs no English literals here.
 */

const HELP_CLASSNAME = 'routing-condition-help';
// Flag set on a wired signal <select> so re-scans never double-bind it.
const BOUND_FLAG = 'springfieldRoutingBound';
// Cap on how many known values are spelled out inline (locale/country are long); the
// full set lives on the Signals reference page.
const VALUE_LIST_CAP = 15;

function expectedFieldFor(select, root) {
    // The condition's signal select and expected-value input share an inline-panel
    // prefix and differ only by the field suffix (Wagtail InlinePanel naming).
    const name = select.getAttribute('name') || '';
    const expectedName = name.replace(/-signal$/, '-expected_value');
    if (expectedName === name) {
        return null;
    }
    return root.querySelector('[name="' + expectedName + '"]');
}

function joinCapped(values) {
    const shown = values.slice(0, VALUE_LIST_CAP).join(', ');
    if (values.length > VALUE_LIST_CAP) {
        return shown + ', … (' + values.length + ' total)';
    }
    return shown;
}

export function buildHelpText(meta) {
    if (!meta) {
        return '';
    }
    // Values-first (ED-3): a closed value set is the most useful thing to show, so it
    // leads the help line for enum signals and for string signals with a known set
    // (locale / country). The lead-in (`hint`) is localized server-side.
    if (meta.enumValues && meta.enumValues.length) {
        const values = meta.enumValues
            .map((entry) => entry.label + ' (' + entry.value + ')')
            .join(', ');
        return meta.hint + ' ' + values;
    }
    if (meta.values && meta.values.length) {
        return meta.hint + ' ' + joinCapped(meta.values);
    }
    const operators = (meta.operators || [])
        .map((entry) => entry.label)
        .join(', ');
    return operators ? meta.hint + ' ' + operators : meta.hint;
}

export function renderConditionHelp(select, payload, root) {
    const scope = root || document;
    const expected = expectedFieldFor(select, scope);
    if (!expected || !expected.parentNode) {
        return null;
    }
    let help = expected.parentNode.querySelector('.' + HELP_CLASSNAME);
    if (!help) {
        help = document.createElement('p');
        help.className = HELP_CLASSNAME;
        expected.parentNode.appendChild(help);
    }
    help.textContent = buildHelpText(payload[select.value]);
    return help;
}

function wireSelect(select, payload, scope) {
    // Idempotent: a select is bound once, so re-scanning after DOM changes is safe.
    if (select.dataset[BOUND_FLAG] === '1') {
        return;
    }
    select.dataset[BOUND_FLAG] = '1';
    select.addEventListener('change', function () {
        renderConditionHelp(select, payload, scope);
    });
    renderConditionHelp(select, payload, scope);
}

function wireAll(payload, scope) {
    const selects = scope.querySelectorAll('select[name$="-signal"]');
    Array.prototype.forEach.call(selects, function (select) {
        wireSelect(select, payload, scope);
    });
}

export function initConditionHelp(options) {
    const opts = options || {};
    const payload =
        opts.payload ||
        (typeof window !== 'undefined'
            ? window.ROUTING_SIGNAL_PAYLOAD
            : null) ||
        {};
    const scope = opts.root || document;

    wireAll(payload, scope);

    // Wagtail hydrates nested InlinePanel rows client-side *after* load, and "Add
    // rule/condition" inserts more rows later — none of which the one-shot scan above
    // sees. Without this observer the help never renders on those rows (the confirmed
    // ED-3 bug). Re-scan (idempotently) whenever nodes are added.
    const observeTarget =
        opts.root || (typeof document !== 'undefined' ? document.body : null);
    if (observeTarget && typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function () {
            wireAll(payload, scope);
        });
        observer.observe(observeTarget, { childList: true, subtree: true });
        return observer;
    }
    return null;
}

// Auto-run in the admin, but only once the payload global is present (the insert_editor_js
// hook sets it just before this script). Skipping when it's absent keeps the observer out
// of non-editor pages and unit tests, which drive the exported functions directly.
if (
    typeof document !== 'undefined' &&
    typeof window !== 'undefined' &&
    window.ROUTING_SIGNAL_PAYLOAD
) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initConditionHelp();
        });
    } else {
        initConditionHelp();
    }
}
