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

export function buildHelpText(meta) {
    if (!meta) {
        return '';
    }
    if (meta.enumValues && meta.enumValues.length) {
        const values = meta.enumValues
            .map((entry) => entry.label + ' (' + entry.value + ')')
            .join(', ');
        return meta.hint + ' ' + values;
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

export function initConditionHelp(options) {
    const opts = options || {};
    const payload =
        opts.payload ||
        (typeof window !== 'undefined'
            ? window.ROUTING_SIGNAL_PAYLOAD
            : null) ||
        {};
    const scope = opts.root || document;
    const selects = scope.querySelectorAll('select[name$="-signal"]');
    Array.prototype.forEach.call(selects, function (select) {
        select.addEventListener('change', function () {
            renderConditionHelp(select, payload, scope);
        });
        renderConditionHelp(select, payload, scope);
    });
}

// Auto-run in the admin. A no-op where there are no condition selects (e.g. tests that
// import the functions and drive them explicitly).
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initConditionHelp();
        });
    } else {
        initConditionHelp();
    }
}
