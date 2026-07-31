/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    buildHelpText,
    renderConditionHelp,
    filterOperators,
    validateExpectedValue,
    validateConditions,
    initConditionHelp
} from '../../../../../media/js/cms/routing/condition-help.es6.js';

const COMMA_HINT = 'Separate multiple values with commas.';
const INVALID_HINT = 'That value is not valid.';

const PAYLOAD = {
    platform: {
        valueType: 'enum',
        description: 'The visitor operating system.',
        hint: 'Enter one of these values:',
        commaHint: COMMA_HINT,
        invalidHint: INVALID_HINT,
        operators: [
            { value: 'is', label: 'is' },
            { value: 'is_not', label: 'is not' },
            { value: 'in', label: 'in' },
            { value: 'not_in', label: 'not in' }
        ],
        enumValues: [
            { value: 'windows', label: 'Windows' },
            { value: 'osx', label: 'macOS' }
        ],
        values: []
    },
    firefox_version: {
        valueType: 'version',
        description: 'The visitor Firefox version.',
        hint: 'Enter a version, e.g. 129 or 130.0.1.',
        commaHint: COMMA_HINT,
        invalidHint: INVALID_HINT,
        operators: [
            { value: 'gte', label: 'is at least' },
            { value: 'lt', label: 'is less than' }
        ],
        enumValues: [],
        values: []
    },
    // A known-set STRING signal (locale/country): the values list is advisory, not enforced —
    // an off-list value fails to match at runtime and the canonical page serves (fail-safe).
    locale: {
        valueType: 'string',
        description: 'The visitor locale.',
        hint: 'Enter one of these values:',
        commaHint: COMMA_HINT,
        invalidHint: INVALID_HINT,
        operators: [
            { value: 'is', label: 'is' },
            { value: 'in', label: 'in' }
        ],
        enumValues: [],
        values: ['en-US', 'de', 'fr']
    },
    // A boolean signal: a malformed value ("yess" → false) silently mis-routes, so it stays a
    // hard block.
    is_default_browser: {
        valueType: 'boolean',
        description: 'Whether Firefox is the default browser.',
        hint: 'Enter true or false.',
        commaHint: COMMA_HINT,
        invalidHint: INVALID_HINT,
        operators: [{ value: 'is', label: 'is' }],
        enumValues: [],
        values: []
    }
};

// A representative subset of the operator dropdown (enum-legal is/in, version-legal gte/lt).
const OPERATOR_OPTIONS = ['is', 'in', 'gte', 'lt'];

function makeConditionDOM(signalValue) {
    const container = document.createElement('div');
    const select = document.createElement('select');
    select.setAttribute('name', 'routing_rules-0-conditions-0-signal');
    Object.keys(PAYLOAD).forEach(function (name) {
        const option = document.createElement('option');
        option.value = name;
        select.appendChild(option);
    });
    select.value = signalValue;

    const operatorSelect = document.createElement('select');
    operatorSelect.setAttribute(
        'name',
        'routing_rules-0-conditions-0-operator'
    );
    OPERATOR_OPTIONS.forEach(function (value) {
        const option = document.createElement('option');
        option.value = value;
        operatorSelect.appendChild(option);
    });

    const fieldWrap = document.createElement('div');
    const input = document.createElement('input');
    input.setAttribute('name', 'routing_rules-0-conditions-0-expected_value');
    fieldWrap.appendChild(input);
    container.appendChild(select);
    container.appendChild(operatorSelect);
    container.appendChild(fieldWrap);
    return {
        container: container,
        select: select,
        operatorSelect: operatorSelect,
        fieldWrap: fieldWrap
    };
}

function hiddenValues(operatorSelect) {
    const hidden = [];
    Array.prototype.forEach.call(operatorSelect.options, function (option) {
        if (option.hidden) {
            hidden.push(option.value);
        }
    });
    return hidden;
}

describe('cms/routing/condition-help.es6.js', function () {
    describe('buildHelpText', function () {
        it('leads with the description and lists enum value codes (no label parens)', function () {
            const text = buildHelpText(PAYLOAD.platform, 'is');
            expect(text).toContain('The visitor operating system.');
            expect(text).toContain('Enter one of these values:');
            expect(text).toContain('windows');
            expect(text).toContain('osx');
            expect(text).not.toContain('(windows)'); // codes only, no label parens
        });

        it('does not restate operators in the help', function () {
            const text = buildHelpText(PAYLOAD.platform, 'is');
            expect(text).not.toContain('is not');
            const version = buildHelpText(PAYLOAD.firefox_version, 'gte');
            expect(version).toContain('The visitor Firefox version.');
            expect(version).toContain('130.0.1');
            expect(version).not.toContain('is at least');
        });

        it('adds a comma-separated hint only for set-membership operators', function () {
            expect(buildHelpText(PAYLOAD.platform, 'is')).not.toContain(
                COMMA_HINT
            );
            expect(buildHelpText(PAYLOAD.platform, 'in')).toContain(COMMA_HINT);
            expect(buildHelpText(PAYLOAD.platform, 'not_in')).toContain(
                COMMA_HINT
            );
        });

        it('leads with the value list for a string signal with a known set', function () {
            const meta = {
                valueType: 'string',
                description: 'The visitor locale.',
                hint: 'Enter one of these values:',
                commaHint: COMMA_HINT,
                operators: [],
                enumValues: [],
                values: ['US', 'GB', 'DE']
            };
            const text = buildHelpText(meta, 'is');
            expect(text).toContain('The visitor locale.');
            expect(text).toContain('US');
            expect(text).toContain('DE');
        });

        it('caps a long value list and reports the total', function () {
            const values = [];
            for (let i = 0; i < 40; i++) {
                values.push('v' + i);
            }
            const text = buildHelpText(
                {
                    valueType: 'string',
                    hint: 'Enter one of these values:',
                    commaHint: COMMA_HINT,
                    operators: [],
                    enumValues: [],
                    values: values
                },
                'in'
            );
            expect(text).toContain('v0');
            expect(text).not.toContain('v39'); // beyond the cap
            expect(text).toContain('(40 total)');
        });

        it('is empty for an unknown signal', function () {
            expect(buildHelpText(undefined, 'is')).toEqual('');
        });
    });

    describe('renderConditionHelp', function () {
        it('inserts help beneath the expected-value field', function () {
            const dom = makeConditionDOM('platform');
            renderConditionHelp(dom.select, PAYLOAD, dom.container);
            const help = dom.fieldWrap.querySelector('.routing-condition-help');
            expect(help).not.toBeNull();
            expect(help.textContent).toContain('operating system');
            expect(help.textContent).toContain('windows');
        });

        it('updates the help when the signal changes', function () {
            const dom = makeConditionDOM('platform');
            renderConditionHelp(dom.select, PAYLOAD, dom.container);
            dom.select.value = 'firefox_version';
            renderConditionHelp(dom.select, PAYLOAD, dom.container);
            const help = dom.fieldWrap.querySelector('.routing-condition-help');
            expect(help.textContent).toContain('Firefox version');
            expect(help.textContent).not.toContain('operating system');
        });
    });

    describe('filterOperators', function () {
        it('restricts the operator dropdown to the signal legal operators', function () {
            const dom = makeConditionDOM('platform');
            filterOperators(dom.select, PAYLOAD, dom.container);
            // Enum signal: is/in legal; version-only gte/lt hidden.
            expect(hiddenValues(dom.operatorSelect).sort()).toEqual([
                'gte',
                'lt'
            ]);
        });

        it('resets a now-illegal operator selection to the first legal one', function () {
            const dom = makeConditionDOM('platform');
            dom.operatorSelect.value = 'gte'; // illegal for an enum signal
            filterOperators(dom.select, PAYLOAD, dom.container);
            expect(dom.operatorSelect.value).toEqual('is');
        });

        it('keeps a still-legal operator selection', function () {
            const dom = makeConditionDOM('platform');
            dom.operatorSelect.value = 'in';
            filterOperators(dom.select, PAYLOAD, dom.container);
            expect(dom.operatorSelect.value).toEqual('in');
        });

        it('leaves every operator available for an unknown/blank signal', function () {
            const dom = makeConditionDOM('platform');
            dom.select.value = ''; // no payload entry
            filterOperators(dom.select, PAYLOAD, dom.container);
            expect(hiddenValues(dom.operatorSelect)).toEqual([]);
        });
    });

    describe('initConditionHelp — operator filtering', function () {
        it('filters operators on initial wiring, preserving a saved legal operator', function () {
            // An existing rule: version signal with a saved, legal operator.
            const dom = makeConditionDOM('firefox_version');
            dom.operatorSelect.value = 'gte';
            initConditionHelp({ payload: PAYLOAD, root: dom.container });
            expect(hiddenValues(dom.operatorSelect).sort()).toEqual([
                'in',
                'is'
            ]);
            expect(dom.operatorSelect.value).toEqual('gte'); // preserved
        });

        it('re-filters operators when the signal changes', function () {
            const dom = makeConditionDOM('platform');
            initConditionHelp({ payload: PAYLOAD, root: dom.container });
            dom.select.value = 'firefox_version';
            dom.select.dispatchEvent(new Event('change'));
            expect(hiddenValues(dom.operatorSelect).sort()).toEqual([
                'in',
                'is'
            ]);
            // 'is' was selected and is now illegal -> reset to the first version operator.
            expect(dom.operatorSelect.value).toEqual('gte');
        });
    });

    describe('validateExpectedValue', function () {
        const enumMeta = PAYLOAD.platform;
        const versionMeta = PAYLOAD.firefox_version;

        it('accepts an enum member and rejects a non-member', function () {
            expect(validateExpectedValue(enumMeta, 'is', 'windows')).toBe(true);
            expect(validateExpectedValue(enumMeta, 'is', 'beos')).toBe(false);
        });

        it('checks every value in a set-membership list', function () {
            expect(validateExpectedValue(enumMeta, 'in', 'windows, osx')).toBe(
                true
            );
            expect(validateExpectedValue(enumMeta, 'in', 'windows, beos')).toBe(
                false
            );
        });

        it('rejects an empty value', function () {
            expect(validateExpectedValue(enumMeta, 'is', '   ')).toBe(false);
        });

        it('rejects an operator illegal for the signal', function () {
            expect(validateExpectedValue(enumMeta, 'gte', 'windows')).toBe(
                false
            );
        });

        it('validates version format (bare, rv-prefixed, dotted)', function () {
            expect(validateExpectedValue(versionMeta, 'gte', '129.0.1')).toBe(
                true
            );
            expect(validateExpectedValue(versionMeta, 'gte', 'rv:129')).toBe(
                true
            );
            expect(validateExpectedValue(versionMeta, 'gte', 'abc')).toBe(
                false
            );
        });

        it('validates integer and boolean values', function () {
            const intMeta = {
                valueType: 'integer',
                operators: [{ value: 'gte', label: 'x' }],
                enumValues: []
            };
            expect(validateExpectedValue(intMeta, 'gte', '30')).toBe(true);
            expect(validateExpectedValue(intMeta, 'gte', '3.5')).toBe(false);
            const boolMeta = {
                valueType: 'boolean',
                operators: [{ value: 'is', label: 'x' }],
                enumValues: []
            };
            expect(validateExpectedValue(boolMeta, 'is', 'true')).toBe(true);
            expect(validateExpectedValue(boolMeta, 'is', 'yes')).toBe(false);
        });

        it('checks membership for a known-set string signal (locale/country)', function () {
            const localeMeta = {
                valueType: 'string',
                operators: [
                    { value: 'is', label: 'x' },
                    { value: 'in', label: 'y' }
                ],
                enumValues: [],
                values: ['en-US', 'de']
            };
            expect(validateExpectedValue(localeMeta, 'is', 'de')).toBe(true);
            expect(validateExpectedValue(localeMeta, 'is', 'zz')).toBe(false);
        });

        it('accepts any non-empty free-text string', function () {
            const strMeta = {
                valueType: 'string',
                operators: [{ value: 'is', label: 'x' }],
                enumValues: [],
                values: []
            };
            expect(validateExpectedValue(strMeta, 'is', 'anything')).toBe(true);
        });

        it('is valid for an unknown signal (server backstop)', function () {
            expect(validateExpectedValue(undefined, 'is', 'x')).toBe(true);
        });
    });

    describe('validateConditions', function () {
        it('returns false and flags the row for an invalid value', function () {
            const dom = makeConditionDOM('platform');
            dom.operatorSelect.value = 'is'; // value left empty -> invalid
            document.body.appendChild(dom.container);
            try {
                expect(validateConditions(dom.container, PAYLOAD)).toBe(false);
                const expected = dom.fieldWrap.querySelector('input');
                expect(expected.getAttribute('aria-invalid')).toEqual('true');
                const help = dom.fieldWrap.querySelector(
                    '.routing-condition-help'
                );
                expect(
                    help.classList.contains('routing-condition-help--invalid')
                ).toBe(true);
                // An explicit message, not just a red outline.
                expect(help.textContent).toContain(INVALID_HINT);
            } finally {
                document.body.removeChild(dom.container);
            }
        });

        it('returns true and clears flags for valid values', function () {
            const dom = makeConditionDOM('platform');
            dom.operatorSelect.value = 'is';
            dom.fieldWrap.querySelector('input').value = 'windows';
            expect(validateConditions(dom.container, PAYLOAD)).toBe(true);
            expect(
                dom.fieldWrap
                    .querySelector('input')
                    .getAttribute('aria-invalid')
            ).toBeNull();
        });

        it('treats an off-list locale/country value as advisory: red hint, but no submit block', function () {
            const dom = makeConditionDOM('locale');
            dom.operatorSelect.value = 'is';
            // A real, valid visitor locale that just isn't one of the CMS content locales.
            dom.fieldWrap.querySelector('input').value = 'zz';
            document.body.appendChild(dom.container);
            try {
                // Advisory ⇒ the save is allowed to proceed...
                expect(validateConditions(dom.container, PAYLOAD)).toBe(true);
                // ...but the author still sees the red hint (with the valid values).
                const help = dom.fieldWrap.querySelector(
                    '.routing-condition-help'
                );
                expect(
                    help.classList.contains('routing-condition-help--invalid')
                ).toBe(true);
                expect(help.textContent).toContain('en-US');
            } finally {
                document.body.removeChild(dom.container);
            }
        });

        it('still blocks a visible hard-invalid value (malformed boolean)', function () {
            const dom = makeConditionDOM('is_default_browser');
            dom.operatorSelect.value = 'is';
            dom.fieldWrap.querySelector('input').value = 'yess'; // silently → false
            document.body.appendChild(dom.container);
            try {
                expect(validateConditions(dom.container, PAYLOAD)).toBe(false);
                expect(
                    dom.fieldWrap
                        .querySelector('input')
                        .getAttribute('aria-invalid')
                ).toEqual('true');
            } finally {
                document.body.removeChild(dom.container);
            }
        });

        it('does not block a hard-invalid row that is hidden (on another tab)', function () {
            const dom = makeConditionDOM('platform');
            dom.operatorSelect.value = 'is';
            dom.fieldWrap.querySelector('input').value = ''; // empty ⇒ hard-invalid
            // An inactive Wagtail tab panel is display:none — the field isn't laid out.
            dom.container.style.display = 'none';
            document.body.appendChild(dom.container);
            try {
                // The field isn't visible, so the save reaches the server and Wagtail surfaces
                // the error on the right tab natively — the client doesn't silently block it.
                expect(validateConditions(dom.container, PAYLOAD)).toBe(true);
            } finally {
                document.body.removeChild(dom.container);
            }
        });
    });

    describe('initConditionHelp — pre-submit guard', function () {
        // The form is left DETACHED from the document on purpose: a synthetic submit that
        // the guard does NOT block would otherwise navigate the test runner away.
        function formWith(signalValue, operator, expectedValue) {
            const form = document.createElement('form');
            const dom = makeConditionDOM(signalValue);
            dom.operatorSelect.value = operator;
            dom.fieldWrap.querySelector('input').value = expectedValue;
            form.appendChild(dom.container);
            return { form: form, dom: dom };
        }

        function submit(form) {
            const event = new Event('submit', {
                cancelable: true,
                bubbles: true
            });
            form.dispatchEvent(event);
            return event;
        }

        it('blocks submit when a visible condition value is hard-invalid', function () {
            // Attached (so the routing field is visible) — safe because the guard blocks the
            // submit, so it never navigates the runner.
            const { form, dom } = formWith('platform', 'is', 'beos');
            document.body.appendChild(form);
            try {
                initConditionHelp({ payload: PAYLOAD, root: form });
                const event = submit(form);
                expect(event.defaultPrevented).toBe(true);
                const help = dom.fieldWrap.querySelector(
                    '.routing-condition-help'
                );
                expect(
                    help.classList.contains('routing-condition-help--invalid')
                ).toBe(true);
            } finally {
                document.body.removeChild(form);
            }
        });

        it('allows submit when every condition value is valid', function () {
            const { form } = formWith('platform', 'is', 'windows');
            initConditionHelp({ payload: PAYLOAD, root: form });
            expect(submit(form).defaultPrevented).toBe(false);
        });

        it('allows submit for an off-list locale value (advisory, not a hard block)', function () {
            const { form } = formWith('locale', 'is', 'zz');
            initConditionHelp({ payload: PAYLOAD, root: form });
            expect(submit(form).defaultPrevented).toBe(false);
        });
    });

    describe('initConditionHelp', function () {
        it('wires a change handler that refreshes the help', function () {
            const dom = makeConditionDOM('platform');
            initConditionHelp({ payload: PAYLOAD, root: dom.container });
            expect(
                dom.fieldWrap.querySelector('.routing-condition-help')
                    .textContent
            ).toContain('operating system');

            dom.select.value = 'firefox_version';
            dom.select.dispatchEvent(new Event('change'));
            expect(
                dom.fieldWrap.querySelector('.routing-condition-help')
                    .textContent
            ).toContain('Firefox version');
        });

        it('wires a row inserted AFTER init (regression guard for the missing observer)', async function () {
            const root = document.createElement('div');
            document.body.appendChild(root);
            try {
                initConditionHelp({ payload: PAYLOAD, root: root });
                // A condition row Wagtail adds after load — the one-shot scan never saw it.
                const dom = makeConditionDOM('platform');
                root.appendChild(dom.container);
                // Let the MutationObserver callback run.
                await new Promise(function (resolve) {
                    setTimeout(resolve, 0);
                });
                const help = dom.fieldWrap.querySelector(
                    '.routing-condition-help'
                );
                expect(help).not.toBeNull();
                expect(help.textContent).toContain('operating system');
            } finally {
                document.body.removeChild(root);
            }
        });

        it('flags a bad value inline on edit (change), before any save', function () {
            const dom = makeConditionDOM('platform');
            document.body.appendChild(dom.container);
            try {
                initConditionHelp({ payload: PAYLOAD, root: dom.container });
                const input = dom.fieldWrap.querySelector('input');
                input.value = 'beos'; // not an enum member
                input.dispatchEvent(new Event('change'));
                const help = dom.fieldWrap.querySelector(
                    '.routing-condition-help'
                );
                expect(
                    help.classList.contains('routing-condition-help--invalid')
                ).toBe(true);
            } finally {
                document.body.removeChild(dom.container);
            }
        });

        it('does not double-bind a select on repeated scans', function () {
            const dom = makeConditionDOM('platform');
            initConditionHelp({ payload: PAYLOAD, root: dom.container });
            // Re-initialising must be a no-op for an already-wired select.
            initConditionHelp({ payload: PAYLOAD, root: dom.container });
            const helps = dom.fieldWrap.querySelectorAll(
                '.routing-condition-help'
            );
            expect(helps.length).toEqual(1);
        });
    });
});
